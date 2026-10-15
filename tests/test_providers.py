import pytest
import providers
from providers import ProviderError, _with_retries

class HTTPError(Exception):

    def __init__(self, code):
        self.status_code = code

@pytest.mark.parametrize('code', [400, 401, 403, 404, 422])
def test_permanent_errors_are_not_retried(code, monkeypatch):
    calls = []

    def call():
        calls.append(1)
        raise HTTPError(code)
    monkeypatch.setattr(providers.time, 'sleep', lambda _: pytest.fail('Should not wait'))
    with pytest.raises(ProviderError):
        _with_retries(call, 'test', 'model')
    assert len(calls) == 1

@pytest.mark.parametrize('error', [HTTPError(429), HTTPError(500), TimeoutError(), ConnectionError()])
def test_transient_errors_retry(error, monkeypatch):
    calls = []

    def call():
        calls.append(1)
        if len(calls) < 3:
            raise error
        return 'ok'
    monkeypatch.setattr(providers.time, 'sleep', lambda _: None)
    assert _with_retries(call, 'test', 'model') == 'ok' and len(calls) == 3

def test_failure_message_does_not_leak_error_body(monkeypatch):

    def call():
        raise ValueError('PRIVATE_KEY_AND_PROMPT')
    with pytest.raises(ProviderError) as e:
        _with_retries(call, 'test', 'model')
    assert 'PRIVATE' not in str(e.value)

def test_live_calls_disabled_by_default(monkeypatch):
    monkeypatch.delenv('ENABLE_LIVE_CLASSIFICATION', raising=False)
    with pytest.raises(ProviderError, match='disabled'):
        providers.complete('test')

def test_model_must_be_configured(monkeypatch):
    monkeypatch.delenv('LLM_MODEL', raising=False)
    with pytest.raises(ProviderError):
        providers.current_model('anthropic')

def test_provider_selection(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'OpenAI')
    assert providers.current_provider_id() == 'openai'
    monkeypatch.setenv('LLM_PROVIDER', 'bad')
    with pytest.raises(ProviderError):
        providers.current_provider_id()

@pytest.mark.parametrize('pid', ['openai', 'grok', 'gemini', 'anthropic'])
def test_sdk_request_shape_and_metadata(pid, monkeypatch):
    import sys
    from types import SimpleNamespace
    captured = {}

    def create(**kw):
        captured.update(kw)
        if pid == 'anthropic':
            return SimpleNamespace(content=[SimpleNamespace(type='text', text='{}')], model='exact-model', stop_reason='end_turn', usage=SimpleNamespace(input_tokens=10, output_tokens=2))
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content='{}'))], model='exact-model', usage=SimpleNamespace(prompt_tokens=10, completion_tokens=2))

    class Client:

        def __init__(self, **kw):
            captured['client'] = kw
            self.messages = SimpleNamespace(create=create)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass
    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(OpenAI=Client))
    monkeypatch.setitem(sys.modules, 'anthropic', SimpleNamespace(Anthropic=Client))
    monkeypatch.setenv('ENABLE_LIVE_CLASSIFICATION', '1')
    monkeypatch.setenv('LLM_PROVIDER', pid)
    monkeypatch.setenv('LLM_MODEL', 'chosen-model')
    monkeypatch.setenv(providers.PROVIDERS[pid]['api_key_env'], 'test-key-not-real')
    result = providers.complete_with_metadata('synthetic', max_tokens=1234, system='classify')
    assert captured['client']['max_retries'] == 0
    assert captured['client']['timeout'] == 25.0
    assert captured['max_completion_tokens' if pid == 'openai' else 'max_tokens'] == 1234
    assert result.metadata()['max_output_tokens'] == 1234
    assert result.metadata()['response_model'] == 'exact-model'
    assert result.metadata()['input_tokens'] == 10
    assert 'text' not in result.metadata()
