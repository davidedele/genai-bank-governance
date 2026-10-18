import pytest
from fastapi.testclient import TestClient
from app import create_app

PUBLIC = 'demo.example.com'

@pytest.fixture
def demo(tmp_path, monkeypatch):
    monkeypatch.setenv('GOVERNANCE_DEMO', '1')
    monkeypatch.setenv('GOVERNANCE_ALLOWED_HOSTS', PUBLIC + ',.example.net')
    monkeypatch.setenv('ENABLE_LIVE_CLASSIFICATION', '1')
    monkeypatch.setenv('GENAI_EVENT_DB', str(tmp_path / 'events.sqlite'))
    return TestClient(create_app(tmp_path / 'register.sqlite'), base_url='https://' + PUBLIC)

def token(client):
    return client.get('/api/bootstrap').json()['token']

def save_body(i=0):
    return {'name': f'Case {i}', 'owner': 'A', 'reviewer': 'B', 'case': {}, 'confirm_review': True}

def test_public_host_refused_unless_demo(tmp_path, monkeypatch):
    monkeypatch.delenv('GOVERNANCE_DEMO', raising=False)
    monkeypatch.setenv('GOVERNANCE_ALLOWED_HOSTS', PUBLIC)
    client = TestClient(create_app(tmp_path / 'r.sqlite'), base_url='https://' + PUBLIC)
    assert client.get('/api/bootstrap').status_code == 403

def test_other_hosts_still_refused_in_demo(demo):
    assert demo.get('/api/bootstrap', headers={'host': 'evil.example.org'}).status_code == 403

def test_health_check_needs_no_host_name(demo):
    assert demo.get('/healthz', headers={'host': 'internal-probe'}).json() == {'ok': True}

def test_demo_switches_ai_and_capture_off_even_if_configured(demo):
    boot = demo.get('/api/bootstrap').json()
    assert boot['demo'] is True and boot['live_enabled'] is False
    tok = boot['token']
    r = demo.post('/api/classify', json={'description': 'x', 'confirm_external_processing': True}, headers={'x-workspace-token': tok})
    assert r.status_code == 403
    assert demo.get('/api/captured').json()['enabled'] is False
    assert demo.post('/api/captured/classify', headers={'x-workspace-token': tok}).status_code == 409

def test_domain_suffix_entry_allows_subdomains_only(demo):
    assert demo.get('/api/bootstrap', headers={'host': 'someone-demo.example.net'}).status_code == 200
    assert demo.get('/api/bootstrap', headers={'host': 'evilexample.net'}).status_code == 403
    assert demo.get('/api/bootstrap', headers={'host': 'example.net.evil.com'}).status_code == 403

def test_origin_must_match_host_behind_a_proxy(demo):
    tok = token(demo)
    ok = demo.post('/api/assess', json={'case': {}}, headers={'x-workspace-token': tok, 'origin': 'https://' + PUBLIC})
    assert ok.status_code == 200
    bad = demo.post('/api/assess', json={'case': {}}, headers={'x-workspace-token': tok, 'origin': 'https://other.example.org'})
    assert bad.status_code == 403

def test_demo_register_is_capped(demo, monkeypatch):
    import app as module
    monkeypatch.setattr(module, 'DEMO_MAX_RECORDS', 2)
    tok = token(demo)
    case = demo.get('/api/bootstrap').json()['examples'][0]['case']
    codes = [demo.post('/api/records', json={**save_body(i), 'case': case}, headers={'x-workspace-token': tok}).status_code for i in range(3)]
    assert codes == [200, 200, 429]

def test_normal_mode_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv('GOVERNANCE_DEMO', raising=False)
    client = TestClient(create_app(tmp_path / 'r.sqlite'))
    boot = client.get('/api/bootstrap').json()
    assert boot['demo'] is False
