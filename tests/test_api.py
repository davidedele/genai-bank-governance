import pytest
from fastapi.testclient import TestClient
from app import create_app
from demo_examples import BASE

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('ENABLE_LIVE_CLASSIFICATION', '0')
    with TestClient(create_app(tmp_path / 'db.sqlite')) as c:
        c.headers['x-workspace-token'] = c.get('/api/bootstrap').json()['token']
        yield c

def payload():
    return {'name': 'Synthetic case', 'owner': 'Owner', 'reviewer': 'Reviewer', 'case': BASE, 'confirm_review': True}

def test_bootstrap_examples_do_not_populate_register(client):
    assert len(client.get('/api/bootstrap').json()['examples']) == 8
    assert client.get('/api/records').json() == []

def test_manual_save_revision_export_flow(client):
    assert client.post('/api/assess', json={'case': BASE}).json()['assessment']['outcome'] == 'Standard controls'
    a = client.post('/api/records', json=payload())
    assert a.status_code == 200
    b = client.post('/api/records', json={**payload(), 'parent_id': a.json()['id']})
    assert b.json()['revision'] == 2
    assert len(client.get('/api/records').json()) == 1
    assert len(client.get('/api/export/json').json()) == 2
    assert 'text/csv' in client.get('/api/export/csv').headers['content-type']

def test_review_required_before_save(client):
    assert client.post('/api/records', json={**payload(), 'confirm_review': False}).status_code == 400

def test_no_csrf_token_rejected(client):
    client.headers.pop('x-workspace-token')
    assert client.post('/api/assess', json={'case': BASE}).status_code == 403

def test_foreign_origin_rejected(client):
    assert client.get('/api/bootstrap', headers={'Origin': 'https://unrelated.example'}).status_code == 403

def test_rebinding_host_rejected(client):
    assert client.get('/api/bootstrap', headers={'Host': 'unrelated.example'}).status_code == 403

def test_model_disabled_and_external_consent_required(client):
    assert client.post('/api/classify', json={'description': 'test'}).status_code == 400
    assert client.post('/api/classify', json={'description': 'test', 'confirm_external_processing': True}).status_code == 403

def test_save_does_not_accept_unbounded_text(client):
    assert client.post('/api/records', json={**payload(), 'name': 'x' * 200}).status_code == 422

def test_typed_schema_errors_not_internal_exceptions(client):
    assert client.post('/api/assess', json={'case': {'tool_access': []}}).status_code == 422

def test_historical_snapshot_not_recomputed(client):
    a = client.post('/api/records', json=payload()).json()
    b = client.get('/api/records/' + a['id']).json()['record']
    assert a['assessment'] == b['assessment']

def test_static_frontend_security_headers(client):
    response = client.get('/')
    assert response.status_code == 200 and "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert client.get('/static/app.js').status_code == 200

def test_model_prediction_cannot_be_forged_and_corrections_preserved(client, monkeypatch):
    monkeypatch.setenv('ENABLE_LIVE_CLASSIFICATION', '1')
    monkeypatch.setattr('app.classify_with_metadata', lambda _: (BASE, {'provider': 'test', 'requested_model': 'mock'}))
    result = client.post('/api/classify', json={'description': 'Synthetic', 'confirm_external_processing': True}).json()
    data = {**payload(), 'description': 'Synthetic', 'classification_id': result['classification_id'], 'case': {**BASE, 'information_involved': 'Personal or client data'}}
    record = client.post('/api/records', json=data).json()
    assert record['original_prediction']['information_involved'] == 'Public information'
    assert record['corrections']['information_involved']['reviewed'] == 'Personal or client data'
    assert record['provenance']['requested_model'] == 'mock'
    assert client.post('/api/records', json={**data, 'description': 'Changed'}).status_code == 409
    assert client.post('/api/records', json={**data, 'classification_id': 'invented'}).status_code == 409

def test_prediction_expires_and_metadata_disabled(client, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr('app.time.monotonic', lambda: clock[0])
    monkeypatch.setenv('ENABLE_LIVE_CLASSIFICATION', '1')
    monkeypatch.setattr('app.classify_with_metadata', lambda _: (BASE, {'provider': 'test'}))
    result = client.post('/api/classify', json={'description': 'Synthetic', 'confirm_external_processing': True}).json()
    clock[0] = 1400.0
    assert client.post('/api/records', json={**payload(), 'description': 'Synthetic', 'classification_id': result['classification_id']}).status_code == 409
    monkeypatch.delenv('GENAI_LOG_METADATA', raising=False)
    assert client.get('/api/events').json()['events'] == []
