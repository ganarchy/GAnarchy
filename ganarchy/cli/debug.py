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
        for i, repo in enumerate(ganarchy.config.CONFIG_REPOS.match({'projects': conf.projects})):
            click.echo("\t\t{}.".format(i))
            click.echo("\t\t\tProject: {}".format(repo['commit'][0]))
            click.echo("\t\t\tURI: {}".format(repo['url'][0]))
            click.echo("\t\t\tBranch: {}".format(repo['branch'][0]))
            click.echo("\t\t\tActive: {}".format(repo['branch'][1] == {'active': True}))

    click.echo("Breaking down the configs.")
    conf = None
    # reverse order is intentional
    for d in reversed(ganarchy.config_dirs):
        click.echo("Config: {}/config.toml".format(d))
        try:
            f = open(d + "/config.toml", 'r', encoding='utf-8', newline='')
            conf = ganarchy.Config(f, conf)
            click.echo("Updated entries:")
            print_conf(conf)
            f.close()
        except (OSError, UnicodeDecodeError, qtoml.decoder.TOMLDecodeError) as e:
            click.echo("\tError: {}".format(e))
    try:
        click.echo("Config: {}/config.toml".format(ganarchy.config_home))
        f = open(ganarchy.config_home + "/config.toml", 'r', encoding='utf-8', newline='')
        conf = ganarchy.Config(f, conf)
        click.echo("Updated entries:")
        print_conf(conf)
        click.echo("-----")
        click.echo("\tTitle: {}".format(conf.base_url))
        click.echo("\tBase URI: {}".format(conf.base_url))
        f.close()
    except (OSError, UnicodeDecodeError, qtoml.decoder.TOMLDecodeError) as e:
        click.echo("\tError: {}".format(e))
