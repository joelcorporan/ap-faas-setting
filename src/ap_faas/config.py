#!/usr/bin/env python3

# Copyright (c) 2022 Joel Corporan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# External imports
import os
from os import path

# Set project base path
BASE_DIR = path.abspath(path.join(__file__, "../../.."))

# Filepath to generated Data.
OUTPUT_DIR = path.join(BASE_DIR, "generated_data")

if not path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
