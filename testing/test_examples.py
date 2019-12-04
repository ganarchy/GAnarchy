import abdl

def test_basic_example():
    m = next(abdl.match("->X:?$dict->Y", {"foo": 1, "bar": {"baz": 2}}, {'dict': dict}))
    assert m['X'][0] == 'bar'
    assert m['Y'][0] == 'baz'
    assert m['Y'][1] == 2

def test_basic_2():
    m = next(abdl.match("->'projects':?$d->P/[0-9a-fA-F]{40}|[0-9a-fA-F]{64}/?:?$d->U:?$d->B", {"projects": {"385e734a52e13949a7a5c71827f6de920dbfea43": {"https://soniex2.autistic.space/git-repos/ganarchy.git": {"HEAD": {"active": True}}}}}, {'d': dict}))
    assert m['P'][0] == "385e734a52e13949a7a5c71827f6de920dbfea43"
    assert m['U'][0] == "https://soniex2.autistic.space/git-repos/ganarchy.git"
    assert m['B'][0] == "HEAD"
    assert m['B'][1] == {"active": True}

def test_spaces():
    pat = abdl.compile("""-> 'projects'?
                             -> commit /[0-9a-fA-F]{40}|[0-9a-fA-F]{64}/? :?$dict
                                -> url :?$dict
                                   -> branch :?$dict""", {'dict': dict})
    data = {"projects": {"385e734a52e13949a7a5c71827f6de920dbfea43": {"https://soniex2.autistic.space/git-repos/ganarchy.git": {"HEAD": {"active": True}}}}}
    m = next(pat.match(data))
    assert m['commit'][0] == "385e734a52e13949a7a5c71827f6de920dbfea43"
    assert m['url'][0] == "https://soniex2.autistic.space/git-repos/ganarchy.git"
    assert m['branch'][0] == "HEAD"
    assert m['branch'][1] == {"active": True}
