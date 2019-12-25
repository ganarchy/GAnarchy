# This file is part of GAnarchy - decentralized project hub
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

import abc
import os

import abdl
import qtoml

from enum import Enum

# sanitize = skip invalid entries
# validate = error on invalid entries
CONFIG_REPOS_SANITIZE = abdl.compile("""->'projects'?:?$dict
                                          ->commit/[0-9a-fA-F]{40}|[0-9a-fA-F]{64}/?:?$dict
                                            ->url:?$dict
                                              ->branch:?$dict(->'active'?:?$bool)""", {'bool': bool, 'dict': dict})
CONFIG_REPOS = abdl.compile("->'projects'->commit->url->branch", {'dict': dict})

CONFIG_TITLE_SANITIZE = abdl.compile("""->title'title'?:?$str""", {'str': str})
CONFIG_BASE_URL_SANITIZE = abdl.compile("""->base_url'base_url'?:?$str""", {'str': str})
CONFIG_SRCS_SANITIZE = abdl.compile("""->'config_srcs'?:?$list->src:?$str""", {'list': list, 'str': str})

CONFIG_TITLE_VALIDATE = abdl.compile("""->title'title':$str""", {'str': str})
CONFIG_BASE_URL_VALIDATE = abdl.compile("""->base_url'base_url':$str""", {'str': str})
CONFIG_SRCS_VALIDATE = abdl.compile("""->'config_srcs':$list->src:$str""", {'list': list, 'str': str})

class ConfigProperty(Enum):
    TITLE = 1
    BASE_URL = 2

class ConfigSource(abc.ABC):
    @abc.abstractmethod
    def update(self):
        """Refreshes the config if necessary."""
        pass

    @abc.abstractmethod
    def exists(self):
        """Returns whether the config exists."""
        pass

    def is_domain_blocked(self, domain):
        """Returns whether the given domain is blocked."""
        return False

    def get_remote_config_sources(self):
        """Yields URI strings for additional configs.

        Yields:
            str: A remote config URI.

        """
        yield from ()

    @abc.abstractmethod
    def get_project_commit_tree_paths(self):
        """Yields (project, URI, branch, options) tuples.

        Yields:
            tuple of (str, str, str, dict): A project commit-tree path.

            Composed of a project commit hash, a repo URI, a branch name
            and a dict of options respectively.

        """
        pass

    def get_supported_properties(self):
        """Returns an iterable of properties supported by this config source.

        Returns:
            Iterable of ConfigProperty: Supported properties.

        """
        return ()

    def get_property_value(self, prop):
        """Returns the value associated with the given property.

        Args:
            prop (ConfigProperty): The property.

        Returns:
            The value associated with the given property.

        Raises:
            ValueError: If the property is not supported by this config
            source.

        """
        raise ValueError

class FileConfigSource(ConfigSource):
    SUPPORTED_PROPERTIES = {}

    def __init__(self, filename):
        self.file_exists = False
        self.last_updated = None
        self.filename = filename
        self.tomlobj = None

    def update(self):
        try:
            updtime = self.last_updated
            self.last_updated = os.stat(self.filename).st_mtime
            if not self.file_exists or updtime != self.last_updated:
                with open(self.filename) as f:
                    self.tomlobj = qtoml.load(f)
            self.file_exists = True
        except OSError:
            return

    def exists(self):
        return self.file_exists

    def get_remote_config_sources(self):
        for r in CONFIG_SRCS_SANITIZE.match(self.tomlobj):
            yield r['src'][1]

    def get_project_commit_tree_paths(self):
        for r in CONFIG_PATTERN_SANITIZE.match(self.tomlobj):
            yield (r['commit'][0], r['url'][0], r['branch'][0], r['branch'][1])

    @classmethod
    def get_supported_properties(cls):
        return cls.SUPPORTED_PROPERTIES

class RemoteConfigSource(ConfigSource):
    def __init__(self, uri):
        self.uri = uri
        self.tomlobj = None
        self.remote_exists = False

    def update(self):
        raise NotImplementedError

    def exists(self):
        return self.remote_exists

    def get_project_commit_tree_paths(self):
        for r in CONFIG_PATTERN_SANITIZE.match(self.tomlobj):
            yield (r['commit'][0], r['url'][0], r['branch'][0], r['branch'][1])

