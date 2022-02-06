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

"""Core logic of GAnarchy.
"""

import hashlib
import hmac
from pathlib import Path
import re
from urllib import parse

import ganarchy.git
import ganarchy.dirs
import ganarchy.data

GIT = ganarchy.git.GitCache(Path(ganarchy.dirs.CACHE_HOME)/'ganarchy-cache.git')

class Repo:
    """A GAnarchy repo.

    Args:
        dbconn (ganarchy.db.Database): The database connection.
        project_commit (str): The project commit.
        url (str): The git URL.
        branch (str): The branch.
        head_commit (str): The last known head commit.

    Attributes:
        branch (str or None): The remote git branch.
        branchname (str): The local git branch.
    """
    # TODO fill in Attributes.

    def __init__(self, dbconn, project_commit, url, branch, head_commit, pinned):
        self.url = url
        self.branch = branch
        self.project_commit = project_commit
        self.errormsg = None
        self.erroring = False
        self.message = None
        self.hash = None
        self.branchname = None
        self.head = None
        self.pinned = pinned

        if not self._check_branch(GIT):
            return

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

        self.refresh_metadata(GIT)

    def _check_branch(self, work_repo):
        """Checks if ``self.branch`` is a valid git branch name, or None. Sets
        ``self.errormsg`` and ``self.erroring`` accordingly.

        Returns:
            bool: True if valid, False otherwise.
        """
        if not self.branch:
            return True
        try:
            work_repo.check_branchname(self.branch)
            return True
        except ganarchy.git.GitError as e:
            self.erroring = True
            self.errormsg = e
            return False

    def refresh_metadata(self, work_repo):
        """Refreshes repo metadata.
        """
        if not self._check_branch(work_repo):
            return
        try:
            self.message = work_repo.get_commit_message(self.branchname)
        except ganarchy.git.GitError as e:
            self.erroring = True
            self.errormsg = e

    # FIXME maybe this shouldn't be "public"?
    # reasoning: this update() isn't reflected in the db.
    # but this might be handy for dry runs.
    # alternatively: change the return to be the new head commit,
    # and update things accordingly.
    def update(self, work_repo, *, dry_run=False):
        """Updates the git repo, returning a commit count.

        Args:
            dry_run (bool): To simulate an update without doing anything.
                In particular, without fetching commits.
        """
        if not self._check_branch(work_repo):
            return None
        if not dry_run:
            try:
                work_repo.force_fetch(self.url, self.head, self.branchname)
            except ganarchy.git.GitError as e:
                # This may error for various reasons, but some
                # are important: dead links, etc
                self.erroring = True
                self.errormsg = e
                return None
        pre_hash = self.hash
        try:
            post_hash = work_repo.get_hash(self.branchname)
        except ganarchy.git.GitError as e:
            # This should never happen, but maybe there's some edge cases?
            # TODO check
            self.erroring = True
            self.errormsg = e
            return None
        self.hash = post_hash
        if not pre_hash:
            pre_hash = post_hash
        count = work_repo.get_count(pre_hash, post_hash)
        try:
            work_repo.check_history(self.branchname, self.project_commit)
            self.refresh_metadata(work_repo)
            return count
        except ganarchy.git.GitError as e:
            self.erroring = True
            self.errormsg = e
            return None

class Project:
    """A GAnarchy project.

    Args:
        dbconn (ganarchy.db.Database): The database connection.
        project_commit (str): The project commit.

    Attributes:
        commit (str): The project commit.
        repos (list, optional): Repos associated with this project.
        title (str, optional): Title of the project.
        description (str, optional): Description of the project.
        commit_body (str, optional): Raw commit message for title and
            description.
        exists (bool): Whether the project exists in our git cache.
    """

    def __init__(self, dbconn, dblock, project_commit):
        self.commit = project_commit
        self.refresh_metadata(GIT)
        self.repos = None
        self._dbconn = dbconn
        self._dblock = dblock

    def load_repos(self):
        """Loads the repos into this project.

        If repos have already been loaded, re-loads them.
        """
        repos = []
        with self._dblock:
            for url, branch, head_commit, pinned in self._dbconn.list_repobranches(self.commit):
                repos.append(
                    Repo(self._dbconn, self.commit, url, branch, head_commit, pinned)
                )
        self.repos = repos

    def refresh_metadata(self, work_repo):
        """Refreshes project metadata.
        """
        try:
            project = work_repo.get_commit_message(self.commit)
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

    def update(self, work_repo, *, dry_run=False):
        """Updates the project and its repos.
        """
        # TODO? check if working correctly
        results = []
        if self.repos is not None:
            for repo in self.repos:
                results.append((repo, repo.update(work_repo, dry_run=dry_run)))
        self.refresh_metadata(work_repo)
        if self.repos is not None:
            results.sort(key=lambda x: x[1] or -1, reverse=True)
            if not dry_run:
                entries = []
                for (repo, count) in results:
                    if count is not None:
                        entries.append((
                            self.commit,
                            repo.url,
                            repo.branch,
                            repo.hash,
                            count
                        ))
                with self._dblock:
                    self._dbconn.insert_activities(entries)
        return results

class GAnarchy:
    """A GAnarchy instance.

    Args:
        dbconn (ganarchy.db.Database): The database connection.
        config (ganarchy.data.DataSource): The (effective) config.

    Attributes:
        base_url (str): Instance base URL.
        title (str): Instance title.
        projects (list, optional): Projects associated with this instance.
    """

    def __init__(self, dbconn, dblock, config):
        self.title = None
        self.base_url = None
        self.projects = None
        self._dbconn = dbconn
        self._dblock = dblock
        self._config = config
        self.load_metadata()

    def load_metadata(self):
        """Loads instance metadata from config.

        If instance metadata has already been loaded, re-loads it.
        """
        try:
            base_url = self._config.get_property_value(
                ganarchy.data.DataProperty.INSTANCE_BASE_URL
            )
        except LookupError:
            # FIXME use a more appropriate error type
            raise ValueError

        try:
            title = self._config.get_property_value(
                ganarchy.data.DataProperty.INSTANCE_TITLE
            )
        except LookupError:
            title = "GAnarchy on " + parse.urlparse(base_url).hostname

        self.title = title
        self.base_url = base_url

    def load_projects(self):
        """Loads the projects into this GAnarchy instance.

        If projects have already been loaded, re-loads them.
        """
        projects = []
        with self._dblock:
            for project in self._dbconn.list_projects():
                projects.append(Project(self._dbconn, self._dblock, project))
        projects.sort(key=lambda p: p.title or "") # sort projects by title
        self.projects = projects
