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

"""A Boneless Datastructure Language, version 1.0.0.

This is a language for matching mixed-type data-structures simiarly to how you'd match a string with regex.

The language has two parts, the Input Langauge and the Output Language.

The Input Language:

    The input language is used for matching the input and setting up variables. An ABDL expression
    is made of tokens that can represent variables, literals, commands or parameters. It must start with
    an arrow, which must be followed by a variable,
    literal, parameter, regex or subtree. Additionally, variables may be followed by a literal,
    parameter or regex. In turn, those may be followed by one or more type tests.

    A variable is a string of alphanumeric characters, not starting with a digit.

    A literal is a string delimited by single quotes. (use ``%'`` to escape ``'`` and ``%%`` to escape ``%``)
    A literal can be made "non-validating" by appending an ``?`` after it.

    A regex is a regex delimited by forward slashes. (use ``%/`` to escape ``/`` and ``%%`` to escape ``%``)
    A regex can be made "non-validating" by appending an ``?`` after it.

    A parameter is the symbol ``$`` followed by a string of alphanumeric characters, not starting with
    a digit. A parameter can be made "non-validating" by appending an ``?`` after it.

    An arrow is ``->`` and indicates indexing/iteration (dicts, sets, frozensets, lists, tuples).

    A type test is ``:`` followed by a parameter. A type test can be made "non-validating" by appending
    an ``?`` after the ``:``.

    A subtree is an ABDL expression enclosed in ``(`` and ``)``, optionally prefixed with one or more type tests.
    This matches keys.

    Example:
        
        >>> for m in abdl.match("->X:?$dict->Y", {"foo": 1, "bar": {"baz": 2}}, {'dict': dict}):
        ...     print(m['X'][0], m['Y'][0], m['Y'][1])
        bar baz 2

    (If ``:?$dict`` wasn't present, a TypeError would be raised when trying to iterate the ``1`` from ``"foo": 1``.)
"""
#"""
#The Output Language [NYI]:
#
#    The output language is used for transforming the input data into something potentially more useful.
#    Its tokens represent variables or commands.
#
#    A variable must be bound on the pattern before being used on the transformer.
#
#    The following commands are accepted:
#        * ``!`` - indicates that the *key* corresponding to the variable shall be used, not the value.
#
#    An output expression always looks like a tuple. That is, it starts with ``(`` and ends with ``)``,
#    and contains comma-separated values. At least one comma is required, and a trailing comma should
#    always be used.
#
#    Example [NYI]:
#
#        >>> for m in abdl.transform("'projects'->?j2/[0-9a-fA-F]{40}|[0-9a-fA-F]{64}/->?j3->?j4", "(j2!,j3!,j4!,j4)", {"projects": {"385e734a52e13949a7a5c71827f6de920dbfea43": {"https://soniex2.autistic.space/git-repos/ganarchy.git": {"HEAD": {"active": True}}}}}):
#        ...     print(m)
#        ('385e734a52e13949a7a5c71827f6de920dbfea43', 'https://soniex2.autistic.space/git-repos/ganarchy.git', 'HEAD', {'active': True})
#"""

import re

from collections.abc import Mapping, Sequence, Iterator, Set

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

class _Subtree(_PatternElement):
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
    keysubtree = (Suppress("(") + Group(ty[...] + subtree[1,...]) + (Suppress(")") | CharsNotIn("").setParseAction(PatternError._unexpected_tok) | StringEnd().setParseAction(PatternError._unexpected_tok)) + Optional("?", default="")).setParseAction(lambda toks: [_Subtree(toks)])
    # represents key matching - switches from "key" to "value"
    tag = (identifier + Optional(parameter | re_literal | keysubtree) | parameter | str_literal | re_literal | keysubtree) + ty[...] + Empty().setParseAction(lambda: [_End()])
    # arrow and tag or we give up
    subtree <<= arrow + tag
    return (subtree | CharsNotIn("").setParseAction(PatternError._unexpected_tok))[...].parseWithTabs()

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
    def __init__(self, key, value, name, parent=None, it=None, empty=False):
        self.name = name
        self.key = key
        self.value = value
        self.empty = empty
        self._it = it
        self.parent = parent
        self.subtree = False

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
    def __init__(self, pattern, defs):
        try:
            self.ops = _built_syntax.parseString(pattern)
        except PatternError as e:
            e._normalize(pattern, defs)
            raise
        else:
            self.params = []
            for op in self.ops:
                op.collect_params(self.params)
            self.defs = {param: defs[param] for param in self.params}

    def match(self, tree):
        return _match_helper(self.ops, self.defs, tree)

#    def transform(self, tree, replacement):
#        pass

def compile(pattern, defs={}):
    # TODO caching
    return Pattern(pattern, defs)

def match(pattern, obj, defs={}):
    return compile(pattern, defs).match(obj)

#def transform(pattern, replacement, obj, defs={}):
#    raise NotImplementedError
