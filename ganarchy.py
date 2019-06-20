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
import re
import qtoml
from collections import defaultdict
from urllib.parse import urlparse

MIGRATIONS = {
        "toml-config": (
                (
                    '''UPDATE "repo_history" SET "project" = (SELECT "git_commit" FROM "config") WHERE "project" IS NULL''',
                    '''ALTER TABLE "repos" RENAME TO "repos_old"''',),
                (
                    '''UPDATE "repo_history" SET "project" = NULL WHERE "project" = (SELECT "git_commit" FROM "config")''',
                    '''ALTER TABLE "repos_old" RENAME TO "repos"''',),
                "switches to toml config format. the old 'repos' table is preserved as 'repos_old'"
            ),
        "better-project-management": (
                (
                    '''ALTER TABLE "repos" ADD COLUMN "branch" TEXT''',
                    '''ALTER TABLE "repos" ADD COLUMN "project" TEXT''',
                    '''CREATE UNIQUE INDEX "repos_url_branch_project" ON "repos" ("url", "branch", "project")''',
                    '''CREATE INDEX "repos_project" ON "repos" ("project")''',
                    '''ALTER TABLE "repo_history" ADD COLUMN "branch" TEXT''',
                    '''ALTER TABLE "repo_history" ADD COLUMN "project" TEXT''',
                    '''CREATE INDEX "repo_history_url_branch_project" ON "repo_history" ("url", "branch", "project")''',),
                (
                    '''DELETE FROM "repos" WHERE "branch" IS NOT NULL OR "project" IS NOT NULL''',
                    '''DELETE FROM "repo_history" WHERE "branch" IS NOT NULL OR "project" IS NOT NULL''',),
                "supports multiple projects, and allows choosing non-default branches"
            ),
        "test": (
                ('''-- apply''',),
                ('''-- revert''',),
                "does nothing"
            )
        }

data_home = os.environ.get('XDG_DATA_HOME', '')
if not data_home:
    data_home = os.environ['HOME'] + '/.local/share'
data_home = data_home + "/ganarchy"

cache_home = os.environ.get('XDG_CACHE_HOME', '')
if not cache_home:
    cache_home = os.environ['HOME'] + '/.cache'
cache_home = cache_home + "/ganarchy"

config_home = os.environ.get('XDG_CONFIG_HOME', '')
if not config_home:
    config_home = os.environ['HOME'] + '/.config'
config_home = config_home + "/ganarchy"

config_dirs = os.environ.get('XDG_CONFIG_DIRS', '')
if not config_dirs:
    config_dirs = '/etc/xdg'
# TODO check if this is correct
config_dirs = [config_dir + "/ganarchy" for config_dir in config_dirs.split(':')]

def get_template_loader():
    from jinja2 import DictLoader, FileSystemLoader, ChoiceLoader
    return ChoiceLoader([
        FileSystemLoader([config_home + "/templates"] + [config_dir + "/templates" for config_dir in config_dirs]),
        DictLoader({
            ## index.html
            'index.html': """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <!--
        GAnarchy - project homepage generator
        Copyright (C) 2019  Soni L.

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <https://www.gnu.org/licenses/>.
        -->
        <title>{{ ganarchy.title|e }}</title>
        <meta name="description" content="{{ ganarchy.title|e }}" />
        <!--if your browser doesn't like the following, use a different browser.-->
        <script type="application/javascript" src="/index.js"></script>
    </head>
    <body>
        <h1>{{ ganarchy.title|e }}</h1>
        <p>This is {{ ganarchy.title|e }}. Currently tracking the following projects:</p>
        <ul>
        {% for project in ganarchy.projects -%}
            <li><a href="/project/{{ project.commit|e }}">{{ project.title|e }}</a>: {{ project.description|e }}</li>
        {% endfor -%}
        </ul>
        <p>Powered by <a href="https://ganarchy.autistic.space/">GAnarchy</a>. AGPLv3-licensed. <a href="https://cybre.tech/SoniEx2/ganarchy">Source Code</a>.</p>
        <p>
            <a href="{{ ganarchy.base_url|e }}" onclick="event.preventDefault(); navigator.registerProtocolHandler('web+ganarchy', this.href + '?url=%s', 'GAnarchy');">Register web+ganarchy: URI handler</a>.
        </p>
    </body>
</html>
""",
            ## index.toml
            'index.toml': """# Generated by GAnarchy

{%- for project, repos in config.projects.items() %}
[projects.{{project}}]
{%- for repo_url, branches in repos.items() %}{% for branch, options in branches.items() %}{% if options.active %}
"{{repo_url|tomle}}".{% if branch %}"{{branch|tomle}}"{% else %}HEAD{% endif %} = { active=true }
{%- endif %}{% endfor %}
{%- endfor %}
{% endfor -%}
""",
            ## project.html FIXME
            'project.html': """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <!--
        GAnarchy - project homepage generator
        Copyright (C) 2019  Soni L.

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
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
        {% endfor -%}
        </ul>
        <p>Powered by <a href="https://ganarchy.autistic.space/">GAnarchy</a>. AGPLv3-licensed. <a href="https://cybre.tech/SoniEx2/ganarchy">Source Code</a>.</p>
        <p>
            <a href="/">Main page</a>.
            <a href="{{ base_url|e }}" onclick="event.preventDefault(); navigator.registerProtocolHandler('web+ganarchy', this.href + '?url=%s', 'GAnarchy');">Register web+ganarchy: URI handler</a>.
        </p>
    </body>
</html>
""",
            ## history.svg FIXME
            'history.svg': """""",
        })
    ])

tomletrans = str.maketrans({
    0: '\\u0000', 1: '\\u0001', 2: '\\u0002', 3: '\\u0003', 4: '\\u0004',
    5: '\\u0005', 6: '\\u0006', 7: '\\u0007', 8: '\\b', 9: '\\t', 10: '\\n',
    11: '\\u000B', 12: '\\f', 13: '\\r', 14: '\\u000E', 15: '\\u000F',
    16: '\\u0010', 17: '\\u0011', 18: '\\u0012', 19: '\\u0013', 20: '\\u0014',
    21: '\\u0015', 22: '\\u0016', 23: '\\u0017', 24: '\\u0018', 25: '\\u0019',
    26: '\\u001A', 27: '\\u001B', 28: '\\u001C', 29: '\\u001D', 30: '\\u001E',
    31: '\\u001F', '"': '\\"', '\\': '\\\\'
    })
def tomlescape(value):
    return value.translate(tomletrans)

def get_env():
    env = jinja2.Environment(loader=get_template_loader(), autoescape=False)
    env.filters['tomlescape'] = tomlescape
    env.filters['tomle'] = env.filters['tomlescape']
    return env


@click.group()
def ganarchy():
    pass

@ganarchy.command()
def initdb():
    """Initializes the ganarchy database."""
    os.makedirs(data_home, exist_ok=True)
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE "repo_history" ("entry" INTEGER PRIMARY KEY ASC AUTOINCREMENT, "url" TEXT, "count" INTEGER, "head_commit" TEXT, "branch" TEXT, "project" TEXT)''')
    c.execute('''CREATE INDEX "repo_history_url_branch_project" ON "repo_history" ("url", "branch", "project")''')
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

class GitError(LookupError):
    """Raised when a git operation fails, generally due to a missing commit or branch, or network connection issues."""
    pass

class Git:
    def __init__(self, path):
        self.path = path
        self.base = ("git", "-C", path)

    def get_hash(self, target):
        try:
            return subprocess.check_output(self.base + ("show", target, "-s", "--format=format:%H", "--"), stderr=subprocess.DEVNULL).decode("utf-8")
        except subprocess.CalledProcessError as e:
            raise GitError from e

    def get_commit_message(self, target):
        try:
            return subprocess.check_output(self.base + ("show", target, "-s", "--format=format:%B", "--"), stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except subprocess.CalledProcessError as e:
            raise GitError from e

# Currently we only use one git repo, at cache_home
GIT = Git(cache_home)

class Repo:
    def __init__(self, dbconn, project_commit, url, branch, head_commit, list_metadata=False):
        self.url = url
        self.branch = branch
        self.project_commit = project_commit
        self.erroring = False

        if not branch:
            self.branchname = "gan" + hashlib.sha256(url.encode("utf-8")).hexdigest()
            self.head = "HEAD"
        else:
            self.branchname = "gan" + hmac.new(branch.encode("utf-8"), url.encode("utf-8"), "sha256").hexdigest()
            self.head = "refs/heads/" + branch

        if head_commit:
            self.hash = head_commit
        else:
            try: # FIXME should we even do this?
                self.hash = GIT.get_hash(self.branchname)
            except GitError:
                self.erroring = True
                self.hash = None

        self.message = None
        if list_metadata:
            try:
                self.update_metadata()
            except GitError:
                self.erroring = True
                pass

    def update_metadata(self):
        self.message = GIT.get_commit_message(self.branchname)

    def update(self):
        """
        Updates the git repo, returning new metadata.
        """
        try:
            subprocess.check_output(["git", "-C", cache_home, "fetch", "-q", self.url, "+" + self.head + ":" + self.branchname], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # This may error for various reasons, but some are important: dead links, etc
            click.echo(e.output, err=True)
            self.erroring = True
            return None
        pre_hash = self.hash
        try:
            post_hash = GIT.get_hash(self.branchname)
        except GitError as e:
            # This should never happen, but maybe there's some edge cases?
            # TODO check
            self.erroring = True
            return None
        self.hash = post_hash
        if not pre_hash:
            pre_hash = post_hash
        try:
            count = int(subprocess.check_output(["git", "-C", cache_home, "rev-list", "--count", pre_hash + ".." + post_hash, "--"]).decode("utf-8").strip())
        except subprocess.CalledProcessError:
            count = 0  # force-pushed
        try:
            subprocess.check_call(["git", "-C", cache_home, "merge-base", "--is-ancestor", self.project_commit, self.branchname], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.update_metadata()
            return count
        except (subprocess.CalledProcessError, GitError) as e:
            click.echo(e, err=True)
            self.erroring = True
            return None

class Project:
    def __init__(self, dbconn, project_commit, list_repos=False):
        self.commit = project_commit
        self.refresh_metadata()
        self.repos = None
        if list_repos:
            self.list_repos(dbconn)

    def list_repos(self, dbconn):
        repos = []
        with dbconn:
            for (e, url, branch, head_commit) in dbconn.execute('''SELECT "max"("e"), "url", "branch", "head_commit" FROM (SELECT "max"("T1"."entry") "e", "T1"."url", "T1"."branch", "T1"."head_commit" FROM "repo_history" "T1"
                                                                WHERE (SELECT "active" FROM "repos" "T2" WHERE "url" = "T1"."url" AND "branch" IS "T1"."branch" AND "project" IS ?1)
                                                                GROUP BY "T1"."url", "T1"."branch"
                                                                UNION
                                                                SELECT null, "T3"."url", "T3"."branch", null FROM "repos" "T3" WHERE "active" AND "project" IS ?1)
                                       GROUP BY "url" ORDER BY "e"''', (self.commit,)):
                repos.append(Repo(dbconn, self.commit, url, branch, head_commit))
        self.repos = repos

    def refresh_metadata(self):
        try:
            project = GIT.get_commit_message(self.commit)
            project_title, project_desc = (lambda x: x.groups() if x is not None else ('', None))(re.fullmatch('^\\[Project\\]\s+(.+?)(?:\n\n(.+))?$', project, flags=re.ASCII|re.DOTALL|re.IGNORECASE))
            if not project_title.strip(): # FIXME
                project_title, project_desc = ("Error parsing project commit",)*2
            # if project_desc: # FIXME
            #     project_desc = project_desc.strip()
            self.commit_body = project
            self.title = project_title
            self.description = project_desc
        except GitError:
            self.commit_body = None
            self.title = None
            self.description = None

    def update(self):
        # TODO? check if working correctly
        results = [(repo, repo.update()) for repo in self.repos]
        self.refresh_metadata()
        return results

class GAnarchy:
    def __init__(self, dbconn, config, list_projects=False, list_repos=False):
        base_url = config.base_url
        title = config.title
        if not base_url:
            # FIXME use a more appropriate error type
            raise ValueError
        if not title:
            title = "GAnarchy on " + urlparse(base_url).hostname
        self.title = title
        self.base_url = base_url
        # load config onto DB
        c = dbconn.cursor()
        c.execute('''CREATE TEMPORARY TABLE "repos" ("url" TEXT PRIMARY KEY, "active" INT, "branch" TEXT, "project" TEXT)''')
        c.execute('''CREATE UNIQUE INDEX "temp"."repos_url_branch_project" ON "repos" ("url", "branch", "project")''')
        c.execute('''CREATE INDEX "temp"."repos_project" ON "repos" ("project")''')
        c.execute('''CREATE INDEX "temp"."repos_active" ON "repos" ("active")''')
        for (project_commit, repos) in config.projects.items():
            for (repo_url, branches) in repos.items():
                for (branchname, options) in branches.items():
                    if options['active']: # no need to insert inactive repos since they get ignored anyway
                        c.execute('''INSERT INTO "repos" VALUES (?, ?, ?, ?)''', (repo_url, 1, branchname, project_commit))
        dbconn.commit()
        if list_projects:
            projects = []
            with dbconn:
                for (project,) in dbconn.execute('''SELECT DISTINCT "project" FROM "repos" '''): # FIXME? *maybe* sort by activity in the future
                    projects.append(Project(dbconn, project, list_repos=list_repos))
            projects.sort(key=lambda project: project.title) # sort projects by title
            self.projects = projects
        else:
            self.projects = None

class Config:
    def __init__(self, toml_file, base=None, remove=True):
        self.projects = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
        config_data = qtoml.load(toml_file)
        self.title = config_data.get('title', '')
        self.base_url = config_data.get('base_url', '')
        # TODO blocked domains (but only read them from config_data if remove is True)
        self.blocked_domains = []
        self.blocked_domain_suffixes = []
        self.blocked_domains.sort()
        self.blocked_domain_suffixes.sort(key=lambda x: x[::-1])
        # FIXME remove duplicates and process invalid entries
        self.blocked_domains = tuple(self.blocked_domains)
        self.blocked_domain_suffixes = tuple(self.blocked_domain_suffixes) # MUST be tuple
        # TODO re.compile("(^" + "|^".join(map(re.escape, domains)) + "|" + "|".join(map(re.escape, suffixes) + ")$")
        if base:
            # FIXME is remove=remove the right thing to do?
            self._update_projects(base.projects, remove=remove, sanitize=False) # already sanitized
        projects = config_data.get('projects', {})
        self._update_projects(projects, remove=remove)

    def _update_projects(self, projects, remove, sanitize=True):
        for (project_commit, repos) in projects.items():
            if sanitize and not isinstance(repos, dict):
                # TODO emit warnings?
                continue
            if sanitize and not re.fullmatch("[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", project_commit): # future-proofing: sha256 support
                # TODO emit warnings?
                continue
            project = self.projects[project_commit]
            for (repo_url, branches) in repos.items():
                if sanitize and not isinstance(branches, dict):
                    # TODO emit warnings?
                    continue
                try:
                    u = urlparse(repo_url)
                    if not u:
                        raise ValueError
                    getattr(u, 'port') # raises ValueError if port is invalid
                    if u.scheme in ('file', ''):
                        raise ValueError
                    if (u.hostname in self.blocked_domains) or (u.hostname.endswith(self.blocked_domain_suffixes)):
                        raise ValueError
                except ValueError:
                    if sanitize:
                        # TODO emit warnings?
                        continue
                    else:
                        raise
                repo = project[repo_url]
                for (branchname, options) in branches.items():
                    if sanitize and not isinstance(options, dict):
                        # TODO emit warnings?
                        continue
                    if branchname == "HEAD":
                        if sanitize:
                            # feels weird, but generally makes things easier
                            # DO NOT emit warnings here. this is deliberate.
                            branchname = None
                        else:
                            raise ValueError
                    branch = repo[branchname]
                    active = options.get('active', False)
                    if active not in (True, False):
                        if sanitize:
                            # TODO emit warnings?
                            continue
                        else:
                            raise ValueError
                    ## | remove | branch.active | options.active | result |
                    ## |    x   |     false     |     false      |  false |
                    ## |    x   |     false     |     true       |  true  |
                    ## |    x   |     true      |     true       |  true  |
                    ## |  false |     true      |     false      |  true  |
                    ## |  true  |     true      |     false      |  false |
                    branch['active'] = branch.get('active', False) or active
                    if remove and not active:
                        branch['active'] = False

@ganarchy.command()
@click.option('--skip-errors/--no-skip-errors', default=False)
@click.argument('files', type=click.File('r', encoding='utf-8'), nargs=-1)
def merge_configs(skip_errors, files):
    """Merges config files."""
    config = None
    for f in files:
        try:
            f.reconfigure(newline='')
            config = Config(f, config, remove=False)
        except (UnicodeDecodeError, qtoml.decoder.TOMLDecodeError):
            if not skip_errors:
                raise
    if config:
        env = get_env()
        template = env.get_template('index.toml')
        click.echo(template.render(config=config))

@ganarchy.command()
@click.argument('project', required=False)
def cron_target(project):
    """Runs ganarchy as a cron target."""
    conf = None
    # reverse order is intentional
    for d in reversed(config_dirs):
        try:
            conf = Config(open(d + "/config.toml", 'r', encoding='utf-8', newline=''), conf)
        except (OSError, UnicodeDecodeError, qtoml.decoder.TOMLDecodeError):
            pass
    with open(config_home + "/config.toml", 'r', encoding='utf-8', newline='') as f:
        conf = Config(f, conf)
    env = get_env()
    if project == "config":
        # render the config
        # doesn't have access to a GAnarchy object. this is deliberate.
        template = env.get_template('index.toml')
        click.echo(template.render(config = conf))
        return
    if project == "project-list":
        # could be done with a template but eh w/e, this is probably better
        for project in conf.projects.keys():
            click.echo(project)
        return
    # make sure the cache dir exists
    os.makedirs(cache_home, exist_ok=True)
    # make sure it is a git repo
    subprocess.call(["git", "-C", cache_home, "init", "-q"])
    conn = sqlite3.connect(data_home + "/ganarchy.db")
    instance = GAnarchy(conn, conf, list_projects=project in ["index", "config"])
    if project == "index":
        # render the index
        template = env.get_template('index.html')
        click.echo(template.render(ganarchy = instance))
        return
    if not instance.base_url or not project:
        click.echo("No base URL or project commit specified", err=True)
        return
    entries = []
    generate_html = []
    c = conn.cursor()
    p = Project(conn, project, list_repos=True)
    results = p.update()
    for (repo, count) in results:
        if count is not None:
            entries.append((repo.url, count, repo.hash, repo.branch, project))
            generate_html.append((repo.url, repo.message, count, repo.branch))
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

if __name__ == "__main__":
    ganarchy()
