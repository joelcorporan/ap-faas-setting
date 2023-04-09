#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# External imports
import concurrent.futures
import itertools
import math
import time
from datetime import datetime, timedelta
from typing import Iterable, Tuple

import boto3
import numpy as np

# Local imports
from ap_faas.traces.providers.TracesInterface import TracesInterface
from ap_faas.utils.logger import logger


class Traces(TracesInterface):
    """
    This is a class for handling cloud provider traces.

    Attributes:
      function (str): function name
      provider_info (dict): Cloud provider information.
      experimental_results (dict): Experimental results from fetcher.
    """

    def __init__(
        self,
        functions: str,
        config_file: dict,
        namespace: str = "AWS/Lambda",
    ) -> None:
        """
        The constructor for Traces class.

        Parameters:
          functions (str): Function name
          config_file (dict): Experimental configuration file.
        """
        session = None

        if "profile" in config_file["credentials"]:
            session = boto3.Session(
                profile_name=config_file["credentials"]["profile"],
                region_name=config_file["region"],
            )
        elif "access_key" and "secret_key" in config_file["credentials"]:
            session = boto3.Session(
                aws_access_key_id=config_file["credentials"]["access_key"],
                aws_secret_access_key=config_file["credentials"]["secret_key"],
                region_name=config_file["region"],
            )
        else:
            raise Exception("Cloud provider credentials not found")

        self.cloudwatch = session.client("cloudwatch")
        logger.info("Connected to AWS CloudWatch")

        self.cloudwatch_logs = session.client("logs")
        logger.info("Connected to AWS CloudWatchLogs")

        self.namespace = namespace
        self.functions = functions

        self.start_time = datetime.fromtimestamp(
            config_file["experimental_results"]["start_time"]
        ) - timedelta(hours=0, minutes=0)
        self.end_time = datetime.fromtimestamp(
            config_file["experimental_results"]["end_time"]
        ) + timedelta(hours=0, minutes=15)

        logger.info(
            (
                f"From {self.start_time.strftime('%m/%d/%Y %H:%M:%S')} "
                f"to {self.end_time.strftime('%m/%d/%Y %H:%M:%S')}"
            )
        )

    def get_traces_per_request(self, limit: int, resolution: int) -> list:
        """
        The function retrieves the trace from each function.

        Parameters:
          limit (int): Record limit of retrieval.

        Returns:
          list: List of dictionaries with traces
        """
        logger.info("Extracting Traces from LambdaInsights")

        query = f"filter event_type = 'performance' and \
            function_name in {self.functions} \
            | fields \
              request_id as response_id, \
              duration as duration_ms, \
              memory_utilization as memory_utilization_percentage, \
              total_memory, \
              cpu_total_time as cpu_total_time_ms, \
              total_network as total_network_bytes, \
              billed_mb_ms, \
              billed_mb_ms / 1000 / 1000 as invoke_cost_gb_per_second, \
              cold_start, \
              init_duration as init_duration_ms, \
              version, \
              shutdown, \
              shutdown_reason \
            | sort @timestamp desc"

        log_group = "/aws/lambda-insights"
        function_traces = self.__iter_query_response(
            query, log_group, limit, resolution
        )

        return [self.__parse_trace_per_request(traces) for traces in function_traces]

    def __parse_trace_per_request(self, traces: list) -> dict:
        """
        The function parse the function trace.

        Parameters:
          traces (list): List of traces from provider.

        Returns:
          dict: Dictionary with all traces
        """
        return {trace["field"]: trace["value"] for trace in traces}

    def __iter_query_response(
        self, query: str, log_group: str, limit: int, resolution: int
    ) -> list:
        """
        The function allows multiple query requests.

        Parameters:
          query (str): Query string.
          log_group (str): Log group where perform query.
          limit (int): Record limit of retrieval.

        Returns:
          list: List of query results
        """
        limit_quota = 10000

        timestamp_sizes = np.arange(
            math.floor(self.start_time.timestamp()),
            math.ceil(self.end_time.timestamp()),
            resolution,
        )

        timestamp_sizes = (
            np.append(timestamp_sizes, self.end_time.timestamp())
            if timestamp_sizes[-1] != self.end_time.timestamp()
            else timestamp_sizes
        )

        def pairwise(iterable: Iterable) -> Iterable[Tuple]:
            a, b = itertools.tee(iterable)
            next(b, None)
            return zip(a, b)

        threads = []
        response_result = []

        logger.info(f"{len(timestamp_sizes) - 1} interval(s) to find the records")
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            for index, pair in enumerate(pairwise(timestamp_sizes)):
                threads.append(
                    executor.submit(
                        self.__query_response,
                        query,
                        log_group,
                        pair[0],
                        pair[1],
                        limit_quota,
                        (index + 1),
                        len(timestamp_sizes) - 1,
                    )
                )
                time.sleep(0.50)
        for future in concurrent.futures.as_completed(threads):
            response_result += future.result()

        return response_result

    def __query_response(
        self,
        query: str,
        log_group: str,
        start_time: float,
        end_time: float,
        limit: int = 1000,
        index: int = 1,
        total: int = 1,
    ) -> list:
        """
        The function perform query over log group.

        Parameters:
          query (str): Query string.
          log_group (str): Log group where perform query.
          start_time (float): Start time of the experiment.
          end_time (float): End time of the experiment.
          limit (int): Record limit of retrieval.

        Returns:
          list: List of query results
        """
        # logger.info("Starting query...")
        start_query_response = self.cloudwatch_logs.start_query(
            logGroupName=log_group,
            startTime=int(start_time),
            endTime=int(end_time),
            queryString=query,
            limit=limit,
        )

        query_id = start_query_response["queryId"]
        logger.info(f"{index} out of {total} - Generated query ID: {query_id}")

        response = {}

        count = 0
        while count < 3:
            time.sleep(1)
            response = self.cloudwatch_logs.get_query_results(queryId=query_id)
            if response["status"] != "Running":
                break
            count += 1

        logger.info(
            f"{query_id}: {len(response['results'])} record(s) found (retries:{count})"
        )
        if len(response["results"]) >= 10000:
            logger.warning(
                (
                    f"Record larger than 10,000 ({len(response['results'])}). "
                    "Please try again with a lower resolution"
                )
            )
        return response["results"]
