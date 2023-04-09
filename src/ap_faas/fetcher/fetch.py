#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# External imports
import asyncio
import time
import uuid
from asyncio import Semaphore
from os import getpid
from types import SimpleNamespace
from typing import List

import numpy as np
from aiohttp import (
    ClientConnectionError,
    ClientPayloadError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    CookieJar,
    TraceConfig,
    TraceRequestEndParams,
    TraceRequestStartParams,
)
from pandas.core.frame import DataFrame
from pandas.core.series import Series
from rich.progress import BarColumn, Progress, TaskID, TextColumn

# Local imports
from ap_faas.utils.logger import TimeColumn, console, logger


async def fetch_data(
    request: Series,
    response_headers: list,
    session: ClientSession,
    progress_bar: Progress,
    task: TaskID,
) -> tuple:
    """
    The function fetch result from Function-as-a-Service.

    Parameters:
      request (Series[Any]): Request data point.
      response_headers (list): Response headers to capture.
      session (ClientSession): Async HTTP requests session
      progress_bar (Progress): Current progress bar.

    Returns:
      tuple: Tuple of request's result
    """
    url = f"{request['endpoint']}/{request['path']}?{request['query_string']}"

    try:
        trace_request_ctx = {
            "request_id": str(uuid.uuid4()),
            "request_time": 0,
            "response_time": 0,
        }
        async with getattr(session, request["method"].lower())(
            url, json=request["body"], trace_request_ctx=trace_request_ctx
        ) as resp:
            message = await resp.read()

            if resp.history:
                result = (
                    trace_request_ctx["request_id"],
                    resp.history[0].headers["response-id"],
                    resp.status,
                    f"Redirect to {resp.url}",
                    trace_request_ctx["request_time"],
                    trace_request_ctx["response_time"],
                ) + tuple(
                    resp.history[0].headers[response_header]
                    if response_header in resp.history[0].headers
                    else None
                    for response_header in response_headers
                )

            elif resp.status == 200:
                result = (
                    trace_request_ctx["request_id"],
                    resp.headers["response-id"],
                    resp.status,
                    message,
                    trace_request_ctx["request_time"],
                    trace_request_ctx["response_time"],
                ) + tuple(
                    resp.headers[response_header]
                    if response_header in resp.headers
                    else None
                    for response_header in response_headers
                )

            else:
                result = (
                    trace_request_ctx["request_id"],
                    None,
                    resp.status,
                    message,
                    trace_request_ctx["request_time"],
                    trace_request_ctx["response_time"],
                ) + tuple(None for _ in response_headers)

    except asyncio.exceptions.TimeoutError as time_error:
        logger.error(f"(TimeoutError) {trace_request_ctx['request_id']}: {time_error}")
        result = (
            trace_request_ctx["request_id"],
            None,
            503,
            time_error,
            trace_request_ctx["request_time"],
            trace_request_ctx["response_time"],
        ) + tuple(None for _ in response_headers)

    except ClientResponseError as resp_err:
        logger.error(
            f"(ClientResponseError) {trace_request_ctx['request_id']}: {resp_err}"
        )
        result = (
            trace_request_ctx["request_id"],
            None,
            resp_err.status,
            resp_err,
            trace_request_ctx["request_time"],
            trace_request_ctx["response_time"],
        ) + tuple(None for _ in response_headers)

    except ClientConnectionError as conn_err:
        logger.error(
            f"(ClientConnectionError) {trace_request_ctx['request_id']}: {conn_err}"
        )
        result = (
            trace_request_ctx["request_id"],
            None,
            500,
            conn_err,
            trace_request_ctx["request_time"],
            trace_request_ctx["response_time"],
        ) + tuple(None for _ in response_headers)

    except ClientPayloadError as load_error:
        logger.error(
            f"(ClientPayloadError) {trace_request_ctx['request_id']}: {load_error}"
        )
        result = (
            trace_request_ctx["request_id"],
            None,
            501,
            load_error,
            trace_request_ctx["request_time"],
            trace_request_ctx["response_time"],
        ) + tuple(None for _ in response_headers)

    except Exception as exeption_error:
        logger.error(f"(Exception) {trace_request_ctx['request_id']}: {exeption_error}")
        result = (
            trace_request_ctx["request_id"],
            None,
            502,
            exeption_error,
            trace_request_ctx["request_time"],
            trace_request_ctx["response_time"],
        ) + tuple(None for _ in response_headers)

    progress_bar.update(
        task, description=f"{request['method']} {request['path']}", advance=1
    )

    return result


async def on_request_start(
    session: ClientSession,
    trace_config_ctx: SimpleNamespace,
    params: TraceRequestStartParams,
) -> None:
    """
    The function traces client request when it starts.

    Parameters:
      session (ClientSession): Async HTTP requests session
      trace_config_ctx (SimpleNamespace): Trace configuration context.
      params (TraceRequestStartParams): Trace parameters
    """
    trace_config_ctx.start = session.loop.time()
    trace_config_ctx.trace_request_ctx["request_time"] = time.time()


async def on_request_end(
    session: ClientSession,
    trace_config_ctx: SimpleNamespace,
    params: TraceRequestEndParams,
) -> None:
    """
    The function traces client request when it starts.

    Parameters:
      session (ClientSession): Async HTTP requests session
      trace_config_ctx (SimpleNamespace): Trace configuration context.
      params (TraceRequestEndParams): Trace parameters
    """
    elapsed = session.loop.time() - trace_config_ctx.start
    trace_config_ctx.trace_request_ctx["response_time"] = elapsed


async def check_sem_async(
    request: Series,
    response_headers: list,
    semaphore: Semaphore,
    session_timeout: ClientTimeout,
    rate_per_request: int,
    progress_bar: Progress,
    task: TaskID,
) -> tuple:
    """
    The function run the request with a semaphore.

    Parameters:
      request (Series[Any]): Request data point.
      response_headers (list): Response headers to capture.
      semaphore (Semaphore): Asyncronous semaphore.
      session_timeout (ClientTimeout): Timeout configuration.
      rate_per_request (int): Delay of request per second.
      progress_bar (Progress): Current progress bar.

    Returns:
      tuple: Tuple of request's result
    """
    # Getter function with semaphore.
    async with semaphore:
        trace_config = TraceConfig()
        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_end.append(on_request_end)

        conn = None  # TCPConnector(limit=0)
        async with ClientSession(
            connector=conn,
            cookie_jar=CookieJar(),
            trace_configs=[trace_config],
            timeout=session_timeout,
        ) as session:
            fetched = await fetch_data(
                request, response_headers, session, progress_bar, task
            )

            if semaphore.locked():
                await asyncio.sleep(rate_per_request)

            return fetched


async def prepare_task(
    data: DataFrame,
    response_headers: list,
    concurrent: int,
    rate_per_request: int,
    progress_bar: Progress,
    task: TaskID,
) -> DataFrame:
    """
    The function prepares the tasks with concurrency and delay per task.

    Parameters:
      data (pd.core.frame.DataFrame): Data sample for process.
      response_headers (list): Response headers to capture.
      concurrent (int): Concurrent size.
      rate_per_request (int): Delay of request per second.
      progress_bar (Progress): Current progress bar.

    Returns:
      DataFrame: List of function's requests
    """
    # create instance of Semaphore
    semaphore = Semaphore(concurrent)

    # set the session timeout (this affects all requests)
    # https://stackoverflow.com/questions/64534844/python-asyncio-aiohttp-timeout
    # https://github.com/aio-libs/aiohttp/issues/3203
    session_timeout = ClientTimeout(total=None)

    updated_data = data
    tasks = [
        asyncio.create_task(
            check_sem_async(
                request,
                response_headers,
                semaphore,
                session_timeout,
                rate_per_request,
                progress_bar,
                task,
            )
        )
        for _, request in data.iterrows()
    ]

    response_output = await asyncio.gather(*tasks, return_exceptions=False)
    filtered_output: List = list(filter(None, response_output))

    updated_data[
        [
            "request_id",
            "response_id",
            "response_status",
            "response_body",
            "request_time",
            "response_time",
        ]
        + response_headers
    ] = np.array(filtered_output, dtype=object)

    return updated_data


def prepare_fetch(
    data: DataFrame,
    response_headers: list,
    concurrent: int,
    rate_per_request: int,
    proc_index: int,
) -> DataFrame:
    """
    The function prepares the fetcher for asyncronous profiling.

    Parameters:
      data (DataFrame): Data sample for process.
      response_headers (list): Response headers to capture.
      concurrent (int): Concurrent size.
      rate_per_request (int): Delay of request per second.
      process_index (str): Process index.

    Returns:
      DataFrame: List of function's requests
    """

    try:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
            TimeColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Process {proc_index} ({getpid()})", total=len(data)
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            results = loop.run_until_complete(
                prepare_task(
                    data, response_headers, concurrent, rate_per_request, progress, task
                )
            )

            progress.update(
                task,
                description=f"[bold green]Fetch Completed: {proc_index} ({getpid()})",
                advance=len(data),
            )

            # Wait 5s for the underlying SSL connections to close
            loop.run_until_complete(asyncio.sleep(2))
            loop.close()

            return results

    except Exception as err:
        logger.error(f"Error from fetcher: {err}")
        raise Exception(err)
