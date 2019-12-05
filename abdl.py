# A Boneless Datastructure Language
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

"""A Boneless Datastructure Language, version 2.0.1.

ABDL expressions are regex-like constructs for matching and validating object structures. They can be used
with JSON and similar formats, and even self-referential data structures.

Language Reference:

    ABDL expressions have the ability to iterate, index, validate and filter data structures. This is
    done with the use of the syntax elements listed below.

    Syntax Elements:

        An ABDL expression is a sequence of zero or more sequences starting with arrows followed by zero or
        more subvalues.

        An arrow is ``->`` and indicates indexing/iteration (Mappings, Sequences, Sets). It must be followed
        by a variable, literal, parameter, regex or key match.

        A variable is a string of alphanumeric characters, not starting with a digit. It may be followed by a
        literal, parameter, regex, key match, or one or more type tests. A ``(key, value)`` tuple containing
        the corresponding matched element will be identified by this name in the results dict.

        A literal is a string delimited by single quotes (use ``%'`` to escape ``'`` and ``%%`` to escape ``%``).
        A literal can be made "non-validating" by appending an ``?`` after it. It may be followed by one or more
        type tests. It is exactly equivalent to indexing an object with a string key.

        A parameter is the symbol ``$`` followed by a string of alphanumeric characters, not starting with
        a digit. A parameter can be made "non-validating" by appending an ``?`` after it. It may be followed by
        one or more type tests. It is exactly equivalent to indexing an object with an arbitrary object key.

        A regex is an RE, as defined by the ``re`` module, delimited by forward slashes (use ``%/`` to escape
        ``/`` and ``%%`` to escape ``%``). A regex can be made "non-validating" by appending an ``?`` after it.
        It may be followed by one or more type tests. It attempts to match each key in the object.

        A type test is ``:`` followed by a parameter. A type test can be made "non-validating" by appending
        an ``?`` after the ``:``. It attempts to match the type of each matched value in the object.

        A key match is an ABDL expression enclosed in ``[`` and ``]``, optionally prefixed with one or more type
        tests. This matches keys (including the type tests).

        A subvalue is an ABDL expression enclosed in ``(`` and ``)``. This allows matching multiple values on
        the same object.

        Some syntax elements can be validating or non-validating. Validating syntax elements will raise a
        :py:exc:`abdl.ValidationError` whenever a non-matching element is encountered, whereas non-validating
        ones will skip them. Note that it is possible for a validating syntax element to still yield results
        before raising a :py:exc:`abdl.ValidationError`, so one needs to be careful when writing code where such
        behaviour could result in a security vulnerability.

    Examples:

        >>> import abdl
        >>> for m in abdl.match("->X:?$dict->Y", {"foo": 1, "bar": {"baz": 2}}, {'dict': dict}):
        ...     print(m['X'][0], m['Y'][0], m['Y'][1])
        bar baz 2

        >>> pat = abdl.compile('''-> 'projects'?
        ...                          -> commit /[0-9a-fA-F]{40}|[0-9a-fA-F]{64}/? :?$dict
        ...                             -> url :?$dict
        ...                                -> branch :?$dict''', {'dict': dict})
        >>> data = {"projects": {
        ...     "385e734a52e13949a7a5c71827f6de920dbfea43": {
        ...         "https://soniex2.autistic.space/git-repos/ganarchy.git": {"HEAD": {"active": True}}
        ...     }
        ... }}
        >>> for m in pat.match(data):
        ...     print(m['commit'][0], m['url'][0], m['branch'][0], m['branch'][1])
        385e734a52e13949a7a5c71827f6de920dbfea43 https://soniex2.autistic.space/git-repos/ganarchy.git HEAD {'active': True}

    (If ``:?$dict`` wasn't present, a TypeError would be raised when trying to iterate the ``1`` from ``"foo": 1``.)
"""

import re

from collections.abc import Mapping, Sequence, Iterator, Set

class DeprecationError(Exception):
    """Raised for deprecated features, if they are disabled.

    This class controls warning/error behaviour of deprecated features."""
    #enable_key_match_compat = False
    #warn_key_match_compat = False

    @classmethod
    def warn_all(cls):
        """Enables all deprecation warnings."""
        pass

class PatternError(Exception):
    """Raised for invalid input or output expressions."""
    # TODO implement formatting

    def __init__(self, msg, pattern, defs, pos, toks):
        self.msg = msg
        self.pattern = pattern
        self.defs = defs
        self.pos = pos
        self._toks = toks # internal use

    def _normalize(self, pattern, defs):
        if pattern is not None:
            if self.pattern is not None:
                raise ValueError("Attempt to normalize normalized pattern")
            else:
                self.pattern = pattern
        if defs is not None:
            if self.defs is not None:
                raise ValueError("Attempt to normalize normalized defs")
            else:
                self.defs = defs

    @classmethod
    def _str_escape(cls, s, pos, toks):
        raise cls("Error in string escape", None, None, pos, toks)

    @classmethod
    def _str_end(cls, s, pos, toks):
        raise cls("Unfinished string", None, None, pos, toks)

    @classmethod
    def _re_escape(cls, s, pos, toks):
        raise cls("Error in regex escape", None, None, pos, toks)

    @classmethod
    def _re_end(cls, s, pos, toks):
        raise cls("Unfinished regex", None, None, pos, toks)

    @classmethod
    def _unexpected_tok(cls, s, pos, toks):
        raise cls("Unexpected token", None, None, pos, toks)

class ValidationError(Exception):
    """Raised when the object tree doesn't validate against the given pattern."""
    # FIXME TODO?

class _PatternElement:
    def on_not_in_key(self, frame, path, defs):
        raise NotImplementedError

    def on_in_key(self, frame, path, defs):
        raise NotImplementedError

    def collect_params(self, res: list):
        pass

class _Arrow(_PatternElement):
    def on_not_in_key(self, frame, path, defs):
        assert not path[-1].empty
        path.append(_Holder(key=None, value=None, name=None, parent=path[-1].value, empty=True))
        return False

class _StringKey(_PatternElement):
    def __init__(self, toks):
        self.key = toks[0]
        self.skippable = toks[1] == '?'

    def on_in_key(self, frame, path, defs):
        return self.on_not_in_key(frame, path, defs)

    def on_not_in_key(self, frame, path, defs):
        path[-1].iterator = self.extract(path[-1].parent)
        path[-1].empty = False
        return True

    def extract(self, obj):
        try:
            yield (self.key, obj[self.key])
        except (TypeError, IndexError, KeyError):
            if not self.skippable:
                raise ValidationError

class _RegexKey(_PatternElement):
    def __init__(self, toks):
        self.key = toks[0]
        self.compiled = re.compile(self.key)
        self.skippable = toks[1] == '?'

    def on_in_key(self, frame, path, defs):
        return self.on_not_in_key(frame, path, defs)

    def on_not_in_key(self, frame, path, defs):
        filtered_iterator = self.filter(path[-1].iterator)
        del path[-1].iterator
        path[-1].iterator = filtered_iterator
        del filtered_iterator
        path[-1].empty = False
        return True

    def filter(self, it):
        for el in it:
            try:
                if self.compiled.search(el[0]):
                    yield el
                elif not self.skippable:
                    raise ValidationError
            except TypeError:
                if not self.skippable:
                    raise ValidationError

class _KeySubtree(_PatternElement):
    def __init__(self, toks):
        self.key = toks[0]
        self.skippable = toks[1] == '?'

    def on_not_in_key(self, frame, path, defs):
        path[-1].subtree = True
        filtered_iterator = self.filter(path[-1].iterator, defs)
        del path[-1].iterator
        path[-1].iterator = filtered_iterator
        del filtered_iterator
        path[-1].empty = False
        return True

    def filter(self, it, defs):
        for x in it:
            for y in _match_helper(self.key, defs, x[0]):
                yield (y, x[1])

    def collect_params(self, res: list):
        for sub in self.key:
            sub.collect_params(res)

class _ValueSubtree(_PatternElement):
    def __init__(self, toks):
        self.key = toks[0]
        self.skippable = toks[1] == '?'

    def on_not_in_key(self, frame, path, defs):
        assert not path[-1].empty
        path.append(_Holder(key=None, value=None, name=None, parent=path[-1].value, empty=False, subtree=True))
        path[-1].iterator = self.filter(path[-1].parent, defs)
        return True

    def filter(self, parent, defs):
        for x in _match_helper(self.key, defs, parent):
            yield (x, parent)

    def collect_params(self, res: list):
        for sub in self.key:
            sub.collect_params(res)

class _Ident(_PatternElement):
    def __init__(self, toks):
        self.key = toks[0]

    def on_not_in_key(self, frame, path, defs):
        path[-1].name = self.key
        path[-1].empty = False
        return True

class _Param(_PatternElement):
    def __init__(self, toks):
        assert isinstance(toks[1], _Ident)
        self.skippable = toks[0] == '?'
        self.key = toks[1].key

    def on_in_key(self, frame, path, defs):
        return self.on_not_in_key(frame, path, defs)

    def on_not_in_key(self, frame, path, defs):
        path[-1].iterator = self.extract(path[-1].parent, defs[self.key])
        path[-1].empty = False
        return True

    def extract(self, obj, key):
        try:
            yield (key, obj[key])
        except (TypeError, IndexError, KeyError):
            if not self.skippable:
                raise ValidationError

    def collect_params(self, res: list):
        res.append(self.key)
    
    def get_value(self, defs):
        return defs[self.key]

class _Ty(_PatternElement):
    def __init__(self, toks):
        assert isinstance(toks[1], _Ident)
        self.skippable = toks[0] == '?'
        self.key = toks[1].key

    def on_in_key(self, frame, path, defs):
        filtered_iterator = self.filter(path[-1].iterator, defs[self.key])
        del path[-1].iterator
        path[-1].iterator = filtered_iterator
        del filtered_iterator
        path[-1].empty = False
        return True

    def on_not_in_key(self, frame, path, defs):
        assert len(path) == 1
        if isinstance(path[-1].value, defs[self.key]):
            return False
        elif not self.skippable:
            raise ValidationError
        path.clear()
        return False

    def filter(self, it, ty):
        for el in it:
            # this may TypeError if ty is not a type nor a tuple of types
            # but that's actually the programmer's error
            if isinstance(el[1], ty):
                yield el
            elif not self.skippable:
                # and this one is for actual validation
                raise ValidationError

    def collect_params(self, res: list):
        res.append(self.key)

class _End(_PatternElement):
    def on_in_key(self, frame, path, defs):
        try:
            path[-1].next()
            return False
        except StopIteration:
            path.pop()
            while frame.prev() and not isinstance(frame.current_op, _End):
                pass
            if not frame.prev():
                # FIXME?
                path.clear()
        return True # FIXME?

def _build_syntax():
    from pyparsing import Suppress, Literal, Forward, CharsNotIn, StringEnd, Combine, Optional, Group, Word, srange, Empty
    # original regex order: arrow, type/parameter/identifier, string, regex, failure
    # better syntax: "arrow" changes from "value" to "key" and thus you need at least one key match before an arrow
    subtree = Forward()
    # where relevant, enforces match behaviour (skippable object tree branch vs required object tree branch)
    skippable = Optional("?", default="")
    #   r"|'(?:%'|%%|%(?P<EES>.|$)|[^%'])*?(?:'|(?P<ES>$))\??" # string literals
    str_literal = (Combine(Suppress("'")
            + (Suppress("%") + "'" | Suppress("%") + "%" | Literal("%") + (CharsNotIn("") | StringEnd()).setParseAction(PatternError._str_escape) | CharsNotIn("%'"))[...]
            + (Suppress("'") | StringEnd().setParseAction(PatternError._str_end))) + skippable).setParseAction(lambda toks: [_StringKey(toks)])
    #   r"|/(?:%/|%%|%(?P<EER>.|$)|[^%/])*?(?:/|(?P<ER>$))\??" # regex
    re_literal = (Combine(Suppress("/")
            + (Suppress("%") + "/" | Suppress("%") + "%" | Literal("%") + (CharsNotIn("") | StringEnd()).setParseAction(PatternError._re_escape) | CharsNotIn("%/"))[...]
            + (Suppress("/") | StringEnd().setParseAction(PatternError._re_end))) + skippable).setParseAction(lambda toks: [_RegexKey(toks)])
    arrow = Literal("->").setParseAction(lambda: [_Arrow()])
    #   r"|(?::\??)?\$?[A-Za-z][A-Za-z0-9]*"                   # identifiers, parameters and type matches
    identifier = Word(srange("[A-Za-z_]"), srange("[A-Za-z0-9_]")).setParseAction(lambda toks: [_Ident(toks)])
    parameter = (Suppress("$") + skippable + identifier).setParseAction(lambda toks: [_Param(toks)])
    ty = (Suppress(":") + skippable + Suppress("$") + identifier).setParseAction(lambda toks: [_Ty(toks)])
    # support for objects-as-keys
    keysubtree = (Suppress("[") + Group(ty[...] + subtree) + (Suppress("]") | CharsNotIn("").setParseAction(PatternError._unexpected_tok) | StringEnd().setParseAction(PatternError._unexpected_tok)) + Optional("?", default="")).setParseAction(lambda toks: [_KeySubtree(toks)])
    # represents key matching - switches from "key" to "value"
    tag = (identifier + Optional(parameter | str_literal | re_literal | keysubtree) | parameter | str_literal | re_literal | keysubtree) + ty[...] + Empty().setParseAction(lambda: [_End()])
    # multiple value matching
    valuesubtree = (Suppress("(") + Group(subtree) + (Suppress(")") | CharsNotIn("").setParseAction(PatternError._unexpected_tok) | StringEnd().setParseAction(PatternError._unexpected_tok)) + Optional("?", default="")).setParseAction(lambda toks: [_ValueSubtree(toks)])
    # arrow and tag, value subtree
    subtree <<= (arrow + tag)[...] + (valuesubtree + Empty().setParseAction(lambda: [_End()]))[...]
    return ((subtree | CharsNotIn("").setParseAction(PatternError._unexpected_tok)) + StringEnd()).parseWithTabs()

_built_syntax = _build_syntax()

def _pairs(o):
    if isinstance(o, Mapping):
        return iter(o.items())
    elif isinstance(o, Sequence):
        return iter(enumerate(o, 0))
    elif isinstance(o, Set):
        return iter(((e, e) for e in o))
    else:
        # maybe there's more stuff I can implement later
        raise TypeError

class _Holder:
    def __init__(self, key, value, name, parent=None, it=None, empty=False, subtree=False):
        self.name = name
        self.key = key
        self.value = value
        self.empty = empty
        self._it = it
        self.parent = parent
        self.subtree = subtree

    @property
    def iterator(self):
        if self._it is None:
            self._it = _pairs(self.parent)
        return self._it

    @iterator.setter
    def iterator(self, value):
        assert self._it is None
        self._it = value

    @iterator.deleter
    def iterator(self):
        self._it = None

    def next(self):
        self.key, self.value = next(self.iterator)

class _Frame:
    def __init__(self, ops):
        self.ops = ops
        self.pc = -1

    def next(self):
        pc = self.pc + 1
        if pc >= len(self.ops):
            return False
        self.pc = pc
        return True

    @property
    def current_op(self):
        return self.ops[self.pc]

    def prev(self):
        pc = self.pc - 1
        if pc < 0:
            return False
        self.pc = pc
        return True

def _match_helper(ops, defs, tree):
    frame = _Frame(ops)

    path = [_Holder(key=None, value=tree, parent=None, it=iter(()), name=None)]
    in_key = False
    while path:
        if not frame.next():
            assert not path[-1].empty
            res = {}
            for h in path:
                if h.subtree:
                    for name, kv in h.key.items():
                        res[name] = kv
                elif h.name is not None:
                    res[h.name] = (h.key, h.value)
            yield res
            assert len(path) == 1 or isinstance(frame.current_op, _End)
            frame.prev()
            in_key = True
        else:
            op = frame.current_op
            if in_key:
                in_key = op.on_in_key(frame, path, defs)
            else:
                in_key = op.on_not_in_key(frame, path, defs)

class Pattern:
    """A compiled pattern object.

    Warning:
        Do not create instances of this class manually. Use :py:func:`abdl.compile`.

    """

    def __init__(self, pattern, defs):
        try:
            self._ops = _built_syntax.parseString(pattern)
        except PatternError as e:
            e._normalize(pattern, defs)
            raise
        else:
            self._params = []
            for op in self._ops:
                op.collect_params(self._params)
            self._defs = {param: defs[param] for param in self._params}

    def match(self, obj):
        """Matches this compiled pattern against the given object.

        Args:
            obj: The object to match against.

        Returns:
            An iterator. This iterator yields ``(key, value)`` pairs
            wrapped in a dict for each variable in the pattern.

        """
        return _match_helper(self._ops, self._defs, obj)

def compile(pattern, defs={}):
    """Compiles the pattern and returns a compiled :py:class:`abdl.Pattern` object.

    Args:
        pattern (str): The pattern. Refer to module-level documentation for
            pattern syntax.
        defs (dict): The parameter list. Used by parameters in the pattern.

    Returns:
        Pattern: A compiled pattern object.

    """
    # TODO caching
    return Pattern(pattern, defs)

def match(pattern, obj, defs={}):
    """Matches the pattern against the given obj.

    This method is equivalent to ``abdl.compile(pattern, defs).match(obj)``.

    Args:
        pattern (str): The pattern. Refer to module-level documentation for
            pattern syntax.
        obj: The object to match against.
        defs (dict): The parameter list. Used by parameters in the pattern.

    Returns:
        An iterator. This iterator yields ``(key, value)`` pairs
        wrapped in a dict for each variable in the pattern.

    """
    return compile(pattern, defs).match(obj)
