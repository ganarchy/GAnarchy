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

"""Git abstraction.
"""

# Errors are raised when we can't provide an otherwise valid result.
# For example, we return 0 for counts instead of raising, but raise
# instead of returning empty strings for commit hashes and messages.

import shutil
import subprocess

class GitError(Exception):
    """Raised when a git operation fails, generally due to a
    missing commit or branch, or network connection issues.
    """
    pass

class Git:
    """A git repo.

    Takes a ``pathlib.Path`` as argument.
    """

    def __init__(self, path):
        self.path = path

    #########################################
    # Operations supported on any git repo. #
    #########################################

    def check_branchname(self, branchname):
        """Checks if the given branchname is a valid branch name.
        Raises if it isn't.

        Args:
            branchname (str): Name of branch.

        Raises:
            GitError: If an error occurs.
        """
        try:
            if branchname.startswith("-"):
                raise GitError("check branchname", branchname)
            out = self._cmd(
                "check-ref-format", "--branch", branchname
            ).stdout.decode("utf-8")
            # protect against @{-1}/@{-n} ("previous checkout operation")
            # is also fairly future-proofed, I hope?
            if (not out.startswith(branchname)) or (
                out.removeprefix(branchname) not in ('\r\n', '\n', '')
            ):
                raise GitError("check branchname", out, branchname)
        except subprocess.CalledProcessError as e:
            raise GitError("check branchname") from e

    def get_hash(self, target):
        """Returns the commit hash for a given target.

        Args:
            target (str): a refspec.

        Raises:
            GitError: If an error occurs.
        """
        try:
            return self._cmd(
                "show", target, "-s", "--format=format:%H", "--"
            ).stdout.decode("utf-8")
        except subprocess.CalledProcessError as e:
            raise GitError("get hash") from e

    def get_commit_message(self, target):
        """Returns the commit message for a given target.

        Args:
            target (str): a refspec.

        Raises:
            GitError: If an error occurs.
        """
        try:
            return self._cmd(
                "show", target, "-s", "--format=format:%B", "--"
            ).stdout.decode("utf-8", "replace")
        except subprocess.CalledProcessError as e:
            raise GitError("get commit message") from e

    def check_history(self, local_head, commit):
        """Checks if the local head contains commit in its history.
        Raises if it doesn't.

        Args:
            local_head (str): Name of local head.
            commit (str): Commit hash.

        Raises:
            GitError: If an error occurs.
        """
        try:
            self._cmd("merge-base", "--is-ancestor", commit, local_head)
        except subprocess.CalledProcessError as e:
            raise GitError("check history") from e

    ########################
    # Low-level operations #
    ########################

    def _cmd_init(self, *args):
        """Runs a command for initializing this git repo.

        Always uses ``--bare``.

        Returns:
            subprocess.CompletedProcess: The results of running the command.

        Raises:
            subprocess.CalledProcessError: If the command exited with a non-zero
            status.
        """
        return self._cmd_common('init', '--bare', *args, self.path)

    def _cmd_clone_from(self, from_, *args):
        """Runs a command for cloning into this git repo.

        Always uses ``--bare``.

        Returns:
            subprocess.CompletedProcess: The results of running the command.

        Raises:
            subprocess.CalledProcessError: If the command exited with a non-zero
            status.
        """
        return self._cmd_common('clone', '--bare', *args, from_, self.path)

    def _cmd(self, *args):
        """Runs a command for operating on this git repo.

        Note: Doesn't work for git init and git clone operations. Use
        ``_cmd_init`` and ``_cmd_clone_from`` instead.

        Always uses ``--bare``.

        Returns:
            subprocess.CompletedProcess: The results of running the command.

        Raises:
            subprocess.CalledProcessError: If the command exited with a non-zero
            status.
        """
        return self._cmd_common('-C', self.path, '--bare', *args)

    def _cmd_common(self, *args):
        """Runs a git command with the given args.

        This is a simple wrapper around ``subprocess.run``.

        Returns:
            subprocess.CompletedProcess: The results of running the command.

        Raises:
            subprocess.CalledProcessError: If the command exited with a non-zero
            status.
        """
        return subprocess.run(
            ('git',) + args,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

class GitCache(Git):
    """A permanent repository used to cache remote objects.
    """

    #####################
    # Public operations #
    #####################

    def create(self):
        """Creates the local repo.

        Can safely be called on an existing repo.
        """
        try:
            return self._cmd_init()
        except subprocess.CalledProcessError as e:
            raise GitError("create") from e

    def with_work_repos(self, count):
        """Creates a context manager for managing work repos.

        Args:
            count (int): The number of work repos.
        """
        """From Rust:
        /// Creates the given number of work repos, and calls the closure to run
        /// operations on them.
        ///
        /// The operations can be done on the individual repos, and they'll be
        /// merged into the main repo as this function returns.
        ///
        /// If the callback fails, the work repos will be deleted. If the function
        /// succeeds, the work repos will be merged back into the main repo.
        ///
        /// # Panics
        ///
        /// Panics if a merge conflict is detected. Specifically, if two work repos
        /// modify the same work branch.
        ///
        /// # "Poisoning"
        ///
        /// If this method unwinds, the underlying git repos, if any, will not be
        /// deleted. Instead, future calls to this method will return a GitError.
        """
        work_repos = []
        for i in range(0, count):
            new_path = self.path.with_name('ganarchy-fetch-{}.git'.format(i))
            work_repos.append(GitFetch(new_path))
        physical_work_repos = []
        for repo in work_repos:
            self._fork(repo)
            physical_work_repos.append(repo)
        return _WithWorkRepos(self, physical_work_repos)

    #######################
    # Internal operations #
    #######################

    def _fetch_work(self, from_, branch, from_branch):
        try:
            self._cmd(
                "fetch", from_.path, "+{}:{}".format(from_branch, branch)
            )
        except subprocess.CalledProcessError as e:
            raise GitError("fetch work") from e

    def _replace(self, old_name, new_name):
        try:
            self._cmd(
                "branch", "-M", old_name, new_name
            )
        except subprocess.CalledProcessError as e:
            raise GitError("replace") from e

    def _fork(self, into):
        """Makes a shared clone of this local repo into the given work repo.

        Equivalent to ``git clone --bare --shared``, which is very dangerous!
        """
        try:
            return into._cmd_clone_from(self.path, '--shared')
        except subprocess.CalledProcessError as e:
            raise GitError("fork") from e

class GitFetch(Git):
    """A temporary repository used to fetch remote objects.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_branches = set()

    #####################
    # Public operations #
    #####################

    def force_fetch(self, url, remote_head, local_head):
        """Fetches a remote head into a local head.
        
        If the local head already exists, it is replaced.

        Args:
            url (str): Remote url.
            remote_head (str): Name of remote head.
            local_head (str): Name of local head.

        Raises:
            GitError: If an error occurs.
        """
        try:
            self._cmd(
                "fetch", url, "+" + remote_head + ":" + local_head
            )
            self.pending_branches.add(local_head)
        except subprocess.CalledProcessError as e:
            raise GitError("fetch source") from e

    def get_count(self, first_hash, last_hash):
        """Returns a count of the commits added since ``first_hash``
        up to ``last_hash``.

        Args:
            first_hash (str): A commit.
            last_hash (str): Another commit.

        Returns:
            int: A count of commits added between the hashes, or 0
            if an error occurs.
        """
        try:
            res = self._cmd(
                "rev-list", "--count", first_hash + ".." + last_hash, "--"
            ).stdout.decode("utf-8").strip()
            return int(res)
        except subprocess.CalledProcessError as e:
            return 0

    #######################
    # Internal operations #
    #######################

    def _rm_branch(self, branch):
        try:
            self._cmd("branch", "-D", branch)
        except subprocess.CalledProcessError as e:
            raise GitError("rm branch") from e

    def _delete(self):
        try:
            shutil.rmtree(self.path)
        except IOError as e:
            raise GitError("delete", self.path) from e

class _WithWorkRepos:
    """Context manager for merging forked repos in ``with_work_repos``.
    """
    def __init__(self, cache_repo, work_repos):
        self.cache_repo = cache_repo
        self.work_repos = work_repos

    def __enter__(self):
        return self.work_repos

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            branches = set()
            for work in self.work_repos:
                for branch in work.pending_branches:
                    if branch in branches:
                        raise GitError("Branch {} is in conflict!".format(branch))
                    branches.add(branch)
            del branches
            del work
            del branch

            for i, repo in enumerate(self.work_repos):
                for branch in repo.pending_branches:
                    fetch_head = "{}-{}".format(branch, i)
                    # First collect the work branch into a fetch head
                    self.cache_repo._fetch_work(repo, fetch_head, branch)
                    # If that succeeds, delete the work branch to free up disk
                    repo._rm_branch(branch)
                    # We have all the objects in the main repo and we probably
                    # have enough disk, so just replace the fetch head into
                    # the main branch and hope nothing errors.
                    self.cache_repo._replace(fetch_head, branch)
                repo._delete()
