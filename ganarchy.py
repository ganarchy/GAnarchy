#!/usr/bin/python3

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
    </head>
    <body>
        <h1>{{ project_title|e }}</h1>
        <p>Tracking <span id="project_commit"><a href="web+ganarchy:{{ project_commit }}">{{ project_commit }}</a></span></p>
        <div id="project_body"><p>{{ project_body|e|replace("\n\n", "</p><p>") }}</p></div>
        <ul>
        {% for url, msg, img in repos -%}
            <li><a href="{{ url|e }}">{{ url|e }}</a>: {{ msg|e }}</li>
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
        "test": ("-- apply", "-- revert", "does nothing")
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
    c.execute('''CREATE TABLE repos (url TEXT PRIMARY KEY, active INT)''')
    c.execute('''CREATE INDEX active_key ON repos (active)''')
    c.execute('''CREATE TABLE repo_history (entry INTEGER PRIMARY KEY ASC AUTOINCREMENT, url TEXT, count INTEGER, head_commit TEXT)''')
    c.execute('''CREATE INDEX url_key ON repo_history (url)''')
    c.execute('''CREATE TABLE config (git_commit TEXT, base_url TEXT)''')
    c.execute('''INSERT INTO config VALUES ('', '')''')
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
    c.execute('''UPDATE config SET git_commit=?''', (commit,))
    conn.commit()
    conn.close()

@ganarchy.command()
@click.argument('base-url')
def set_base_url(base_url):
    """Sets the GAnarchy instance's base URL."""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE config SET base_url=?''', (base_url,))
    conn.commit()
    conn.close()

@ganarchy.group()
def repo():
    """Modifies repos to track."""

@repo.command()
@click.argument('url')
def add(url):
    """Adds a repo to track."""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''INSERT INTO repos VALUES (?, 0)''', (url,))
    conn.commit()
    conn.close()

@repo.command()
@click.argument('url')
def enable(url):
    """Enables tracking of a repo."""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE repos SET active=1 WHERE url=?''', (url,))
    conn.commit()
    conn.close()

@repo.command()
@click.argument('url')
def disable(url):
    """Disables tracking of a repo."""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE repos SET active=0 WHERE url=?''', (url,))
    conn.commit()
    conn.close()

@repo.command()
@click.argument('url')
def remove(url):
    """Stops tracking a repo."""
    click.confirm("WARNING: This operation does not delete the commits associated with the given repo! Are you sure you want to continue? This operation cannot be undone.")
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''DELETE FROM repos WHERE url=?''', (url,))
    c.execute('''DELETE FROM repo_history WHERE url=?''', (url,))
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
        c.execute(MIGRATIONS[migration][0])
        conn.commit()
        conn.close()

    @click.argument('migration')
    @migrations.command()
    def revert(migration):
        """Reverts the migration with the given name."""
        conn = sqlite3.connect(data_home + "/ganarchy.db")
        c = conn.cursor()
        click.echo(MIGRATIONS[migration][1])
        c.execute(MIGRATIONS[migration][1])
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
def cron_target():
    """Runs ganarchy as a cron target."""
    def handle_target(url, project_commit):
        branchname = "gan" + hashlib.sha256(url.encode("utf-8")).hexdigest()
        try:
            pre_hash = subprocess.check_output(["git", "-C", cache_home, "show", branchname, "-s", "--format=%H", "--"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        except subprocess.CalledProcessError:
            pre_hash = None
        try:
            subprocess.check_output(["git", "-C", cache_home, "fetch", "-q", url, "+HEAD:" + branchname], stderr=subprocess.STDOUT)
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
    c.execute('''SELECT git_commit, base_url FROM config''')
    (project_commit, base_url) = c.fetchone()
    if not base_url or not project_commit:
        click.echo("No base URL or project commit specified", err=True)
        return
    entries = []
    generate_html = []
    for (e, url,) in c.execute("""SELECT max(e), url FROM (SELECT max(T1.entry) e, T1.url FROM repo_history T1
                                                        WHERE (SELECT active FROM repos T2 WHERE url = T1.url)
                                                        GROUP BY T1.url
                                                        UNION
                                                        SELECT null, T3.url FROM repos T3 WHERE active)
                               GROUP BY url ORDER BY e"""):
        result = handle_target(url, project_commit)
        if result is not None:
            count, post_hash, msg = result
            entries.append((url, count, post_hash))
            generate_html.append((url, msg, count))
    # sort stuff twice because reasons
    entries.sort(key=lambda x: x[1], reverse=True)
    generate_html.sort(key=lambda x: x[2], reverse=True)
    c.executemany('''INSERT INTO repo_history VALUES (NULL, ?, ?, ?)''', entries)
    conn.commit()
    html_entries = []
    for (url, msg, count) in generate_html:
        history = c.execute('''SELECT count FROM repo_history WHERE url == ? ORDER BY entry ASC''', (url,)).fetchall()
        # TODO process history into SVG
        html_entries.append((url, msg, ""))
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
