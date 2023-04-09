#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# External imports
import concurrent.futures
import math
import os
import time
from concurrent.futures._base import DoneAndNotDoneFutures
from multiprocessing import cpu_count

import numpy as np
import pandas as pd

from ap_faas.config import BASE_DIR
from ap_faas.fetcher.fetch import prepare_fetch

# Local imports
from ap_faas.utils.logger import logger


def get_concurrent_seq(concurrent: int, core_size: int) -> list:
    """
    The function retrieves the sequence of concurrency per core.

    Parameters:
      concurrent (int): Concurrent size
      core_size (int): Core size

    Returns:
      list: Sequence of concurrency
    """
    if concurrent < core_size:
        return [1 for _ in range(concurrent)]
    else:
        base, extra = divmod(concurrent, core_size)
        return [base + (i < extra) for i in range(core_size)]


def run_experiment(
    config_file: dict,
    processes: int,
    concurrent_index: int,
    chunked_data_per_core: list,
    concurrent_per_core: list,
) -> DoneAndNotDoneFutures[pd.core.frame.DataFrame]:
    """
    The function run experiment for asyncronous profiling.

    Parameters:
      config_file (dict): Fetching configuration file
      processes (int): Number of processes
      concurrent_index (int): Concurrent index
      chunked_data_per_core (list): Chunked of data per core
      concurrent_per_core (list): Concurrent size per core

    Returns:
      concurrent.futures: Completed asyncronous requests per core
    """
    logger.info(f"Current processes used: {processes}")
    logger.info(f"Current concurrent size: {concurrent_index}")

    ramp_up_per_core = config_file["ramp_up_time"] / processes
    logger.info(
        (
            f"Current ramp up time: {config_file['ramp_up_time']} "
            f"({ramp_up_per_core} second(s) interval per core)"
        )
    )
    logger.info(
        (
            "Current chunked per core: "
            f"{[ len(chunked) for chunked in chunked_data_per_core]}"
        )
    )
    logger.info(f"Current concurrent sequence per core: {concurrent_per_core}")

    executor = concurrent.futures.ProcessPoolExecutor(processes)

    futures = []
    chunked_concurrent_per_core = zip(chunked_data_per_core, concurrent_per_core)
    for index, (chunked, concurrent_size) in enumerate(chunked_concurrent_per_core):
        future = executor.submit(
            prepare_fetch,
            chunked,
            config_file["response_headers"],
            concurrent_size,
            config_file["rate_per_request"],
            (index + 1),
        )

        futures.append(future)

        # Ramp up time
        time.sleep(ramp_up_per_core)

    finishedResults = concurrent.futures.wait(futures)
    logger.info("Shutting processes down: started")
    executor.shutdown(wait=True)
    logger.info("Shutting processes down: finished")

    return finishedResults


def init(config_file: dict, exp_dir: str, data: pd.core.frame.DataFrame) -> list:
    """
    The function initializes the asyncronous profiling
    of function as a service at a cloud provider.

    Parameters:
      config_file (dict): Fetching configuration file
      exp_dir (str): Directory of the experimental results.
      data (pd.core.frame.DataFrame): Generated test data to fetch.

    Returns:
      list: List of files based on concurrency
    """

    # Number of CPU cores available (including logical cores)
    num_cores = math.floor(cpu_count() * (config_file["cpu_percentage"] / 100))

    # If data size is smaller than the number of CPU cores
    num_cores = num_cores if num_cores < len(data) else len(data)
    logger.info(f"Number of processes available: {num_cores}")

    # List of concurrent request per period
    concurrent_sizes = np.arange(
        config_file["concurrency"]["initial"],
        config_file["concurrency"]["maximum"],
        config_file["concurrency"]["increment"],
    )
    concurrent_sizes = (
        np.append(concurrent_sizes, config_file["concurrency"]["maximum"])
        if concurrent_sizes[-1] != config_file["concurrency"]["maximum"]
        else concurrent_sizes
    )
    logger.info(f"Concurrent sizes: {list(concurrent_sizes)}")

    # Run experiment per concurrent size
    logger.info("Starting Experiment....\n")
    for concurrent_index in concurrent_sizes:
        concurrent_per_core = get_concurrent_seq(concurrent_index, num_cores)

        # Number of processes to use
        processes = num_cores if concurrent_index > num_cores else concurrent_index

        # Data divided in chunked per CPU cores
        chunked_data_per_core = np.array_split(data, processes)

        doneTasks, _ = run_experiment(
            config_file,
            processes,
            concurrent_index,
            chunked_data_per_core,
            concurrent_per_core,
        )
        logger.info("Compiling experimental data and writting CSV file...")
        results = [item.result() for item in doneTasks]

        completed_results = pd.concat(results)
        completed_results.reset_index(drop=True, inplace=True)

        # Write to CSV file
        concurrent_file_location = os.path.join(
            exp_dir, f"test_{concurrent_index}_concurrency.csv"
        )
        completed_results.to_csv(concurrent_file_location, index=False)
        logger.info(f"Number of data processed: {len(completed_results)}")

        logger.success(
            (
                "Number of successful requests: "
                f"{len(completed_results[completed_results['response_status'] == 200])}"
            )
        )
        logger.error(
            (
                "Number of failed requests: "
                f"{len(completed_results[completed_results['response_status'] > 200 ])}"
            )
        )
        logger.info(
            (
                f"Test file saved for {concurrent_index} concurrent(s): "
                f"{os.path.relpath(concurrent_file_location, BASE_DIR)}\n"
            )
        )

        if config_file["concurrency"]["maximum"] != concurrent_index:
            wait_per_concurrency = config_file["concurrency"]["wait_time"]
            # Wait time per concurrent size
            logger.info(
                f"Wait of {wait_per_concurrency} second(s) before continuing...\n"
            )
            time.sleep(wait_per_concurrency)

    if len(os.listdir(exp_dir)) == len(concurrent_sizes):
        logger.info(f"Number of test file(s) stored: {len(os.listdir(exp_dir))}")
        return [
            f"test_{concurrent_index}_concurrency.csv"
            for concurrent_index in concurrent_sizes
        ]
    else:
        raise Exception(
            "The number of test file(s) stored are distinct to the concurreny size"
        )
