#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import urllib.parse as queryParams

# External imports
import pandas as pd
from pandas.core.frame import DataFrame

# Local imports
from ap_faas.utils.logger import logger


def parse_query(query_params: dict) -> str:
    """
    The function parses the query parameters from dictionary to string.

    Parameters:
      query_params (dict): Configuration file

    Returns:
      str: Encoded query parameters
    """
    query_pairs = [(k, v) for k, v in query_params.items()] if query_params else []
    return queryParams.urlencode(query_pairs, doseq=True)


def parse_https_sample(function: dict) -> dict:
    """
    The function parses the https events to dict.

    Parameters:
      function (dict): HTTP events

    Returns:
      str: List of dicts for HTTP events
    """
    https_samples = {
        "function_name": [function["name"] for _ in function["samples"]],
        "endpoint": [function["endpoint"] for _ in function["samples"]],
        "path": [sample["path"] for sample in function["samples"]],
        "method": [sample["method"] for sample in function["samples"]],
        "query_string": [
            parse_query(sample["query_string"]) for sample in function["samples"]
        ],
        "body": [sample["body"] for sample in function["samples"]],
    }

    return https_samples


def generate_sample(config_file: dict) -> DataFrame:
    """
    The function generates test data for profiling.

    Parameters:
      config_file (dict): Configuration file

    Returns:
      DataFrame: Generated sample data
    """
    logger.info("Test data generation has started!")
    logger.info(f"Test data size: {config_file['data_size']}")
    logger.info(f"Random seed: {config_file['random_seed']}")

    samples = None

    if config_file["event"] == "https":
        samples_df = pd.DataFrame(
            columns=[
                "function_name",
                "endpoint",
                "path",
                "method",
                "query_string",
                "body",
            ]
        )

        for function in config_file["functions"]:
            https_samples = pd.DataFrame(parse_https_sample(function))
            samples_df = pd.concat([samples_df, https_samples], ignore_index=True)

        samples = samples_df.copy(deep=True)

    if samples is None:
        raise Exception("Error parsing samples")

    sample_data = samples.sample(
        random_state=config_file["random_seed"],
        n=config_file["data_size"],
        replace=True,
    ).reset_index(drop=True)

    logger.info(f"\n {sample_data}")
    logger.success("Test data generation completed!\n")

    return sample_data
