# Tests abdl.py internals

import abdl

import re

class OpHelper:
    def __init__(self, pat, ops=None):
        self.pat = pat
        if not ops:
            self.ops = pat._ops
        else:
            self.ops = ops
        self.pos = -1

    def done(self):
        assert self.pos + 1 == len(self.ops)

    def __enter__(self):
        self.pos += 1
        first = self.pos
        assert not isinstance(self.ops[first], abdl._End)
        while not isinstance(self.ops[self.pos], abdl._End):
            self.pos += 1
        assert isinstance(self.ops[self.pos], abdl._End)
        return self.ops[first:self.pos]

    def __exit__(self, exc_type, exc_value, traceback):
        pass

def expect_types(seq, *tys):
    assert len(seq) == len(tys)
    assert(all(map(lambda x: isinstance(*x), zip(seq, tys))))

def expect_idents(oph, *idents):
    for ident in idents:
        with oph as ops:
            expect_types(ops, abdl._Arrow, abdl._Ident)
            assert ops[1].key == ident

def test_empty_iterator_pattern():
    oph = OpHelper(abdl.compile(""))
    oph.done()

def test_four_depths_pattern():
    oph = OpHelper(abdl.compile("->X->Y->Z->W"))
    expect_idents(oph, "X", "Y", "Z", "W")
    oph.done()

def test_regex_pattern():
    oph = OpHelper(abdl.compile("->/.../"))
    with oph as ops:
        expect_types(ops, abdl._Arrow, abdl._RegexKey)
        assert ops[1].key == '...'
        assert ops[1].compiled == re.compile('...')
        assert ops[1].skippable == False
    oph.done()

def test_regex_skippable_pattern():
    oph = OpHelper(abdl.compile("->/.../?"))
    with oph as ops:
        expect_types(ops, abdl._Arrow, abdl._RegexKey)
        assert ops[1].key == '...'
        assert ops[1].compiled == re.compile('...')
        assert ops[1].skippable == True
    oph.done()

def test_regex_and_bind_pattern():
    oph = OpHelper(abdl.compile("->/.../->Y"))
    with oph as ops:
        expect_types(ops, abdl._Arrow, abdl._RegexKey)
        assert ops[1].key == '...'
        assert ops[1].compiled == re.compile('...')
        assert ops[1].skippable == False
    expect_idents(oph, "Y")
    oph.done()

def test_empty_literal_skippable_and_bind_pattern():
    oph = OpHelper(abdl.compile("->''?->Y"))
    with oph as ops:
        expect_types(ops, abdl._Arrow, abdl._StringKey)
        assert ops[1].key == ''
        assert ops[1].skippable == True
    expect_idents(oph, "Y")
    oph.done()

def test_type_pattern():
    oph = OpHelper(abdl.compile("->X:?$a->Y", defs={'a': (dict, list, set)}))
    assert oph.pat._defs['a'] == (dict, list, set)
    with oph as ops:
        expect_types(ops, abdl._Arrow, abdl._Ident, abdl._Ty)
        assert ops[1].key == 'X'
        assert ops[2].key == 'a'
        assert ops[2].skippable == True
    expect_idents(oph, "Y")
    oph.done()

def test_multi_type_pattern():
    oph = OpHelper(abdl.compile("->X:$a:?$b:?$c->Y", defs={'a': (dict, list, set), 'b': (dict, set), 'c': dict}))
    assert oph.pat._defs['a'] == (dict, list, set)
    assert oph.pat._defs['b'] == (dict, set)
    assert oph.pat._defs['c'] == dict
    with oph as ops:
        expect_types(ops, abdl._Arrow, abdl._Ident, abdl._Ty, abdl._Ty, abdl._Ty)
        assert ops[1].key == 'X'
        assert ops[2].key == 'a'
        assert ops[2].skippable == False
        assert ops[3].key == 'b'
        assert ops[3].skippable == True
        assert ops[4].key == 'c'
        assert ops[4].skippable == True
    expect_idents(oph, "Y")
    oph.done()

def test_key_subtree_pattern():
    oph = OpHelper(abdl.compile("->[:?$set->A]->D", defs={'set': set}))
    assert oph.pat._defs['set'] == set
    with oph as ops:
        expect_types(ops, abdl._Arrow, abdl._KeySubtree)
        oph2 = OpHelper(None, ops=ops[1].key)
        with oph2 as ops2:
            expect_types(ops2, abdl._Ty, abdl._Arrow, abdl._Ident)
            assert ops2[0].key == 'set'
            assert ops2[0].skippable == True
            assert ops2[2].key == 'A'
        oph2.done()
    expect_idents(oph, "D")
    oph.done()

def test_param_pattern():
    oph = OpHelper(abdl.compile("->X->$a->Z", defs={'a': '0'}))
    assert oph.pat._defs['a'] == '0'
    expect_idents(oph, "X")
    with oph as ops:
        expect_types(ops, abdl._Arrow, abdl._Param)
        assert ops[1].key == 'a'
        assert ops[1].skippable == False
    expect_idents(oph, "Z")
    oph.done()

def test_value_subtree_pattern():
    oph = OpHelper(abdl.compile("(->foo'foo')(->bar'bar')"))
    with oph as ops:
        expect_types(ops, abdl._ValueSubtree)
        oph2 = OpHelper(None, ops=ops[0].key)
        with oph2 as ops2:
            expect_types(ops2, abdl._Arrow, abdl._Ident, abdl._StringKey)
            assert ops2[1].key == 'foo'
            assert ops2[2].key == 'foo'
            assert ops2[2].skippable == False
        oph2.done()
    with oph as ops:
        expect_types(ops, abdl._ValueSubtree)
        oph2 = OpHelper(None, ops=ops[0].key)
        with oph2 as ops2:
            expect_types(ops2, abdl._Arrow, abdl._Ident, abdl._StringKey)
            assert ops2[1].key == 'bar'
            assert ops2[2].key == 'bar'
            assert ops2[2].skippable == False
        oph2.done()
    oph.done()
