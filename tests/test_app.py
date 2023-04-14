#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import os
from os import path

# from ap_faas.app import run_experiment

# External imports
# import pytest


# from unittest.mock import MagicMock, patch


def test_run_experiment() -> None:
    sample_yaml = "config/test.yaml"

    # Set project base path
    BASE_DIR = path.abspath(path.join(__file__, ".."))

    sample_yaml = path.abspath(path.join(BASE_DIR, sample_yaml))

    print(sample_yaml)

    assert os.path.exists(sample_yaml)

    # call the function with the test arguments

    # run_experiment(config, "test_exp")

    # with patch("ap_faas.main.fetcher", MagicMock()) as fetcher_mock:
    #     with patch(
    #         "ap_faas.main.generate_sample", MagicMock(return_value="sample_data")
    #     ) as generate_sample_mock:
    #         with patch("ap_faas.main.write_file", MagicMock()) as write_file_mock:
    #             filename = "test_config.json"
    #             exp_name = "Test Experiment"

    #             run_experiment(filename, exp_name)

    #             fetcher_mock.assert_called_once_with(
    #                 config, f"{main.OUTPUT_DIR}/timestamp_{exp_name}", "sample_data"
    #             )
    #             generate_sample_mock.assert_called_once_with(config)
    #             write_file_mock.assert_called_once()
