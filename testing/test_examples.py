import abdl

def test_basic_example():
    for m in abdl.match("->X:?$dict->Y", {"foo": 1, "bar": {"baz": 2}}, {'dict': dict}):
        assert m['X'][0] == 'bar' and  m['Y'][0] == 'baz' and m['Y'][1] == 2

def test_basic_2():
    for m in abdl.match("->'projects':?$d->P/[0-9a-fA-F]{40}|[0-9a-fA-F]{64}/?:?$d->U:?$d->B", {"projects": {"385e734a52e13949a7a5c71827f6de920dbfea43": {"https://soniex2.autistic.space/git-repos/ganarchy.git": {"HEAD": {"active": True}}}}}, {'d': dict}):
        assert m['P'][0] == "385e734a52e13949a7a5c71827f6de920dbfea43" and m['U'][0] == "https://soniex2.autistic.space/git-repos/ganarchy.git" and m['B'][0] == "HEAD" and m['B'][1] == {"active": True}
