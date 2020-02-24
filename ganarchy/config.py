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
                                            ->url[:?$uri]:?$dict
                                              ->branch:?$dict(->'active'?:?$bool)""", {'bool': bool, 'dict': dict, 'uri': object})#URIValidator})
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

class PCTP:
    def __init__(self, project_commit, uri, branch, options):
        self.project_commit = project_commit
        self.uri = uri
        self.branch = branch
        self.options = options

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
        except (OSError, UnicodeDecodeError, qtoml.decoder.TOMLDecodeError) as e:
            return e

    def exists(self):
        return self.file_exists

    def get_remote_config_sources(self):
        for r in CONFIG_SRCS_SANITIZE.match(self.tomlobj):
            yield r['src'][1]

    def get_project_commit_tree_paths(self):
        for r in CONFIG_REPOS_SANITIZE.match(self.tomlobj):
            yield PCTP(r['commit'][0], r['url'][0], r['branch'][0], r['branch'][1])

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
        for r in CONFIG_REPOS_SANITIZE.match(self.tomlobj):
            yield (r['commit'][0], r['url'][0], r['branch'][0], r['branch'][1])

class ConfigManager:
    """A ConfigManager takes care of managing config sources and
    collecting their details."""
    def __init__(self, sources):
        self.sources = sources

    def update(self):
        for source in self.sources:
            try:
                source.update()
            except:
                raise # TODO

    @classmethod
    def new_default(cls):
        from ganarchy import config_home, config_dirs
        base_src = [FileConfigSource(config_home + "/config.toml")]
        extra_srcs = [FileConfigSource(d + "/config.toml") for d in config_dirs]
        return cls(base_src + extra_srcs)

# class Config:
#     def __init__(self, toml_file, base=None, remove=True):
#         self.projects = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
#         config_data = qtoml.load(toml_file)
#         self.remote_configs = config_data.get('config_srcs', [])
#         self.title = config_data.get('title', '')
#         self.base_url = config_data.get('base_url', '')
#         # TODO blocked domains (but only read them from config_data if remove is True)
#         self.blocked_domains = []
#         self.blocked_domain_suffixes = []
#         self.blocked_domains.sort()
#         self.blocked_domain_suffixes.sort(key=lambda x: x[::-1])
#         # FIXME remove duplicates and process invalid entries
#         self.blocked_domains = tuple(self.blocked_domains)
#         self.blocked_domain_suffixes = tuple(self.blocked_domain_suffixes) # MUST be tuple
#         # TODO re.compile("(^" + "|^".join(map(re.escape, domains)) + "|" + "|".join(map(re.escape, suffixes) + ")$")
#         if base:
#             # FIXME is remove=remove the right thing to do?
#             self._update_projects(base.projects, remove=remove, sanitize=False) # already sanitized
#         projects = config_data.get('projects', {})
#         self._update_projects(projects, remove=remove)
# 
#     def _update_projects(self, projects, remove, sanitize=True):
#         m = (m_ganarchy_config.CONFIG_PATTERN_SANITIZE if sanitize else m_ganarchy_config.CONFIG_PATTERN).match(projects)
#         for v in m:
#             commit, repo_url, branchname, options = v['commit'][0], v['url'][0], v['branch'][0], v['branch'][1]
#             try:
#                 u = urlparse(repo_url)
#                 if not u:
#                     raise ValueError
#                 # also raises for invalid ports, see https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse
#                 # "Reading the port attribute will raise a ValueError if an invalid port is specified in the URL. [...]"
#                 if u.port == 0:
#                     raise ValueError
#                 if u.scheme not in ('http', 'https'):
#                     raise ValueError
#                 if (u.hostname in self.blocked_domains) or (u.hostname.endswith(self.blocked_domain_suffixes)):
#                     raise ValueError
#             except ValueError:
#                 continue
#             if branchname == "HEAD":
#                 branchname = None
#             active = options.get('active', None)
#             if active not in (True, False):
#                 continue
#             branch = self.projects[commit][repo_url][branchname]
#             branch['active'] = active or (branch.get('active', False) and not remove)
