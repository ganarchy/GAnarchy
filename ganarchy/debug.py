# This file is part of GAnarchy - decentralized project hub
# Copyright (C) 2019  Soni L.
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

import click

import ganarchy
import ganarchy.config

@ganarchy.ganarchy.group()
def debug():
    pass

@debug.command()
def paths():
    click.echo('Config home: {}'.format(ganarchy.config_home))
    click.echo('Additional config search path: {}'.format(ganarchy.config_dirs))
    click.echo('Cache home: {}'.format(ganarchy.cache_home))
    click.echo('Data home: {}'.format(ganarchy.data_home))

@debug.command()
def configs():
    pass

