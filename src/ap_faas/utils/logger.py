#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# External imports
import sys
from enum import Enum
from typing import Optional, Union

import loguru
from loguru import logger as custom_logger
from rich.console import Console
from rich.progress import ProgressColumn, Task
from rich.text import Text
from rich.theme import Theme


class LogLevel(Enum):
    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40


def _log_formatter(record: "loguru.Record") -> str:
    """Log message formatter"""
    color_map = {
        "TRACE": "dim blue",
        "DEBUG": "cyan",
        "INFO": "not bold",
        "SUCCESS": "not bold green",
        "WARNING": "yellow",
        "ERROR": "not bold red",
        "CRITICAL": "not bold white on red",
    }
    lvl_color = color_map.get(record["level"].name, "cyan")
    return (
        "[not bold green]{time:YYYY-MM-DD HH:mm:ss}[/not bold green] | "
        + f"[{lvl_color}]{{message}}[/{lvl_color}]"
    )


console = Console(
    file=sys.stdout,
    log_time=False,
    log_path=False,
    theme=Theme(
        {
            "logging.level.trace": "gray42",
            "logging.level.debug": "white",
            "logging.level.info": "bright_blue",
            "logging.level.success": "green",
            "logging.level.warning": "orange1",
            "logging.level.error": "red",
        }
    ),
)


class CustomLogger:
    """
    The CustomLogger class adds custom levels to the Loguru logger.
    """

    def __init__(self, logger: "loguru.Logger"):
        self.logger = logger

    def trace(
        self, msg: str, *args: Union[str, int, float], **kwargs: Union[str, int, float]
    ) -> None:
        self.logger.log(LogLevel.TRACE.value, msg, *args, **kwargs)

    def debug(
        self, msg: str, *args: Union[str, int, float], **kwargs: Union[str, int, float]
    ) -> None:
        self.logger.log(LogLevel.DEBUG.value, msg, *args, **kwargs)

    def info(
        self, msg: str, *args: Union[str, int, float], **kwargs: Union[str, int, float]
    ) -> None:
        self.logger.log(LogLevel.INFO.value, msg, *args, **kwargs)

    def success(
        self, msg: str, *args: Union[str, int, float], **kwargs: Union[str, int, float]
    ) -> None:
        self.logger.log(LogLevel.SUCCESS.value, msg, *args, **kwargs)

    def warning(
        self, msg: str, *args: Union[str, int, float], **kwargs: Union[str, int, float]
    ) -> None:
        self.logger.log(LogLevel.WARNING.value, msg, *args, **kwargs)

    def error(
        self,
        msg: Union[str, Exception],
        *args: Union[str, int, float],
        **kwargs: Union[str, int, float],
    ) -> None:
        if isinstance(msg, Exception):
            msg = self._log_exception(msg)
        self.logger.log(LogLevel.ERROR.value, msg, *args, **kwargs)

    def _log_exception(self, e: Exception) -> str:
        """Log exception message"""
        exc_type = type(e).__name__
        exc_msg = str(e)
        return f"{exc_type}: {exc_msg}"


def create_logger(console: Console) -> CustomLogger:
    """
    The function creates a custom logger.

    Returns:
      CustomLogger: Custom logger
    """
    custom_logger.remove()
    custom_logger.add(console.print, colorize=True, format=_log_formatter)
    return CustomLogger(custom_logger)


logger = create_logger(console=console)


def _format_time(seconds: Optional[float]) -> str:
    """Formats seconds to readable time string.
    This function is used to display time in progress bar.
    """
    if not seconds:
        return "--:--"

    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class TimeColumn(ProgressColumn):
    """Renders total time, ETA, and speed in progress bar."""

    max_refresh = 0.5  # Only refresh twice a second to prevent jitter

    def render(self, task: Task) -> Text:
        elapsed_time = _format_time(task.elapsed)
        speed = f"{task.speed:.2f}/s" if task.speed else "?/s"
        return Text(f"[{elapsed_time}, {speed}]", style="progress.remaining")


# class CustomProgressColumn(ProgressColumn):
#     def render(self, task: Task) -> Text:
#         completed = task.completed
#         total = task.total
#         elapsed_time = task.finished - task.started
#         average_time = elapsed_time / completed if completed else 0
#         return (
#             f"Completed: {completed}/{total} Avg. time per request: {average_time:.2f}s"
#         )
