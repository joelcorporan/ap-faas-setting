#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# External imports
import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

# Local imports
from ap_faas.config import BASE_DIR, OUTPUT_DIR
from ap_faas.fetcher import init as fetcher
from ap_faas.traces import init as traces
from ap_faas.utils.file_handler import (
    read_config_file,
    validate_config_file,
    write_file,
)
from ap_faas.utils.generator import generate_sample
from ap_faas.utils.logger import logger


def run_experiment(filename: str, exp_name: str) -> None:
    """
    Run experiment.

    :param filename (str): File name of configurations.
    :param exp_name (str): Name of the experiment
    :return bool
    """
    extension = Path(filename).suffix
    config_file = read_config_file(filename, extension)
    validate_config_file(config_file)

    # Check if data_size is lower than maximum concurrency
    if config_file["data_size"] < config_file["concurrency"]["maximum"]:
        raise Exception(
            "Maximum concurrency size greater than data size. \
            The maximum concurrency size has to be lower or equal the data size."
        )

    experiment_name = exp_name or config_file["name"]
    logger.info(f"Stating Experiment: {experiment_name}")

    logger.info("Generating sample data...\n")
    sample_data = generate_sample(config_file)

    # Start time of the experiment
    exp_start_time = datetime.now()

    # Create experiment directory
    exp_dir = os.path.join(
        OUTPUT_DIR,
        f"{int(round(exp_start_time.timestamp()))}_{experiment_name}",
    )
    os.makedirs(exp_dir)

    # Starting experimentation
    output_files = fetcher(config_file, exp_dir, sample_data)

    exp_end_time = datetime.now()

    logger.info(f"Start timestamp: {exp_start_time.strftime('%m/%d/%Y %H:%M:%S')}")
    logger.info(f"End timestamp: {exp_end_time.strftime('%m/%d/%Y %H:%M:%S')}")

    # Stored current results
    write_file(
        os.path.join(exp_dir, "config_used.json"),
        config_file
        | {
            "experimental_results": {
                "start_time": exp_start_time.timestamp(),
                "end_time": exp_end_time.timestamp(),
                "test_files": output_files,
            },
        },
    )

    logger.success("Experimental result successfully stored")


def get_traces(directory: str, resolution: int) -> None:
    """
    Get traces.

    :param experiment:str Directory with experimentation.
    :return bool
    """
    # Stop if directory not exists
    if directory is None or not os.path.exists(directory):
        raise Exception(
            "Directory not found: specify directory with .csv(s) and config_used.json"
        )

    config_filename = os.path.join(directory, "config_used.json")

    # Stop if config.json not exists
    if not os.path.exists(config_filename):
        raise Exception(
            "config.json not found: specify directory with in .csv(s) and config.json"
        )

    config_file = read_config_file(config_filename)
    test_directory = os.path.join(BASE_DIR, directory)

    concurrency_files = list(
        filter(lambda f: f.endswith(".csv"), os.listdir(test_directory))
    )

    if len(concurrency_files) != len(config_file["experimental_results"]["test_files"]):
        logger.error(
            "Length of .csv files found does not match"
            "with 'test_files' in config_used.json"
        )

    experiment_data = pd.concat(
        [
            pd.read_csv(os.path.join(test_directory, file)).assign(
                concurrency=int(file.split("_")[1])
            )
            for file in config_file["experimental_results"]["test_files"]
        ]
    ).reset_index(drop=True)

    traces_directory = os.path.join(test_directory, "traces")

    if not os.path.exists(traces_directory):
        os.makedirs(traces_directory)
    logger.info(f"Location of traces: {os.path.relpath(traces_directory, BASE_DIR)}")

    traces(config_file, traces_directory, experiment_data, resolution)


def experiment() -> None:
    """
    The experiment main function.

    """
    try:
        parser = argparse.ArgumentParser(
            prog="ap-faas",
            description="Run a experiment for a particular FaaS Function.",
            epilog="If a bug is found, please report it on the repository.",
        )

        # Options
        parser.add_argument(
            "-f",
            "--file",
            dest="filename",
            required=True,
            help="Configuration file for experiment.",
        )

        parser.add_argument(
            "-n",
            "--name",
            dest="name",
            required=False,
            help="Name of the experiment.",
        )

        args = parser.parse_args()

        if args.filename:
            return run_experiment(args.filename, args.name)
        else:
            parser.print_help()

    except Exception as e:
        logger.error(e)


def trace() -> None:
    """
    The trace main function.

    """
    try:
        parser = argparse.ArgumentParser(
            prog="ap-faas",
            description="Get the traces for a particular experimentation data. \
            To run an experimentation, use `poetry run experiment` instead.",
            epilog="If a bug is found, please report it on the repository.",
        )

        # Options
        parser.add_argument(
            "-d",
            "--directory",
            dest="directory",
            required=True,
            help="Directory of experimentation results.",
        )
        parser.add_argument(
            "-r",
            "--resolution",
            action="store",
            type=int,
            dest="resolution",
            help="Data resolution",
            default=30,
        )

        args = parser.parse_args()

        if args.directory:
            return get_traces(args.directory, args.resolution)
        else:
            parser.print_help()

    except Exception as e:
        logger.error(e)
