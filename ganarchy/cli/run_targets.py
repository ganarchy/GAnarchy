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

"""This module contains the CLI Run Targets.
"""

import os
import shutil

import click

from ganarchy import cli
from ganarchy import core
from ganarchy import data
from ganarchy import db
from ganarchy import dirs
from ganarchy.templating import environment

@cli.main.command()
@click.option('--keep-stale-projects/--no-keep-stale-projects', default=True)
@click.argument('out', required=True, type=click.Path(file_okay=False, resolve_path=True))
def run_once(out, keep_stale_projects):
    """Runs GAnarchy once.

    Processes any necessary updates and updates the output directory to match.
    """
#    """Runs ganarchy standalone.
#
#    This will run ganarchy so it regularly updates the output directory given
#    by OUT. Additionally, it'll also search for the following hooks in its
#    config dirs:
#
#        - post_object_update_hook - executed after an object is updated.
#
#        - post_update_cycle_hook - executed after all objects in an update
#            cycle are updated.
#    """
    # create config objects
    conf = data.ConfigManager.new_default()
    effective_conf = data.EffectiveSource(conf)
    repos = data.RepoListManager(effective_conf)
    effective_repos = data.EffectiveSource(repos)

    # create dir if it doesn't exist
    os.makedirs(out, exist_ok=True)

    # load template environment
    env = environment.get_env()

    # make sure the cache dir exists
    os.makedirs(dirs.CACHE_HOME, exist_ok=True)

    # make sure it is a git repo
    core.GIT.create()

    if True:
        # reload config and repo data
        effective_repos.update()
        database = db.connect_database(effective_conf)
        database.load_repos(effective_repos)

        instance = core.GAnarchy(database, effective_conf)

        if not instance.base_url:
            click.echo("No base URL specified", err=True)
            return

        instance.load_projects()

        # update and render projects
        if not keep_stale_projects:
            shutil.rmtree(out + "/project")

        os.makedirs(out + "/project", exist_ok=True)

        template_project = env.get_template('project.html')
        for p in instance.projects:
            p.load_repos()

            generate_html = []
            results = p.update()
            #if not p.exists:
            #    ...
            for (repo, count) in results:
                if count is not None:
                    generate_html.append(
                        (repo.url, repo.message, count, repo.branch)
                    )
                else:
                    click.echo(repo.url, err=True)
                    click.echo(repo.branch, err=True)
                    click.echo(repo.errormsg, err=True)
            html_entries = []
            for (url, msg, count, branch) in generate_html:
                history = database.list_repobranch_activity(p.commit, url, branch)
                # TODO process history into SVG
                # TODO move this into a separate system
                # (e.g. ``if project.startswith("svg-"):``)
                html_entries.append((url, msg, "", branch))

            os.makedirs(out + "/project/" + p.commit, exist_ok=True)

            with open(out + "/project/" + p.commit + "/index.html", "w") as f:
                template_project.stream(
                    project_title  = p.title,
                    project_desc   = p.description,
                    project_body   = p.commit_body,
                    project_commit = p.commit,
                    repos          = html_entries,
                    base_url       = instance.base_url,
                    # I don't think this thing supports deprecating the above?
                    project        = p,
                    ganarchy       = instance
                ).dump(f)

        # render the config
        template = env.get_template('index.toml')
        with open(out + "/index.toml", "w") as f:
            template.stream(database=database).dump(f)

        # render the index
        # but reload projects first to pick up sorting order
        # (new projects don't get sorted until their repos get fetched for the
        # first time, because that's where the metadata is stored)
        # FIXME .sort_projects()?
        instance.load_projects()
        template = env.get_template('index.html')
        with open(out + "/index.html", "w") as f:
            template.stream(ganarchy=instance).dump(f)


@cli.main.command()
@click.option('--dry-run/--no-dry-run', '--no-update/--update', default=False)
@click.argument('project', required=False)
def cron_target(dry_run, project):
    """Runs ganarchy as a cron target.

    "Deprecated". Useful if you want full control over how GAnarchy
    generates the pages.
    """
    # create config objects
    conf = data.ConfigManager.new_default()
    effective_conf = data.EffectiveSource(conf)
    repos = data.RepoListManager(effective_conf)
    effective_repos = data.EffectiveSource(repos)

    # load config and repo data
    effective_repos.update()
    database = db.connect_database(effective_conf)
    database.load_repos(effective_repos)

    # load template environment
    env = environment.get_env()

    # handle config and project list
    if project == "config":
        # render the config
        template = env.get_template('index.toml')
        click.echo(template.render(database=database), nl=False)
        return
    if project == "project-list":
        # could be done with a template but eh w/e, this is probably better
        for project in database.list_projects():
            click.echo(project)
        return

    # make sure the cache dir exists
    os.makedirs(dirs.CACHE_HOME, exist_ok=True)

    # make sure it is a git repo
    core.GIT.create()

    instance = core.GAnarchy(database, effective_conf)

    if not instance.base_url or not project:
        click.echo("No base URL or project commit specified", err=True)
        return

    if project == "index":
        instance.load_projects()
        # render the index
        template = env.get_template('index.html')
        click.echo(template.render(ganarchy=instance), nl=False)
        return

    p = core.Project(database, project)
    p.load_repos()

    generate_html = []
    results = p.update(dry_run=dry_run)
    #if not p.exists:
    #    ...
    for (repo, count) in results:
        if count is not None:
            generate_html.append((repo.url, repo.message, count, repo.branch))
        else:
            click.echo(repo.errormsg, err=True)
    html_entries = []
    for (url, msg, count, branch) in generate_html:
        history = database.list_repobranch_activity(project, url, branch)
        # TODO process history into SVG
        # TODO move this into a separate system
        # (e.g. ``if project.startswith("svg-"):``)
        html_entries.append((url, msg, "", branch))

    template = env.get_template('project.html')
    click.echo(
        template.render(
            project_title  = p.title,
            project_desc   = p.description,
            project_body   = p.commit_body,
            project_commit = p.commit,
            repos          = html_entries,
            base_url       = instance.base_url,
            # I don't think this thing supports deprecating the above?
            project        = p,
            ganarchy       = instance
        ),
        nl=False
    )
