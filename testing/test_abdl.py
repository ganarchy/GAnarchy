# Tests abdl.py

import abdl

import hypothesis
import hypothesis.strategies as st

import collections.abc

import re

import traceback

# use abdl's _pairs for consistency.
pairs = abdl._pairs

# do not put integers, floats, etc here
# do not put bytes, they iterate as integers
hashables = st.deferred(lambda: st.text() | st.frozensets(hashables) | st.lists(hashables).map(tuple))
values = st.deferred(lambda: hashables | objtree)
objtree = st.deferred(lambda: st.text() | st.dictionaries(hashables, values) | st.lists(values) | st.sets(hashables) | st.lists(hashables).map(tuple))

# note: use all() so as to not eat all the RAM :p

class LogAndCompare:
    def __init__(self, left, right):
        self._itl = left
        self._itr = right
        self.left = []
        self.right = []
    def __iter__(self):
        return self
    def __next__(self):
        try:
            left = next(self._itl)
        except abdl.ValidationError as e:
            e.tb = traceback.format_exc()
            left = e
        try:
            right = next(self._itr)
        except abdl.ValidationError as e:
            e.tb = traceback.format_exc()
            right = e
        self.left.append(left)
        self.right.append(right)
        return left == right or (type(left), type(right)) == (abdl.ValidationError,)*2
    def __repr__(self):
        return "LogAndCompare(left=" + repr(self.left) + ", right=" + repr(self.right) + ")"


@hypothesis.given(objtree, st.just(abdl.compile("->X")))
def test_basic_iterator(foo, pat):
    assert all(LogAndCompare(pat.match(foo), map(lambda x: {"X": x}, pairs(foo))))

@hypothesis.given(objtree, st.just(abdl.compile("->X->Y")))
def test_two_depths(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            for y in pairs(x[1]):
                yield {"X": x, "Y": y}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

@hypothesis.given(objtree, st.just(abdl.compile("->X->Y->Z->W")))
def test_four_depths(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            for y in pairs(x[1]):
                for z in pairs(y[1]):
                    for w in pairs(z[1]):
                        yield {"X": x, "Y": y, "Z": z, "W": w}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

@hypothesis.given(st.dictionaries(st.text(), st.text()) | st.sets(st.text()), st.just(abdl.compile("->/.../")))
def test_regex(foo, pat):
    # no bindings on this one :<
    def deep(foo):
        for x in pairs(foo):
            if re.search("...", x[0]):
                    yield {}
            else:
                raise abdl.ValidationError
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

@hypothesis.given(objtree, st.just(abdl.compile("->/.../?")))
def test_regex_skippable_vs_objtree(foo, pat):
    assert all(LogAndCompare(pat.match(foo), ({} for x in pairs(foo) if isinstance(x[0], str) and re.search("...", x[0]))))

@hypothesis.given(st.dictionaries(st.text(), st.text()) | st.sets(st.text()), st.just(abdl.compile("->/.../->Y")))
def test_regex_and_bind(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            if re.search("...", x[0]):
                for y in pairs(x[1]):
                    yield {"Y": y}
            else:
                raise abdl.ValidationError
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

@hypothesis.given(objtree, st.just(abdl.compile("->/.../?->Y")))
def test_regex_skippable_and_bind_vs_objtree(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            if isinstance(x[0], str) and re.search("...", x[0]):
                for y in pairs(x[1]):
                    yield {"Y": y}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

@hypothesis.given(objtree, st.just(abdl.compile("->/^...$/?->Y")))
def test_regex_anchored_skippable_and_bind_vs_objtree(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            if isinstance(x[0], str) and re.search("^...$", x[0]):
                for y in pairs(x[1]):
                    yield {"Y": y}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

@hypothesis.given(objtree, st.just(abdl.compile("->''?->Y")))
def test_empty_literal_vs_objtree(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            if x[0] == '':
                for y in pairs(x[1]):
                    yield {"Y": y}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

defs = {'a': (dict, list, set)}
@hypothesis.given(objtree, st.just(abdl.compile("->X:?$a->Y", defs=defs)))
def test_type(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            if isinstance(x[1], (dict, list, set)):
                for y in pairs(x[1]):
                    yield {"X": x, "Y": y}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

defs = {'a': (dict, list, set), 'b': (dict, set), 'c': dict}
@hypothesis.given(objtree, st.just(abdl.compile("->X:?$a:?$b:?$c->Y", defs=defs)))
def test_multi_type(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            if isinstance(x[1], dict):
                for y in pairs(x[1]):
                    yield {"X": x, "Y": y}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

defs = {'a': (dict, list, set), 'b': (dict, set), 'c': dict}
@hypothesis.given(objtree, st.just(abdl.compile("->X:$a:$b:$c->Y", defs=defs)))
@hypothesis.settings(suppress_health_check=[hypothesis.HealthCheck.too_slow])
def test_multi_type_with_validation_errors(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            if isinstance(x[1], dict):
                for y in pairs(x[1]):
                    yield {"X": x, "Y": y}
            else:
                raise abdl.ValidationError
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

@hypothesis.given(st.dictionaries(st.frozensets(st.text()), st.text()), st.just(abdl.compile("->(:?$sets->A)->D", {'sets': collections.abc.Set})))
def test_subtree_partial(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            if isinstance(x[0], collections.abc.Set):
                for a in pairs(x[0]):
                    for d in pairs(x[1]):
                        yield {"A": a, "D": d}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

@hypothesis.given(objtree, st.just(abdl.compile("->X->$a->Z", {'a': '0'})))
def test_param(foo, pat):
    def deep(foo):
        for x in pairs(foo):
            try:
                y = x['0']
            except (TypeError, IndexError, KeyError):
                raise abdl.ValidationError
            else:
                for z in pairs(y):
                    yield {"X": x, "Z": z}
    assert all(LogAndCompare(pat.match(foo), deep(foo)))

# FIXME
#@hypothesis.given(objtree, st.text())
#def test_exhaustive(foo, pat):
#    hypothesis.assume(not re.match("^%s+$", pat))
#    hypothesis.assume(pat)
#    try:
#        compiled = abdl.compile(pat)
#        print(pat)
#    except abdl.PatternError:
#        hypothesis.assume(False)
#    compiled.match(foo)
