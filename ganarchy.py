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
<title>{{ project_title }}</title>
</head>
<body>
<ul>
{% for url, msg, img in repos %}
    <li><a href="{{ url|e }}">{{ url|e }}</a>: {{ msg|e }}</li>
{% endfor %}
</ul>
Powered by <a href="https://ganarchy.autistic.space/">GAnarchy</a>. AGPLv3-licensed. <a href="https://cybre.tech/SoniEx2/ganarchy">Source Code</a>.
</body>
</html>
"""

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
    """Initializes the ganarchy database"""
    os.makedirs(data_home, exist_ok=True)
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE repos (url TEXT PRIMARY KEY, active INT)''')
    c.execute('''CREATE TABLE repo_history (entry INTEGER PRIMARY KEY ASC AUTOINCREMENT, url TEXT, count INTEGER, head_commit TEXT)''')
    c.execute('''CREATE TABLE config (git_commit TEXT, project_title TEXT)''')
    c.execute('''INSERT INTO config VALUES ('', '')''')
    conn.commit()
    conn.close()

@ganarchy.command()
@click.argument('commit')
def set_commit(commit):
    """Sets the commit that represents the project"""
    import re
    if not re.fullmatch("[a-fA-F0-9]{40}", commit):
        raise click.BadArgumentUsage("COMMIT must be a git commit hash")
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE config SET git_commit=?''', (commit,))
    conn.commit()
    conn.close()

@ganarchy.command()
@click.argument('project-title')
def set_project_title(project_title):
    """Sets the project title"""
    import re
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE config SET project_title=?''', (project_title,))
    conn.commit()
    conn.close()

@ganarchy.group()
def repo():
    """Modifies repos to track"""

@repo.command()
@click.argument('url')
def add(url):
    """Adds a repo to track"""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''INSERT INTO repos VALUES (?, 0)''', (url,))
    conn.commit()
    conn.close()

@repo.command()
@click.argument('url')
def enable(url):
    """Enables tracking of a repo"""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE repos SET active=1 WHERE url=?''', (url,))
    conn.commit()
    conn.close()

@repo.command()
@click.argument('url')
def disable(url):
    """Disables tracking of a repo"""
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''UPDATE repos SET active=0 WHERE url=?''', (url,))
    conn.commit()
    conn.close()

@repo.command()
@click.argument('url')
def remove(url):
    """Stops tracking a repo"""
    click.confirm("WARNING: This operation does not delete the commits associated with the given repo! Are you sure you want to continue? This operation cannot be undone.")
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''DELETE FROM repos WHERE url=?''', (url,))
    c.execute('''DELETE FROM repo_history WHERE url=?''', (url,))
    conn.commit()
    conn.close()

@ganarchy.command()
def cron_target():
    """Runs ganarchy as a cron target"""
    def handle_target(url, project_commit):
        branchname = hashlib.sha256(url.encode("utf-8")).hexdigest()
        try:
            pre_hash = subprocess.check_output(["git", "-C", cache_home, "show", branchname, "-s", "--format=%H", "--"], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            pre_hash = None
        try:
            subprocess.check_output(["git", "-C", cache_home, "fetch", "-q", url, "+HEAD:" + branchname], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # This may error for various reasons, but some are important: dead links, etc
            click.echo(e.output, err=True)
            return None
        post_hash = subprocess.check_output(["git", "-C", cache_home, "show", branchname, "-s", "--format=%H", "--"], stderr=subprocess.DEVNULL)
        if not pre_hash:
            pre_hash = post_hash
        try:
            count = subprocess.check_output(["git", "-C", cache_home, "rev-list", "--count", pre_hash + ".." + post_hash])
        except subprocess.CalledProcessError:
            count = 0  # force-pushed
        try:
            subprocess.check_call(["git", "-C", cache_home, "merge-base", "--is-ancestor", project_commit, branchname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return count, post_hash, subprocess.check_output(["git", "-C", cache_home, "show", branchname, "-s", "--format=%B", "--"], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return None
    os.makedirs(cache_home, exist_ok=True)
    subprocess.call(["git", "-C", cache_home, "init", "-q"])
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''SELECT git_commit, project_title FROM config''')
    (project_commit, project_title) = c.fetchone()
    entries = []
    generate_html = []
    for (url,) in c.execute("""SELECT url FROM repos WHERE active == 1"""):
        result = handle_target(url, project_commit)
        if result is not None:
            count, post_hash, msg = result
            entries.append((url, count, post_hash))
            generate_html.append((url, msg))
    c.executemany('''INSERT INTO repo_history VALUES (NULL, ?, ?, ?)''', entries)
    conn.commit()
    html_entries = []
    for (url, msg) in generate_html:
        history = c.execute('''SELECT count FROM repo_history WHERE url == ? ORDER BY entry ASC''', (url,)).fetchall()
        # TODO process history into SVG
        html_entries.append((url, msg, ""))
    template = jinja2.Template(TEMPLATE)
    click.echo(template.render(project_title = project_title, repos = html_entries))

if __name__ == "__main__":
    ganarchy()
