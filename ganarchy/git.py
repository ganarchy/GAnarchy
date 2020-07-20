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

import subprocess

class GitError(LookupError):
    """Raised when a git operation fails, generally due to a
    missing commit or branch, or network connection issues.
    """
    pass

class Git:
    def __init__(self, path):
        self.path = path
        self.base = ("git", "-C", path)

    def create(self):
        """Creates the local repo.

        Can safely be called on an existing repo.
        """
        subprocess.call(self.base + ("init", "-q"))


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
            subprocess.check_call(
                self.base + ("merge-base", "--is-ancestor", commit, local_head),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            raise GitError from e

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
            subprocess.check_output(
                self.base + ("fetch", "-q", url, "+" + remote_head + ":" + local_head),
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            raise GitError from e

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
            res = subprocess.check_output(
                self.base + ("rev-list", "--count", first_hash + ".." + last_hash, "--"),
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            return int(res)
        except subprocess.CalledProcessError as e:
            return 0

    def get_hash(self, target):
        """Returns the commit hash for a given target.

        Args:
            target (str): a refspec.

        Raises:
            GitError: If an error occurs.
        """
        try:
            return subprocess.check_output(
                self.base + ("show", target, "-s", "--format=format:%H", "--"),
                stderr=subprocess.DEVNULL
            ).decode("utf-8")
        except subprocess.CalledProcessError as e:
            raise GitError from e

    def get_commit_message(self, target):
        """Returns the commit message for a given target.

        Args:
            target (str): a refspec.

        Raises:
            GitError: If an error occurs.
        """
        try:
            return subprocess.check_output(
                self.base + ("show", target, "-s", "--format=format:%B", "--"),
                stderr=subprocess.DEVNULL
            ).decode("utf-8", "replace")
        except subprocess.CalledProcessError as e:
            raise GitError from e
