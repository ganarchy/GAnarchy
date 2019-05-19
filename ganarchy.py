#!/usr/bin/env python3

# GAnarchy - project homepage generator
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

import sqlite3
import click
import os
import subprocess
import hashlib
import hmac
import jinja2

# default HTML, can be overridden in $XDG_DATA_HOME/ganarchy/template.html or the $XDG_DATA_DIRS (TODO)
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <!--
        GAnarchy - project homepage generator
        Copyright (C) 2019  Soni L.

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU Affero General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU Affero General Public License for more details.

        You should have received a copy of the GNU Affero General Public License
        along with this program.  If not, see <https://www.gnu.org/licenses/>.
        -->
        <title>{{ project_title|e }}</title>
        {% if project_desc %}<meta name="description" content="{{ project_desc|e }}" />{% endif %}
        <style type="text/css">.branchname { color: #808080; font-style: italic; }</style>
    </head>
    <body>
        <h1>{{ project_title|e }}</h1>
        <p>Tracking <span id="project_commit"><a href="web+ganarchy:{{ project_commit }}">{{ project_commit }}</a></span></p>
        <div id="project_body"><p>{{ project_body|e|replace("\n\n", "</p><p>") }}</p></div>
        <ul>
        {% for url, msg, img, branch in repos -%}
            <li><a href="{{ url|e }}">{{ url|e }}</a>{% if branch %} <span class="branchname">[{{ branch|e }}]</span>{% endif %}: {{ msg|e }}</li>
        {%- endfor %}
        </ul>
        <p>Powered by <a href="https://ganarchy.autistic.space/">GAnarchy</a>. AGPLv3-licensed. <a href="https://cybre.tech/SoniEx2/ganarchy">Source Code</a>.</p>
        <p>
            <a href="/">Main page</a>.
            <a href="{{ base_url|e }}" onclick="event.preventDefault(); navigator.registerProtocolHandler('web+ganarchy', this.href + '?url=%s', 'GAnarchy');">Register web+ganarchy: URI handler</a>.
        </p>
    </body>
</html>
"""

MIGRATIONS = {
        "better-project-management": (
                (
                    """ALTER TABLE "repos" ADD COLUMN "branch" TEXT""",
                    """ALTER TABLE "repos" ADD COLUMN "project" TEXT""",
                    """CREATE UNIQUE INDEX "repos_url_branch_project" ON "repos" ("url", "branch", "project")""",
                    """CREATE INDEX "repos_project" ON "repos" ("project")""",
                    """ALTER TABLE "repo_history" ADD COLUMN "branch" TEXT""",
                    """ALTER TABLE "repo_history" ADD COLUMN "project" TEXT""",
                    """CREATE INDEX "repo_history_url_branch_project" ON "repo_history" ("url", "branch", "project")"""),
                (
                    """DELETE FROM "repos" WHERE "branch" IS NOT NULL OR "project" IS NOT NULL""",
                    """DELETE FROM "repo_history" WHERE "branch" IS NOT NULL OR "project" IS NOT NULL"""),
                "supports multiple projects, and allows choosing non-default branches"
            ),
        "test": (
                ("""-- apply""",),
                ("""-- revert""",),
                "does nothing"
            )
        }

try:
    data_home = os.environ['XDG_DATA_HOME']
except KeyError:
    data_home = ''
if not data_home:
    data_home = os.environ['HOME'] + '/.local/share'
data_home = data_home + "/ganarchy"

try:
    cache_home = os.environ['XDG_CACHE_HOME']
except KeyError:
    cache_home = ''
if not cache_home:
    cache_home = os.environ['HOME'] + '/.cache'
cache_home = cache_home + "/ganarchy"

@click.group()
def ganarchy():
    pass

@ganarchy.command()
def initdb():
    """Initializes the ganarchy database."""
    os.makedirs(data_home, exist_ok=True)
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE "repos" ("url" TEXT PRIMARY KEY, "active" INT, "branch" TEXT, "project" TEXT)''')
    c.execute('''CREATE UNIQUE INDEX "repos_url_branch_project" ON "repos" ("url", "branch", "project")''')
    c.execute('''CREATE INDEX "repos_project" ON "repos" ("project")''')
    c.execute('''CREATE INDEX "repos_active" ON "repos" ("active")''')
    c.execute('''CREATE TABLE "repo_history" ("entry" INTEGER PRIMARY KEY ASC AUTOINCREMENT, "url" TEXT, "count" INTEGER, "head_commit" TEXT, "branch" TEXT, "project" TEXT)''')
    c.execute('''CREATE INDEX "repo_history_url_branch_project" ON "repo_history" ("url", "branch", "project")''')
    c.execute('''CREATE TABLE "config" ("git_commit" TEXT, "base_url" TEXT)''')
    c.execute('''INSERT INTO "config" VALUES ('', '')''')
    conn.commit()
    conn.close()

@ganarchy.command()
@click.argument('commit')
def set_commit(commit):
    """Sets the commit that represents the project."""
    import re
    if not re.fullmatch("[a-fA-F0-9]{40}", commit):
        raise click.BadArgumentUsage("COMMIT must be a git commit hash")
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE "config" SET "git_commit"=?''', (commit,))
    conn.commit()
    conn.close()

@ganarchy.command()
@click.argument('base-url')
def set_base_url(base_url):
    """Sets the GAnarchy instance's base URL."""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE "config" SET "base_url"=?''', (base_url,))
    conn.commit()
    conn.close()

# TODO move --branch into here?
@ganarchy.group()
def repo():
    """Modifies repos to track."""

@repo.command()
@click.option('--branch', default=None, help="Sets the branch to be used for the repo")
@click.option('--project', default=None, help="Sets the project commit to be used for the repo")
@click.option('--disabled', default=False, is_flag=True, help="Mark the repo as disabled")
@click.argument('url')
def add(branch, project, disabled, url):
    """Adds a repo to track."""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''SELECT "git_commit", "base_url" FROM "config"''')
    (project_commit, base_url) = c.fetchone()
    if project_commit == project:
        project = None
    c.execute('''INSERT INTO "repos" ("url", "active", "branch", "project") VALUES (?, ?, ?, ?)''', (url, int(not disabled), branch, project))
    conn.commit()
    conn.close()

@repo.command()
@click.option('--branch', default=None, help="Sets the branch to be used for the repo")
@click.option('--project', default=None, help="Sets the project commit to be used for the repo")
@click.argument('url')
def enable(branch, project, url):
    """Enables tracking of a repo."""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''SELECT "git_commit", "base_url" FROM "config"''')
    (project_commit, base_url) = c.fetchone()
    if project_commit == project:
        project = None
    c.execute('''UPDATE "repos" SET "active"=1 WHERE "url"=? AND "branch" IS ? AND "project" IS ?''', (url, branch, project))
    conn.commit()
    conn.close()

@repo.command()
@click.option('--branch', default=None, help="Sets the branch to be used for the repo")
@click.option('--project', default=None, help="Sets the project commit to be used for the repo")
@click.argument('url')
def disable(branch, project, url):
    """Disables tracking of a repo."""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''SELECT "git_commit", "base_url" FROM "config"''')
    (project_commit, base_url) = c.fetchone()
    if project_commit == project:
        project = None
    c.execute('''UPDATE repos SET "active"=0 WHERE "url"=? AND "branch" IS ? AND "project" IS ?''', (url, branch, project))
    conn.commit()
    conn.close()

@repo.command()
@click.option('--branch', default=None, help="Sets the branch to be used for the repo")
@click.option('--project', default=None, help="Sets the project commit to be used for the repo")
@click.argument('url')
def remove(branch, project, url):
    """Stops tracking a repo."""
    click.confirm("WARNING: This operation does not delete the commits associated with the given repo! Are you sure you want to continue? This operation cannot be undone.")
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''SELECT "git_commit", "base_url" FROM "config"''')
    (project_commit, base_url) = c.fetchone()
    if project_commit == project:
        project = None
    c.execute('''DELETE FROM "repos" WHERE "url"=? AND "branch" IS ? AND "project" IS ?''', (url, branch, project))
    c.execute('''DELETE FROM "repo_history" WHERE "url"=? AND "branch" IS ? AND "project" IS ?''', (url, branch, project))
    conn.commit()
    conn.close()

def migrations():
    @ganarchy.group()
    def migrations():
        """Modifies the DB to work with a newer/older version.

        WARNING: THIS COMMAND CAN BE EXTREMELY DESTRUCTIVE!"""

    @migrations.command()
    @click.argument('migration')
    def apply(migration):
        """Applies the migration with the given name."""
        conn = sqlite3.connect(data_home + "/ganarchy.db")
        c = conn.cursor()
        click.echo(MIGRATIONS[migration][0])
        for migration in MIGRATIONS[migration][0]:
            c.execute(migration)
        conn.commit()
        conn.close()

    @click.argument('migration')
    @migrations.command()
    def revert(migration):
        """Reverts the migration with the given name."""
        conn = sqlite3.connect(data_home + "/ganarchy.db")
        c = conn.cursor()
        click.echo(MIGRATIONS[migration][1])
        for migration in MIGRATIONS[migration][1]:
            c.execute(migration)
        conn.commit()
        conn.close()

    @click.argument('migration', required=False)
    @migrations.command()
    def info(migration):
        """Shows information about the migration with the given name."""
        if not migration:
            # TODO could be improved
            click.echo(MIGRATIONS.keys())
        else:
            click.echo(MIGRATIONS[migration][2])

migrations()

@ganarchy.command()
@click.argument('project', required=False)
def cron_target(project):
    """Runs ganarchy as a cron target."""
    def handle_target(url, branch, project_commit):
        if not branch:
            branchname = "gan" + hashlib.sha256(url.encode("utf-8")).hexdigest()
            branch = "HEAD"
        else:
            branchname = "gan" + hmac.new(branch.encode("utf-8"), url.encode("utf-8"), "sha256").hexdigest()
            branch = "refs/heads/" + branch
        try:
            pre_hash = subprocess.check_output(["git", "-C", cache_home, "show", branchname, "-s", "--format=%H", "--"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        except subprocess.CalledProcessError:
            pre_hash = None
        try:
            subprocess.check_output(["git", "-C", cache_home, "fetch", "-q", url, "+" + branch + ":" + branchname], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # This may error for various reasons, but some are important: dead links, etc
            click.echo(e.output, err=True)
            return None
        post_hash = subprocess.check_output(["git", "-C", cache_home, "show", branchname, "-s", "--format=%H", "--"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        if not pre_hash:
            pre_hash = post_hash
        try:
            count = int(subprocess.check_output(["git", "-C", cache_home, "rev-list", "--count", pre_hash + ".." + post_hash, "--"]).decode("utf-8").strip())
        except subprocess.CalledProcessError:
            count = 0  # force-pushed
        try:
            subprocess.check_call(["git", "-C", cache_home, "merge-base", "--is-ancestor", project_commit, branchname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return count, post_hash, subprocess.check_output(["git", "-C", cache_home, "show", branchname, "-s", "--format=%B", "--"], stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except subprocess.CalledProcessError:
            return None
    os.makedirs(cache_home, exist_ok=True)
    subprocess.call(["git", "-C", cache_home, "init", "-q"])
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''SELECT "git_commit", "base_url" FROM "config"''')
    (project_commit, base_url) = c.fetchone()
    if not base_url or not (project or project_commit):
        click.echo("No base URL or project commit specified", err=True)
        return
    if project_commit == project:
        project = None
    elif project is not None:
        project_commit = project
    entries = []
    generate_html = []
    for (e, url, branch) in c.execute('''SELECT "max"("e"), "url", "branch" FROM (SELECT "max"("T1"."entry") "e", "T1"."url", "T1"."branch" FROM "repo_history" "T1"
                                                        WHERE (SELECT "active" FROM "repos" "T2" WHERE "url" = "T1"."url" AND "branch" IS "T1"."branch" AND "project" IS ?1)
                                                        GROUP BY "T1"."url", "T1"."branch"
                                                        UNION
                                                        SELECT null, "T3"."url", "T3"."branch" FROM "repos" "T3" WHERE "active" AND "project" IS ?1)
                               GROUP BY "url" ORDER BY "e"''', (project,)):
        result = handle_target(url, branch, project_commit)
        if result is not None:
            count, post_hash, msg = result
            entries.append((url, count, post_hash, branch, project))
            generate_html.append((url, msg, count, branch))
    # sort stuff twice because reasons
    entries.sort(key=lambda x: x[1], reverse=True)
    generate_html.sort(key=lambda x: x[2], reverse=True)
    c.executemany('''INSERT INTO "repo_history" ("url", "count", "head_commit", "branch", "project") VALUES (?, ?, ?, ?, ?)''', entries)
    conn.commit()
    html_entries = []
    for (url, msg, count, branch) in generate_html:
        history = c.execute('''SELECT "count" FROM "repo_history" WHERE "url" = ? AND "branch" IS ? AND "project" IS ? ORDER BY "entry" ASC''', (url, branch, project)).fetchall()
        # TODO process history into SVG
        html_entries.append((url, msg, "", branch))
    template = jinja2.Template(TEMPLATE)
    import re
    project = subprocess.check_output(["git", "-C", cache_home, "show", project_commit, "-s", "--format=%B", "--"], stderr=subprocess.DEVNULL).decode("utf-8", "replace")
    project_title, project_desc = (lambda x: x.groups() if x is not None else ('', None))(re.fullmatch('^\\[Project\\]\s+(.+?)(?:\n\n(.+))?$', project, flags=re.ASCII|re.DOTALL|re.IGNORECASE))
    if not project_title.strip():
        project_title, project_desc = ("Error parsing project commit",)*2
    if project_desc:
        project_desc = project_desc.strip()
    click.echo(template.render(project_title  = project_title,
                               project_desc   = project_desc,
                               project_body   = project,
                               project_commit = project_commit,
                               repos          = html_entries,
                               base_url       = base_url))

if __name__ == "__main__":
    ganarchy()
