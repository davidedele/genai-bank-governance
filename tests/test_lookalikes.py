from fastapi.testclient import TestClient
from app import create_app
from demo_examples import lookalike_pairs, examples
from mapper import assess_use_case

def changed_fields(a, b):
    return [k for k in a if k in b and a[k] != b[k] and k not in {'rationale', 'evidence', 'form'}]

def test_every_pair_changes_the_outcome():
    for pair in lookalike_pairs():
        a, b = assess_use_case(pair['a']['case']), assess_use_case(pair['b']['case'])
        assert a['outcome'] != b['outcome'], pair['id']
        assert not a['unresolved'] and not b['unresolved'], pair['id']

def test_pairs_differ_only_in_the_named_detail():
    allowed = {'information': {'information_involved'}, 'review': {'role_of_output'}, 'expertise': {'task_expertise'}, 'approval': {'approval_status'}, 'code': {'role_of_output'}, 'public-tool': {'tool_access', 'approval_status'}}
    for pair in lookalike_pairs():
        assert set(changed_fields(pair['a']['case'], pair['b']['case'])) == allowed[pair['id']], pair['id']

def test_pair_names_are_unique_and_not_library_duplicates_of_each_other():
    names = [p[side]['name'] for p in lookalike_pairs() for side in 'ab']
    assert len(names) == len(set(names))
    assert {e['name'] for e in examples()[:2]} <= set(names)

def test_bootstrap_serves_pairs_with_assessments(tmp_path):
    client = TestClient(create_app(tmp_path / 'r.sqlite'))
    data = client.get('/api/bootstrap').json()
    assert len(data['lookalikes']) == 6
    first = data['lookalikes'][0]
    assert first['a']['assessment']['outcome'] == 'Standard controls'
    assert first['b']['assessment']['outcome'] == 'Review required'
