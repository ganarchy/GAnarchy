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
import ganarchy.data

@ganarchy.cli.main.group()
def debug():
    pass

@debug.command()
def paths():
    click.echo('Config home: {}'.format(ganarchy.config_home))
    click.echo('Additional config search path: {}'.format(ganarchy.config_dirs))
    click.echo('Cache home: {}'.format(ganarchy.cache_home))
    click.echo('Data home: {}'.format(ganarchy.data_home))

def print_data_source(data_source):
    if ganarchy.data.DataProperty.INSTANCE_TITLE in data_source.get_supported_properties():
        try:
            title = data_source.get_property_value(ganarchy.data.DataProperty.INSTANCE_TITLE)
        except LookupError:
            title = None
        click.echo("\tTitle: {}".format(title))

    if ganarchy.data.DataProperty.INSTANCE_BASE_URL in data_source.get_supported_properties():
        try:
            base_url = data_source.get_property_value(ganarchy.data.DataProperty.INSTANCE_BASE_URL)
        except LookupError:
            base_url = None
        click.echo("\tBase URL: {}".format(base_url))

    if ganarchy.data.DataProperty.REPO_LIST_SOURCES in data_source.get_supported_properties():
        click.echo("\tRepo list sources:")
        try:
            iterator = data_source.get_property_values(ganarchy.data.DataProperty.REPO_LIST_SOURCES)
        except LookupError:
            click.echo("\t\tNone")
        else:
            for i, rls in enumerate(iterator, 1):
                click.echo("\t\t{}.".format(i))
                click.echo("\t\t\tURI: {}".format(rls.uri))
                click.echo("\t\t\tOptions: {}".format(rls.options))
                click.echo("\t\t\tActive: {}".format(rls.active))

    if ganarchy.data.DataProperty.VCS_REPOS in data_source.get_supported_properties():
        click.echo("\tRepos:")
        try:
            iterator = data_source.get_property_values(ganarchy.data.DataProperty.VCS_REPOS)
        except LookupError:
            click.echo("\t\tNone")
        else:
            for i, pctp in enumerate(iterator, 1):
                click.echo("\t\t{}.".format(i))
                click.echo("\t\t\tProject: {}".format(pctp.project_commit))
                click.echo("\t\t\tURI: {}".format(pctp.uri))
                click.echo("\t\t\tBranch: {}".format(pctp.branch))
                click.echo("\t\t\tOptions: {}".format(pctp.options))
                click.echo("\t\t\tActive: {}".format(pctp.active))

@debug.command()
def configs():
    confs = ganarchy.data.ConfigManager.new_default()
    click.echo("Configs (raw): {}".format(confs.sources))
    click.echo("Breaking down the configs.")
    update_excs = confs.update()
    for conf, exc in zip(reversed(confs.sources), reversed(update_excs)):
        click.echo("Config: {}".format(conf))
        if exc is not None:
            click.echo("\tError(s): {}".format(exc))
        if conf.exists():
            print_data_source(conf)
    click.echo("ConfigManager (raw):")
    print_data_source(confs)
    click.echo("ConfigManager (effective):")
    print_data_source(ganarchy.data.EffectiveSource(confs))

@debug.command()
def repo_lists():
    confs = ganarchy.data.ConfigManager.new_default()
    repo_lists = ganarchy.data.RepoListManager(confs)
    update_excs = repo_lists.update()
    click.echo("Repo lists (raw): {}".format(repo_lists.sources))
    click.echo("Breaking down the repo lists.")
    for repo_list, exc in zip(reversed(repo_lists.sources), reversed(update_excs)):
        click.echo("Repo list: {}".format(repo_list))
        if exc is not None:
            click.echo("\tError(s): {}".format(exc))
        if repo_list.exists():
            print_data_source(repo_list)
    click.echo("RepoListManager (raw):")
    print_data_source(repo_lists)
    click.echo("RepoListManager (effective):")
    print_data_source(ganarchy.data.EffectiveSource(repo_lists))

