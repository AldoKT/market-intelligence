from research.signal_validate_broker_phase2 import compare_views


def test_reproducibility_detects_missing_extra_and_modified_views(tmp_path):
    expected=tmp_path/'expected';actual=tmp_path/'actual'
    expected.mkdir();actual.mkdir()
    for root in (expected,actual):
        (root/'session.json').write_text('{"net": 0}')
    assert compare_views(expected,actual)['passed']
    (actual/'session.json').write_text('{"net": 1}')
    (expected/'episode.json').write_text('{}')
    (actual/'unreviewed.json').write_text('{}')
    result=compare_views(expected,actual)
    assert not result['passed']
    assert result['changed_files']==['session.json']
    assert result['missing_files']==['episode.json']
    assert result['extra_files']==['unreviewed.json']
