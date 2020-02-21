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
import qtoml

import ganarchy
import ganarchy.cli
import ganarchy.config

@ganarchy.cli.main.group()
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
    def print_conf(conf):
        click.echo("\tRepos:")
        for i, pctp in enumerate(conf.get_project_commit_tree_paths()):
            click.echo("\t\t{}.".format(i))
            click.echo("\t\t\tProject: {}".format(pctp.project_commit))
            click.echo("\t\t\tURI: {}".format(pctp.uri))
            click.echo("\t\t\tBranch: {}".format(pctp.branch))
            click.echo("\t\t\tActive: {}".format(pctp.options == {'active': True}))

    confs = ganarchy.config.ConfigManager.new_default()
    click.echo("Configs: {}".format(confs.sources))
    click.echo("Breaking down the configs.")
    for conf in reversed(confs.sources):
        click.echo("Config: {}".format(conf.filename))
        e = conf.update()
        if e is None:
            print_conf(conf)
        else:
            click.echo("\tError: {}".format(e))
