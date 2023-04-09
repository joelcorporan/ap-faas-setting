#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


class TracesInterface:
    """
    This is an interface for handling cloud provider traces.

    Attributes:
      function (str): function name
      credectials (dict): Cloud provider credentials.
      experimental_results (dict): Experimental results from fetcher.
    """

    def __init__(self, function: str, credentials: dict, config_file: dict) -> None:
        """
        The constructor for Traces class.

        Parameters:
          function (str): function name
          credectials (dict): Cloud provider credentials.
        """

    def get_traces_per_request(self, limit: int, resolution: int) -> list:
        """
        The function retrieves the trace from each function.

        Parameters:
          limit (int): Record limit of retrieval.

        Returns:
          list: List of dictionaries with traces
        """
        raise NotImplementedError("Subclass must implement abstract method")
