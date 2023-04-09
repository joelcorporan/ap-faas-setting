#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json

# External imports
import os

import jsonschema
import yaml
from jsonschema import validate

# Local imports
from ap_faas.config import BASE_DIR

with open(os.path.join(BASE_DIR, "schema.json"), "r") as file:
    schema_data = file.read()
config_schema = json.loads(schema_data)


def validate_config_file(config_file: dict) -> bool:
    """
    The function validates configuration file.

    Parameters:
      config_file (dict): Configuration file.

    Returns:
      bool: Validation
    """
    try:
        validate(instance=config_file, schema=config_schema)
        return True

    except jsonschema.exceptions.ValidationError as err:
        raise Exception(f"Error validating file: {err.message}")


def read_config_file(file_name: str, ext: str = ".json") -> dict:
    """
    The function reads file with configurations.

    Parameters:
      file_name (dict): Configuration file.
      ext (str): File extention.

    Returns:
      dict: Dictionary with configuration
    """
    try:
        with open(os.path.join(BASE_DIR, file_name), "r") as file:
            if ext in [".yaml", ".yml"]:
                config_file = yaml.safe_load(file)
            else:
                config_file = json.load(file)

        return config_file

    except (json.decoder.JSONDecodeError, yaml.YAMLError) as err:
        raise Exception(f"Error reading {ext} file: {err}")


def write_file(output_file_name: str, content: dict) -> bool:
    """
    The function writes JSON file with configurations.

    Parameters:
      output_file_name (str): Name and location of JSON file.
      content (str): Content to store.

    Returns:
      bool: Validation of storage
    """
    try:
        with open(output_file_name, "w") as outfile:
            json.dump(content, outfile, indent=2)

        return True

    except Exception as err:
        raise Exception(f"Error writing file: {err}")
