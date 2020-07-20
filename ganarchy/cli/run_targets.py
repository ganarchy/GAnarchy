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

import click

from ganarchy import cli
from ganarchy import core
from ganarchy import data
from ganarchy import db
from ganarchy import dirs
from ganarchy.templating import environment

#@cli.main.command()
#@click.argument('out', required=True)
#def run(out):
#    """Runs ganarchy standalone.
#
#    This will run ganarchy so it regularly updates the output directory given by OUT.
#    Additionally, it'll also search for the following hooks in its config dirs:
#
#        - post_object_update_hook - executed after an object is updated.
#
#        - post_update_cycle_hook - executed after all objects in an update cycle are updated."""
#    pass

@cli.main.command()
@click.option('--update/--no-update', default=True)
@click.argument('project', required=False)
def cron_target(update, project):
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
        click.echo(template.render(database=database))
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
        click.echo(template.render(ganarchy=instance))
        return

    # FIXME this should be in core, as it belongs to core logic!
    entries = []
    generate_html = []
    c = conn.cursor()
    p = Project(conn, project, list_repos=True)
    results = p.update(update)
    for (repo, count) in results:
        if count is not None:
            entries.append((repo.url, count, repo.hash, repo.branch, project))
            generate_html.append((repo.url, repo.message, count, repo.branch))
    # sort stuff twice because reasons
    entries.sort(key=lambda x: x[1], reverse=True)
    generate_html.sort(key=lambda x: x[2], reverse=True)
    if update:
        c.executemany('''INSERT INTO "repo_history" ("url", "count", "head_commit", "branch", "project") VALUES (?, ?, ?, ?, ?)''', entries)
        conn.commit()
    html_entries = []
    for (url, msg, count, branch) in generate_html:
        history = c.execute('''SELECT "count" FROM "repo_history" WHERE "url" = ? AND "branch" IS ? AND "project" IS ? ORDER BY "entry" ASC''', (url, branch, project)).fetchall()
        # TODO process history into SVG
        html_entries.append((url, msg, "", branch))
    template = env.get_template('project.html')
    click.echo(template.render(project_title  = p.title,
                               project_desc   = p.description,
                               project_body   = p.commit_body,
                               project_commit = p.commit,
                               repos          = html_entries,
                               base_url       = instance.base_url,
                               # I don't think this thing supports deprecating the above?
                               project        = p,
                               ganarchy       = instance))
