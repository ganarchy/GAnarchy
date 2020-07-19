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

_tomletrans = str.maketrans({
    0: '\\u0000', 1: '\\u0001', 2: '\\u0002', 3: '\\u0003', 4: '\\u0004',
    5: '\\u0005', 6: '\\u0006', 7: '\\u0007', 8: '\\b', 9: '\\t', 10: '\\n',
    11: '\\u000B', 12: '\\f', 13: '\\r', 14: '\\u000E', 15: '\\u000F',
    16: '\\u0010', 17: '\\u0011', 18: '\\u0012', 19: '\\u0013', 20: '\\u0014',
    21: '\\u0015', 22: '\\u0016', 23: '\\u0017', 24: '\\u0018', 25: '\\u0019',
    26: '\\u001A', 27: '\\u001B', 28: '\\u001C', 29: '\\u001D', 30: '\\u001E',
    31: '\\u001F', '"': '\\"', '\\': '\\\\'
    })

def tomlescape(value):
    """Escapes a string for use in a TOML string.

    Returns:
        str: The escaped string.
    """
    return value.translate(_tomletrans)
