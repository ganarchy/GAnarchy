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

import re
from urllib import parse

import ganarchy.git
import ganarchy.dirs
import ganarchy.data

# Currently we only use one git repo, at CACHE_HOME
# TODO optimize
GIT = ganarchy.git.Git(ganarchy.dirs.CACHE_HOME)

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
            except ganarchy.git.GitError:
                self.erroring = True
                self.hash = None

        self.message = None
        if list_metadata:
            try:
                self.update_metadata()
            except ganarchy.git.GitError:
                self.erroring = True
                pass

    def update_metadata(self):
        self.message = GIT.get_commit_message(self.branchname)

    def update(self, updating=True):
        """Updates the git repo, returning new metadata.
        """
        if updating:
            try:
                GIT.force_fetch(self.url, self.head, self.branchname)
            except ganarchy.git.GitError as e:
                # This may error for various reasons, but some
                # are important: dead links, etc
                click.echo(e.output, err=True)
                self.erroring = True
                return None
        pre_hash = self.hash
        try:
            post_hash = GIT.get_hash(self.branchname)
        except ganarchy.git.GitError as e:
            # This should never happen, but maybe there's some edge cases?
            # TODO check
            self.erroring = True
            return None
        self.hash = post_hash
        if not pre_hash:
            pre_hash = post_hash
        count = GIT.get_count(pre_hash, post_hash)
        try:
            if updating:
                GIT.check_history(self.branchname, self.project_commit)
            self.update_metadata()
            return count
        except ganarchy.git.GitError as e:
            click.echo(e, err=True)
            self.erroring = True
            return None

class Project:
    # FIXME add docs

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
            self.exists = True
            self.commit_body = project
            self.title = project_title
            self.description = project_desc
        except ganarchy.git.GitError:
            self.exists = False
            self.commit_body = None
            self.title = None
            self.description = None

    def update(self, updating=True):
        # TODO? check if working correctly
        results = [(repo, repo.update(updating)) for repo in self.repos]
        self.refresh_metadata()
        return results

class GAnarchy:
    # FIXME add docs

    def __init__(self, dbconn, config):
        try:
            base_url = config.get_property_value(
                ganarchy.data.DataProperty.INSTANCE_BASE_URL
            )
        except LookupError:
            # FIXME use a more appropriate error type
            raise ValueError

        try:
            title = config.get_property_value(
                ganarchy.data.DataProperty.INSTANCE_TITLE
            )
        except LookupError:
            title = "GAnarchy on " + parse.urlparse(base_url).hostname

        self.title = title
        self.base_url = base_url
        self.projects = None
        self.dbconn = dbconn

    def load_projects(self, list_repos=False):
        # FIXME add docs, get rid of list_repos
        projects = []
        for project in self.dbconn.list_projects():
            projects.append(Project(self.dbconn, project, list_repos=list_repos))
        projects.sort(key=lambda p: p.title or "") # sort projects by title
        self.projects = projects
