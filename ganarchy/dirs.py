# This file is part of GAnarchy - decentralized project hub
# Copyright (C) 2020  Soni L.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""This module handles GAnarchy's config, data and cache directories.

These are not XDG dirs. They're GAnarchy dirs. They're based on XDG
dirs but they're not XDG dirs.

Attributes:
    DATA_HOME (str): GAnarchy data home.
    CACHE_HOME (str): GAnarchy cache home.
    CONFIG_HOME (str): GAnarchy config home.
    CONFIG_DIRS (list of str): GAnarchy config dirs.
"""

import os

# need to check for unset or empty, ``.get`` only handles unset.

DATA_HOME = os.environ.get('XDG_DATA_HOME', '')
if not DATA_HOME:
    DATA_HOME = os.environ['HOME'] + '/.local/share'
DATA_HOME = DATA_HOME + "/ganarchy"

CACHE_HOME = os.environ.get('XDG_CACHE_HOME', '')
if not CACHE_HOME:
    CACHE_HOME = os.environ['HOME'] + '/.cache'
CACHE_HOME = CACHE_HOME + "/ganarchy"

CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME', '')
if not CONFIG_HOME:
    CONFIG_HOME = os.environ['HOME'] + '/.config'
CONFIG_HOME = CONFIG_HOME + "/ganarchy"

CONFIG_DIRS = os.environ.get('XDG_CONFIG_DIRS', '')
if not CONFIG_DIRS:
    CONFIG_DIRS = '/etc/xdg'
# TODO check if this is correct
CONFIG_DIRS = [config_dir + "/ganarchy" for config_dir in CONFIG_DIRS.split(':')]

