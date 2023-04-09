#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# External imports
import importlib
import os

import pandas as pd

# Local imports
from ap_faas.utils.logger import logger


def write_function_traces(
    traces_directory: str,
    experimental_data: pd.core.frame.DataFrame,
    function_traces: pd.core.frame.DataFrame,
) -> None:
    """
    The function stores execution and traces for each request

    Parameters:
      traces_directory (str): Directory of the trace files.
      experimental_data (DataFrame): Results from experimental test.
      function_traces (DataFrame): Trace information from each function's request.
    """

    # Filename for experimental data CSV file
    experimental_data_file = os.path.join(traces_directory, "experimental_data.csv")

    # Filename for traces data CSV file
    trace_data_file = os.path.join(traces_directory, "trace_data.csv")

    # Filename for complete data CSV file
    complete_data_file = os.path.join(traces_directory, "complete_data.csv")

    # Filename for unmatched traces
    unmatched_traces_file = os.path.join(traces_directory, "unmatched_traces.csv")

    # Write experimental data in file
    experimental_data.to_csv(experimental_data_file, index=False)

    # Write traces data in file
    function_traces.to_csv(trace_data_file, index=False)

    # Compile experimental data with traces
    complete_data = experimental_data.merge(
        function_traces.drop_duplicates(subset=["response_id"]),
        left_on="response_id",
        right_on="response_id",
        how="left",
        sort=False,
    )

    # Write complete data in file
    complete_data.to_csv(complete_data_file, index=False)

    # Get unmerged traces
    unmerged_df = function_traces.merge(complete_data, how="left", indicator=True)
    unmatched_traces = unmerged_df[unmerged_df["_merge"] == "left_only"][
        list(function_traces.columns)
    ]

    # Write unmatched traces in file
    unmatched_traces.to_csv(unmatched_traces_file, index=False)

    logger.info(
        (
            "(Unsuccessful Requests) - Experimental data: "
            f"{len(experimental_data.loc[experimental_data['response_status'] > 200 ])}"
            f" | Function traces: {complete_data['@ptr'].isna().sum()}"
        )
    )
    logger.success(
        (
            "Complete experiment data saved: "
            f"{os.path.relpath(complete_data_file, traces_directory)}\n"
        )
    )


def init(
    config_file: dict,
    traces_directory: str,
    experimental_data: pd.core.frame.DataFrame,
    resolution: int,
) -> None:
    """
    The function initializes the retrieval of traces from the provider
    from the cloud provider.

    Parameters:
      config_file (dict): Experimetnal configuration file
      traces_directory (str): Directory of the traces files
      limit (int): Record limit retrieval from logs
      experimental_data (Dataframe): Results from experimental test
    """
    # Get provider information
    provider = config_file["provider"]
    logger.info(f"Provider: {provider.upper()}")

    # Import library from supported cloud provider
    Traces = getattr(
        importlib.import_module(f"ap_faas.traces.providers.{provider}"),
        "Traces",
    )

    # Initialize Traces class
    traces = Traces(experimental_data["function_name"].unique().tolist(), config_file)
    logger.info(
        (
            f"{len(experimental_data.loc[experimental_data['response_status'] == 200])}"
            " requests were successful"
        )
    )

    # Getting traces information from function insights
    function_traces = pd.DataFrame(
        traces.get_traces_per_request(
            limit=len(experimental_data), resolution=resolution
        )
    )
    logger.info(
        f"{len(function_traces)} out of {len(experimental_data)} function traces found."
    )

    # Write execution and trace for each function's request
    write_function_traces(traces_directory, experimental_data, function_traces)
