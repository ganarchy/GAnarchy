from ganarchy.data import DataProperty, ObjectDataSource, PCTP

def test_basic_project():
    ods = ObjectDataSource({
        'projects': {
            '0123456789012345678901234567890123456789': {
                'https://example/': {
                    None: {'active': True}
                }
            }
         }
    })
    values = list(ods.get_property_values(DataProperty.VCS_REPOS))
    assert len(values) == 1
    assert isinstance(values[0], PCTP)
    assert values[0].project_commit == '0123456789'*4
    assert values[0].uri == 'https://example/'
    assert values[0].branch == None
    assert values[0].active
    assert values[0].federate # defaults to True
    assert not values[0].pinned # defaults to False

def test_nul_in_project_uri():
    # tests what happens if repo uri is malicious/bogus
    # should just ignore bad uri
    ods = ObjectDataSource({
        'projects': {
            '0123456789012345678901234567890123456789': {
                'https://example/\0': {
                    None: {'active': True}
                }
            }
         }
    })
    values = list(ods.get_property_values(DataProperty.VCS_REPOS))
    assert not len(values)

def test_bad_branch():
    # tests what happens if repo branch is malicious/bogus
    # should just ignore bad branch
    ods = ObjectDataSource({
        'projects': {
            '0123456789012345678901234567890123456789': {
                'https://example/': {
                    '\0': {'active': True}
                }
            }
         }
    })
    values = list(ods.get_property_values(DataProperty.VCS_REPOS))
    assert not len(values)
