import csv
import io
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from storage import Store, ConflictError, export_csv, safe_csv_cell, daily_limit_from_env
from demo_examples import BASE
from mapper import load_policy

@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'private' / 'register.sqlite')

def save(store, **kw):
    return store.save(name='Example', owner='Owner', reviewer='Reviewer', case=BASE, **kw)

def test_record_survives_reopening_and_snapshot_is_frozen(store):
    a = save(store)
    p = load_policy()
    p['version'] = 'changed'
    b = save(store, parent_id=a['id'], policy=p)
    assert Store(store.path).get(a['id'])['assessment']['policy_version'] != b['assessment']['policy_version']
    assert b['revision'] == 2 and len(store.list()) == 2 and (len(store.list(latest_only=True)) == 1)

def test_stale_revision_conflict(store):
    a = save(store)
    save(store, parent_id=a['id'])
    with pytest.raises(ConflictError):
        save(store, parent_id=a['id'])

def test_private_text_not_persisted_by_default(store):
    sentinel = 'PRIVATE_SENTINEL'
    prediction = {**BASE, 'rationale': sentinel, 'evidence': {'tool_access': sentinel}}
    a = store.save(name='Example', owner='Owner', reviewer='Reviewer', case=prediction, prediction=prediction, description=sentinel)
    assert sentinel not in json.dumps(a)
    assert sentinel.encode() not in store.path.read_bytes()

def test_text_retention_is_explicit(store):
    a = save(store, description='Synthetic description', retain_description=True)
    assert a['description'] == 'Synthetic description'

def test_daily_counter_shared_and_persistent(store):
    for _ in range(3):
        store.reserve_api_attempt(limit=3)
    with pytest.raises(ValueError):
        Store(store.path).reserve_api_attempt(limit=3)

@pytest.mark.parametrize('text', ['=1+1', '+formula', '-formula', '@SUM(1)', '  =formula', '\tformula', '\rformula', '\nformula'])
def test_csv_formula_neutralization(text):
    assert safe_csv_cell(text).startswith("'")

def test_csv_keeps_valid_quoting(store):
    a = store.save(name='Comma, quote " and text', owner='Owner', reviewer='Reviewer', case=BASE)
    rows = list(csv.DictReader(io.StringIO(export_csv([a]))))
    assert rows[0]['name'] == a['name']

def test_concurrent_record_writes(store):
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda _: save(store), range(24)))
    assert len(store.list()) == 24

def test_risk_control_wording_is_frozen(store, monkeypatch):
    from mapper import RISK_AREAS
    a = save(store)
    risk = a['assessment']['risk_details'][0]
    before = risk['control_objective']
    original = next((r for r in RISK_AREAS if r['id'] == risk['id']))
    monkeypatch.setitem(original, 'control_objective', 'Changed later')
    assert store.get(a['id'])['assessment']['risk_details'][0]['control_objective'] == before
    assert len(a['assessment']['framework_sha256']) == 64

def test_corrections_and_field_sources_preserved_without_stale_evidence(store):
    predicted = {**BASE, 'evidence': {'information_involved': 'public report'}, 'rationale': 'public report'}
    reviewed = {**predicted, 'information_involved': 'Personal or client data'}
    a = store.save(name='Sample', owner='Owner', reviewer='Reviewer', case=reviewed, prediction=predicted, retain_description=True)
    assert a['corrections']['information_involved']['reviewed'] == 'Personal or client data'
    assert 'information_involved' not in a['case']['evidence']
    assert a['case']['rationale'] == ''
    assert a['original_prediction']['evidence']['information_involved'] == 'public report'
    assert a['field_sources']['information_involved'] == 'reviewer correction'


def test_daily_limit_zero_means_no_cap(store):
    for _ in range(5):
        assert store.reserve_api_attempt(limit=0) == -1

def test_daily_limit_message_names_the_setting(store):
    store.reserve_api_attempt(limit=1)
    with pytest.raises(ValueError, match='DAILY_CLASSIFICATION_LIMIT'):
        store.reserve_api_attempt(limit=1)

@pytest.mark.parametrize('value,expected', [(None, 30), ('', 30), ('12', 12), (' 7 ', 7), ('0', 0), ('-3', 30), ('many', 30), ('2.5', 30)])
def test_daily_limit_from_environment(value, expected):
    environ = {} if value is None else {'DAILY_CLASSIFICATION_LIMIT': value}
    assert daily_limit_from_env(environ) == expected
