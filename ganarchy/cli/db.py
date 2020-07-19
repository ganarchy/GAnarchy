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

"""Database-related CLI commands.

"""

import os

import click

import ganarchy.cli
import ganarchy.data
import ganarchy.db
import ganarchy.dirs

@ganarchy.cli.main.command()
def initdb():
    """Initializes the ganarchy database."""
    # TODO: makedirs in a separate command?
    os.makedirs(ganarchy.dirs.DATA_HOME, exist_ok=True)
    db = ganarchy.db.connect_database(ganarchy.data.ConfigManager.new_default())
    db.initialize()
    db.close()

@ganarchy.cli.main.group()
def migrations():
    """Modifies the DB to work with a newer/older version.

    WARNING: THIS COMMAND CAN BE EXTREMELY DESTRUCTIVE!"""

@migrations.command()
@click.argument('migration')
def apply(migration):
    """Applies the migration with the given name."""
    db = ganarchy.db.connect_database(ganarchy.data.ConfigManager.new_default())
    click.echo(ganarchy.db.MIGRATIONS[migration][0])
    db.apply_migration(migration)
    db.close()

@click.argument('migration')
@migrations.command()
def revert(migration):
    """Reverts the migration with the given name."""
    db = ganarchy.db.connect_database(ganarchy.data.ConfigManager.new_default())
    click.echo(ganarchy.db.MIGRATIONS[migration][1])
    db.revert_migration(migration)
    db.close()

@click.argument('migration', required=False)
@migrations.command()
def info(migration):
    """Shows information about the migration with the given name."""
    if not migration:
        # TODO could be improved
        click.echo(ganarchy.db.MIGRATIONS.keys())
    else:
        click.echo(ganarchy.db.MIGRATIONS[migration][2])
