# This file is part of GAnarchy - decentralized project hub
# Copyright (C) 2019, 2020, 2024  Soni L.
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

"""This module handles GAnarchy's data and config sources.

A data source can be either a config source or a repo list source, but be
careful: they use identical syntax, but have different semantics! Mistaking
a repo list source for a config source is a recipe for security bugs!
"""

import abc
import itertools
import os
import re
import time
import tomllib

import requests

from enum import Enum
from urllib.parse import urlparse

import ganarchy.dirs

# TODO move elsewhere
class _ValidationError(Exception):
    # we have no idea how classes work in python anymore, it's been 2 years
    pass

def _check_type(obj, ty):
    if isinstance(obj, ty):
        return obj
    raise _ValidationError # TODO...

def _is_uri(obj, ports=range(1,65536), schemes=('https',)):
    try:
        u = urlparse(obj)
        if not u:
            return False
        # also raises for invalid ports, see
        # https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse
        # "Reading the port attribute will raise a ValueError if an
        # invalid port is specified in the URL. [...]"
        if u.port is not None and u.port not in ports:
            return False
        if u.scheme not in schemes:
            return False
    except ValueError:
        return False
    return True

def _check_uri(obj, ports=range(1,65536), schemes=('https',)):
    _check_type(obj, str)
    if _is_uri(obj, ports, schemes):
        return obj
    raise _ValidationError # TODO...

_commit_pattern = re.compile(r"^[0-9a-fA-F]{40}$")
_commit_sha256_pattern = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")

def _is_commit_id(obj, sha256ready=True):
    if not isinstance(obj, str):
        return False
    if sha256ready:
        return _commit_sha256_pattern.match(obj)
    else:
        return _commit_pattern.match(obj)

# TODO
#_MATCHER_ALIASES = abdl.compile("""->'project_settings':$dict
#                                     ->commit/[0-9a-fA-F]{40}|[0-9a-fA-F]{64}/?:?$dict
#                                       """, {'dict': dict}) # FIXME check for aliases, might require changes to abdl

# TODO
#_MATCHER_URI_FILTERS = abdl.compile("""->'uri_filters':$dict
#                                         ->filter[:?$str]:?$dict
#                                           (->'active'?:?$bool)""",
#                                    dict(dict=dict, str=str, bool=bool))

class OverridableProperty(abc.ABC):
    """An overridable property, with options.

    Attributes:
        options (dict): Options.
    """

    @abc.abstractmethod
    def as_key(self):
        """Returns an opaque representation of this OverridablePRoperty
        suitable for use as a dict key.

        The returned object is not suitable for other purposes.
        """
        return ()

    @property
    def active(self):
        """Whether this property is active.
        """
        return self.options.get('active', False)

class PCTP(OverridableProperty):
    """A Project Commit-Tree Path.

    Attributes:
        project_commit (str): The project commit.
        uri (str): The URI of a fork of the project.
        branch (str): The branch name, or None for the default branch.
        options (dict): A dict of fork-specific options.
    """

    def __init__(self, project_commit, uri, branch, options):
        self.project_commit = project_commit
        self.uri = uri
        if branch == "HEAD":
            self.branch = None
        else:
            self.branch = branch
        self.options = options

    def as_key(self):
        return (self.project_commit, self.uri, self.branch, )

    @property
    def federate(self):
        return self.options.get('federate', True)

    @property
    def pinned(self):
        return self.options.get('pinned', False)

class RepoListSource(OverridableProperty):
    """A source for a repo list.

    Attributes:
        uri (str): The URI of the repo list.
        options (dict): A dict of repo list-specific options.
    """

    def __init__(self, uri, options):
        self.uri = uri
        self.options = options

    def as_key(self):
        return (self.uri, )

class DataProperty(Enum):
    """Represents values that can be returned by a data source.

    See documentation for DataSource get_property_value and
    DataSource get_property_values for more details.
    """
    INSTANCE_TITLE = (1, str)
    INSTANCE_BASE_URL = (2, str)
    VCS_REPOS = (3, PCTP)
    REPO_LIST_SOURCES = (4, RepoListSource)
    INSTANCE_FEDITO = (5, int)

    def get_type(self):
        """Returns the expected type for values from this DataProperty.
        """
        return self.value[1]

class PropertyError(LookupError):
    """Raised to indicate improper use of a DataProperty.
    """
    pass

class DataSource(abc.ABC):
    @abc.abstractmethod
    def update(self):
        """Refreshes the data associated with this source, if necessary.
        """
        pass

    @abc.abstractmethod
    def exists(self):
        """Returns whether this source has usable data.
        """
        pass

    @abc.abstractmethod
    def get_supported_properties(self):
        """Returns an iterable of properties supported by this data source.

        Returns:
            Iterable of DataProperty: Supported properties.

        """
        return ()

    def get_property_value(self, prop):
        """Returns the value associated with the given property.

        If duplicated, an earlier value should override a later value.

        Args:
            prop (DataProperty): The property.

        Returns:
            The value associated with the given property.

        Raises:
            PropertyError: If the property is not supported by this data
            source.
            LookupError: If the property is supported, but isn't available.
            ValueError: If the property doesn't have exactly one value.
        """
        iterator = self.get_property_values(prop)
        try:
            # note: unpacking
            ret, = iterator
        except LookupError as exc:
            # don't accidentally swallow bugs in the iterator
            raise RuntimeError from exc
        return ret

    @abc.abstractmethod
    def get_property_values(self, prop):
        """Returns the values associated with the given property as an iterable.

        If duplicated, earlier values should override later values.

        Args:
            prop (DataProperty): The property.

        Returns:
            The values associated with the given property.

        Raises:
            PropertyError: If the property is not supported by this data
            source.
            LookupError: If the property is supported, but isn't available.

        """
        raise PropertyError

class DummyDataSource(DataSource):
    """A DataSource that provides nothing.
    """

class ObjectDataSource(DataSource):
    """A DataSource backed by a Python object.

    Updates to the backing object will be immediately reflected in this
    DataSource.
    """

    @staticmethod
    def _get_instance_title(obj):
        result = obj.get('title')
        if not isinstance(result, str):
            raise _ValidationError
        return [result]

    @staticmethod
    def _get_instance_base_uri(obj):
        result = obj.get('base_url')
        if not isinstance(result, str):
            raise _ValidationError
        if not result.isprintable() and not _is_uri(result):
            raise _ValidationError
        return [result]

    @staticmethod
    def _get_instance_fedito(obj):
        result = obj.get('fedi-to')
        if not isinstance(result, int):
            raise _ValidationError
        return [result]

    @staticmethod
    def _get_vcs_repos(obj):
        projects = obj.get('projects')
        if not isinstance(projects, dict):
            raise _ValidationError
        return (
            PCTP(commit, uri, branch,
                 {k: v
                  for k, v in options.items()
                  if (k in {'active', 'federate', 'pinned'}
                      and isinstance(v, bool))
                 })
            for (commit, uris) in projects.items()
            if _is_commit_id(commit)
            if isinstance(uris, dict)
            for (uri, branches) in uris.items()
            if isinstance(uri, str) and uri.isprintable() and _is_uri(uri)
            if isinstance(branches, dict)
            for (branch, options) in branches.items()
            if branch is None or isinstance(branch, str)
            and branch.isprintable()
            if isinstance(options, dict)
            and isinstance(options.get('active'), bool)
        )

    @staticmethod
    def _get_repo_list_sources(obj):
        sources = obj.get('repo_list_srcs')
        if not isinstance(sources, dict):
            raise _ValidationError
        return (
            RepoListSource(src, options)
            for (src, options) in sources.items()
            if isinstance(src, str)
            and _is_uri(src, schemes=('https','file'))
            if isinstance(options, dict)
            and isinstance(options.get('active'), bool)
            # TODO it would probably make sense to add
            # options.get('type', 'toml') somewhere...
        )

    _SUPPORTED_PROPERTIES = {
        DataProperty.INSTANCE_TITLE: _get_instance_title,
        DataProperty.INSTANCE_BASE_URL: _get_instance_base_uri,
        DataProperty.INSTANCE_FEDITO: _get_instance_fedito,
        DataProperty.VCS_REPOS: _get_vcs_repos,
        DataProperty.REPO_LIST_SOURCES: _get_repo_list_sources,
    }

    def __init__(self, obj):
        self._obj = obj

    def update(self):
        pass

    def exists(self):
        return True

    def get_property_values(self, prop):
        try:
            factory = self.get_supported_properties()[prop]
        except KeyError as exc:
            raise PropertyError from exc
        try:
            iterable = factory(self._obj)
        except _ValidationError as exc:
            raise LookupError from exc
        return iterable

    @classmethod
    def get_supported_properties(cls):
        return cls._SUPPORTED_PROPERTIES

class LocalDataSource(ObjectDataSource):
    def __init__(self, filename):
        super().__init__({})
        self.file_exists = False
        self.last_updated = None
        self.filename = filename

    def update(self):
        try:
            updtime = self.last_updated
            self.last_updated = os.stat(self.filename).st_mtime
            if not self.file_exists or updtime != self.last_updated:
                with open(self.filename, 'rb') as f:
                    self._obj = tomllib.load(f)
            self.file_exists = True
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
            self.file_exists = False
            self.last_updated = None
            self._obj = {}
            return e

    def exists(self):
        return self.file_exists

    def __repr__(self):
        return "LocalDataSource({!r})".format(self.filename)

class RemoteDataSource(ObjectDataSource):
    def __init__(self, uri):
        super().__init__({})
        self.uri = uri
        self.remote_exists = False
        self.next_update = 0

    def update(self):
        if self.next_update > time.time():
            return
        # I long for the day when toml has a registered media type
        # FIXME this should be JSON
        # (also doesn't it have one nowadays? -- nvm, not a registered one :/)
        response = requests.get(self.uri, headers={'user-agent': 'ganarchy/0.0.0', 'accept': '*/*'})
        self.remote_exists = response.status_code == 200
        seconds = 3600
        if (refresh := response.headers.get('Refresh', None)) is not None:
            try:
                seconds = int(refresh)
            except ValueError:
                refresh = refresh.split(';', 1)
                try:
                    seconds = int(refresh[0])
                except ValueError:
                    pass
        self.next_update = time.time() + seconds
        if self.remote_exists:
            response.encoding = 'utf-8'
            try:
                self._obj = tomllib.loads(response.text)
            except (UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
                self._obj = {}
                return e
        else:
            return response

    def exists(self):
        return self.remote_exists

    def __repr__(self):
        return "RemoteDataSource({!r})".format(self.uri)

class DefaultsDataSource(ObjectDataSource):
    """Provides a way for contributors to define/encourage some default
    settings.

    In particular, enables contributors to have a say in default domain
    blocks.
    """
    DEFAULTS = {}

    def __init__(self):
        super().__init__(self.DEFAULTS)

    def exists(self):
        return True

    def update(self):
        return

    def __repr__(self):
        return "DefaultsDataSource()"


class ConfigManager(DataSource):
    """A ConfigManager takes care of managing config sources and
    collecting their details.

    Args:
        sources (list of DataSource): The config sources to be managed.
    """
    def __init__(self, sources):
        self.sources = sources

    @classmethod
    def new_default(cls):
        srcs = [LocalDataSource(d + "/config.toml") for d in [ganarchy.dirs.CONFIG_HOME] + ganarchy.dirs.CONFIG_DIRS]
        return cls(srcs + [DefaultsDataSource()])

    def exists(self):
        return True

    def update(self):
        excs = []
        for source in self.sources:
            excs.append(source.update())
        return excs

    def get_supported_properties(self):
        return DataProperty

    def get_property_values(self, prop):
        if prop not in self.get_supported_properties():
            raise PropertyError
        elif prop == DataProperty.VCS_REPOS:
            return self._get_vcs_repos()
        elif prop == DataProperty.REPO_LIST_SOURCES:
            return self._get_repo_list_sources()
        else:
            # short-circuiting, as these are only supposed to return a single value
            for source in self.sources:
                try:
                    return source.get_property_values(prop)
                except PropertyError:
                    pass
                except LookupError:
                    pass
            raise LookupError

    def _get_vcs_repos(self):
        for source in self.sources:
            if DataProperty.VCS_REPOS in source.get_supported_properties():
                try:
                    iterator = source.get_property_values(DataProperty.VCS_REPOS)
                except LookupError:
                    pass
                else:
                    yield from iterator

    def _get_repo_list_sources(self):
        for source in self.sources:
            if DataProperty.REPO_LIST_SOURCES in source.get_supported_properties():
                try:
                    iterator = source.get_property_values(DataProperty.REPO_LIST_SOURCES)
                except LookupError:
                    pass
                else:
                    yield from iterator

class RepoListManager(DataSource):
    """A RepoListManager takes care of managing repo lists.

    Args:
        config_manager (DataSource): The config manager from which the repo
            lists come.
    """
    def __init__(self, config_manager):
        self.config_manager = EffectiveSource(config_manager)
        self.sources = [self.config_manager]

    def exists(self):
        return True

    def update(self):
        excs = [self.config_manager.update()]
        if DataProperty.REPO_LIST_SOURCES in self.config_manager.get_supported_properties():
            self.sources = [self.config_manager]
            try:
                it = self.config_manager.get_property_values(DataProperty.REPO_LIST_SOURCES)
            except LookupError:
                pass
            else:
                self.sources.extend(RemoteDataSource(rls.uri) for rls in it if rls.active)
        for source in self.sources[1:]:
            excs.append(source.update())
        return excs

    def get_supported_properties(self):
        return {DataProperty.VCS_REPOS}

    def get_property_values(self, prop):
        if prop not in self.get_supported_properties():
            raise PropertyError
        assert prop == DataProperty.VCS_REPOS
        return self._get_vcs_repos()

    def _get_vcs_repos(self):
        assert self.config_manager == self.sources[0]
        try:
            # config manager may override repo lists
            iterator = self.config_manager.get_property_values(DataProperty.VCS_REPOS)
        except (PropertyError, LookupError):
            pass
        else:
            yield from iterator
        for source in self.sources:
            if DataProperty.VCS_REPOS in source.get_supported_properties():
                try:
                    iterator = source.get_property_values(DataProperty.VCS_REPOS)
                except LookupError:
                    pass
                else:
                    for pctp in iterator:
                        # but repo lists aren't allowed to override anything
                        for filtered in ['federate', 'pinned']:
                            try:
                                del pctp.options[filtered]
                            except KeyError:
                                pass
                        if pctp.active:
                            yield pctp

class EffectiveSource(DataSource):
    """Wraps another ``DataSource`` and yields "unique" results suitable
    for general use.

    Methods on this class, in particular ``get_property_values``, handle
    ``OverridableProperty`` overrides both to avoid code duplication and
    so the user doesn't have to.

    Args:
        raw_source (DataSource): The raw backing source.
    """
    def __init__(self, raw_source):
        self.raw_source = raw_source

    def exists(self):
        return self.raw_source.exists()

    def update(self):
        return self.raw_source.update()

    def get_property_value(self, prop):
        return self.raw_source.get_property_value(prop)

    def get_supported_properties(self):
        return self.raw_source.get_supported_properties()

    def get_property_values(self, prop):
        # must raise exceptions *now*
        # not when the generator runs
        return self._wrap_values(prop, self.raw_source.get_property_values(prop))

    def _wrap_values(self, prop, it):
        if issubclass(prop.get_type(), OverridableProperty):
            seen = {}
            for v in it:
                k = v.as_key()
                if k in seen:
                    continue
                seen[k] = v
                yield v
        else:
            yield from it

    def __repr__(self):
        return "EffectiveSource({!r})".format(self.raw_source)
