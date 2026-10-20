import pytest
from fastapi.testclient import TestClient
from app import create_app

@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(tmp_path / 'register.sqlite'))

def boot(client):
    data = client.get('/api/bootstrap').json()
    return data['token'], data['examples'][0]['case']

def body(case, **extra):
    return {'name': 'n', 'owner': 'o', 'reviewer': 'r', 'case': case, 'confirm_review': True, **extra}

def test_empty_parent_id_saves_a_new_case_instead_of_crashing(client):
    token, case = boot(client)
    r = client.post('/api/records', json=body(case, parent_id=''), headers={'x-workspace-token': token})
    assert r.status_code == 200
    assert r.json()['revision'] == 1 and r.json()['parent_id'] is None

def test_unknown_parent_id_is_a_clean_error(client):
    token, case = boot(client)
    r = client.post('/api/records', json=body(case, parent_id='does-not-exist'), headers={'x-workspace-token': token})
    assert r.status_code == 422

def test_chunked_bodies_cannot_get_around_the_size_limit(client):
    token, _ = boot(client)
    def chunks():
        for _ in range(3):
            yield b'{"case":{"x":"' + b'A' * 40000 + b'"}}'
    r = client.post('/api/assess', content=chunks(), headers={'x-workspace-token': token, 'content-type': 'application/json'})
    assert r.status_code == 411

def test_ordinary_requests_still_work_after_the_chunked_rule(client):
    token, case = boot(client)
    assert client.post('/api/assess', json={'case': case}, headers={'x-workspace-token': token}).status_code == 200
    assert client.delete('/api/captured', headers={'x-workspace-token': token}).status_code == 200

@pytest.mark.parametrize('value', [None, True, 0, -1, 10 ** 30, 1.5, '', 'x' * 3000, '\x00', '../../etc/passwd', "' OR 1=1 --", [], {}, [[]], ['x'] * 200, '‮'])
def test_hostile_values_never_cause_a_server_error(client, value):
    token, case = boot(client)
    h = {'x-workspace-token': token}
    for key in list(case):
        r = client.post('/api/assess', json={'case': {**case, key: value}}, headers=h)
        assert r.status_code < 500, (key, value, r.text)
        r = client.post('/api/records', json=body({**case, key: value}), headers=h)
        assert r.status_code < 500, (key, value, r.text)
    for field in ('parent_id', 'classification_id', 'name', 'owner', 'reviewer', 'description', 'review_note'):
        r = client.post('/api/records', json=body(case, **{field: value}), headers=h)
        assert r.status_code < 500, (field, value, r.text)

@pytest.mark.parametrize('path', ['/api/records/../x', '/api/records/%00', "/api/records/1' OR '1'='1", '/static/../app.py', '/static/%2e%2e/app.py', '/static/..%2fapp.py', '/api/export/xml'])
def test_odd_paths_are_refused_cleanly(client, path):
    r = client.get(path)
    assert r.status_code in (404, 405) and 'import' not in r.text

@pytest.mark.parametrize('host', ['[::1]x', 'evil.com', 'localhost@evil.com', 'local host', ''])
def test_malformed_or_foreign_hosts_get_a_clean_refusal(client, host):
    assert client.get('/api/records', headers={'Host': host}).status_code == 403

def test_a_non_ascii_token_is_refused_not_a_server_error(client):
    token, case = boot(client)
    r = client.post('/api/assess', json={'case': case}, headers={'x-workspace-token': 'caf\xe9'.encode('latin-1')})
    assert r.status_code == 403

@pytest.mark.parametrize('raw', ['{"case": NaN}', '{"case": Infinity}', '{"case": -Infinity}', '{"case": 1e999}'])
def test_non_finite_numbers_get_a_validation_error_that_does_not_echo_them(client, raw):
    token, _ = boot(client)
    r = client.post('/api/assess', content=raw, headers={'x-workspace-token': token, 'content-type': 'application/json'})
    assert r.status_code == 422
    assert 'input' not in str(r.json()) and 'NaN' not in r.text and 'Infinity' not in r.text

def test_validation_errors_never_echo_what_was_sent(client):
    token, _ = boot(client)
    r = client.post('/api/records', json={'name': 'SECRET-NAME-VALUE', 'owner': '', 'reviewer': 'r', 'case': {}, 'confirm_review': True}, headers={'x-workspace-token': token})
    assert r.status_code == 422 and 'SECRET-NAME-VALUE' not in r.text
