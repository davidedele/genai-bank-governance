"""Optional provider clients. One retry layer, bounded timeouts, no error-body leakage."""
from dataclasses import dataclass, asdict
import os
import time
from typing import Callable, TypeVar
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 25.0
PROVIDERS = {'anthropic': {'label': 'Anthropic', 'sdk': 'anthropic', 'api_key_env': 'ANTHROPIC_API_KEY', 'base_url': None}, 'openai': {'label': 'OpenAI', 'sdk': 'openai', 'api_key_env': 'OPENAI_API_KEY', 'base_url': None}, 'grok': {'label': 'xAI', 'sdk': 'openai', 'api_key_env': 'XAI_API_KEY', 'base_url': 'https://api.x.ai/v1'}, 'gemini': {'label': 'Google Gemini', 'sdk': 'openai', 'api_key_env': 'GEMINI_API_KEY', 'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai/'}}

class ProviderError(RuntimeError):
    pass

@dataclass
class Completion:
    text: str
    provider: str
    requested_model: str
    response_model: str | None
    input_tokens: int | None
    output_tokens: int | None
    attempts: int = 1
    elapsed_seconds: float = 0.0
    max_output_tokens: int = 1600

    def metadata(self):
        data = asdict(self)
        del data['text']
        data['request_timeout_seconds'] = REQUEST_TIMEOUT_SECONDS
        data['sampling'] = 'provider defaults'
        return data

def current_provider_id() -> str:
    value = os.environ.get('LLM_PROVIDER', 'anthropic').strip().lower()
    if value not in PROVIDERS:
        raise ProviderError('LLM_PROVIDER must be anthropic, openai, grok or gemini.')
    return value

def current_model(provider_id: str) -> str:
    if provider_id not in PROVIDERS:
        raise ProviderError('Unknown provider.')
    model = os.environ.get('LLM_MODEL', '').strip()
    if not model or len(model) > 200:
        raise ProviderError('Set LLM_MODEL to a model identifier available in your provider account.')
    return model

def _is_transient(error: Exception) -> bool:
    status = getattr(error, 'status_code', None)
    if isinstance(status, int):
        return status in (408, 409, 429) or 500 <= status <= 599
    return isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in {'APITimeoutError', 'APIConnectionError', 'ReadTimeout', 'ConnectTimeout', 'ConnectError'}
T = TypeVar('T')

def _with_retries(call: Callable[[], T], provider_label: str, model: str) -> T:
    started = time.monotonic()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            value = call()
            if isinstance(value, Completion):
                value.attempts = attempt
                value.elapsed_seconds = round(time.monotonic() - started, 4)
            return value
        except Exception as error:
            if not _is_transient(error) or attempt == MAX_ATTEMPTS:
                code = getattr(error, 'status_code', None)
                suffix = f' (HTTP {code})' if isinstance(code, int) else ''
                raise ProviderError(f'{provider_label} request failed{suffix} after {attempt} attempt(s). Check configuration or provider availability.') from None
            delay = RETRY_BACKOFF_SECONDS * 2 ** (attempt - 1)
            headers = getattr(getattr(error, 'response', None), 'headers', {})
            try:
                retry_after = float(headers.get('retry-after', 0))
                if retry_after > 10:
                    raise ProviderError('Provider requested a longer retry delay; retry the operation later.') from None
                delay = max(delay, retry_after)
            except (ValueError, TypeError):
                pass
            time.sleep(delay)
    raise ProviderError('Request failed.')

def complete_with_metadata(prompt: str, max_tokens: int=1600, *, system: str='') -> Completion:
    if os.environ.get('ENABLE_LIVE_CLASSIFICATION', '0') != '1':
        raise ProviderError('Live classification is disabled. Enable it explicitly in your local configuration.')
    pid = current_provider_id()
    cfg = PROVIDERS[pid]
    model = current_model(pid)
    key = os.environ.get(cfg['api_key_env'], '').strip()
    if not key or key.endswith('...'):
        raise ProviderError(f"Set {cfg['api_key_env']} in your local environment.")
    if cfg['sdk'] == 'anthropic':
        try:
            import anthropic
        except ImportError:
            raise ProviderError('Install requirements-llm.txt to enable this provider.') from None

        def call():
            with anthropic.Anthropic(api_key=key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0) as client:
                result = client.messages.create(model=model, system=system, max_tokens=max_tokens, messages=[{'role': 'user', 'content': prompt}])
            text = ''.join((b.text for b in result.content if getattr(b, 'type', None) == 'text')).strip()
            if not text or getattr(result, 'stop_reason', None) == 'max_tokens':
                raise ProviderError('Empty or truncated model response.')
            return Completion(text, pid, model, getattr(result, 'model', None), getattr(result.usage, 'input_tokens', None), getattr(result.usage, 'output_tokens', None))
    else:
        try:
            import openai
        except ImportError:
            raise ProviderError('Install requirements-llm.txt to enable this provider.') from None

        def call():
            with openai.OpenAI(api_key=key, base_url=cfg['base_url'], timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0) as client:
                token_limit = {'max_completion_tokens' if pid == 'openai' else 'max_tokens': max_tokens}
                result = client.chat.completions.create(model=model, **token_limit, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}])
            if not result.choices or result.choices[0].finish_reason == 'length':
                raise ProviderError('Empty or truncated model response.')
            text = result.choices[0].message.content
            if not isinstance(text, str) or not text.strip():
                raise ProviderError('Model returned no classification text.')
            usage = result.usage
            return Completion(text.strip(), pid, model, getattr(result, 'model', None), getattr(usage, 'prompt_tokens', None), getattr(usage, 'completion_tokens', None))
    completion = _with_retries(call, cfg['label'], model)
    completion.max_output_tokens = max_tokens
    return completion

def complete(prompt: str, max_tokens: int=1600, *, system: str='') -> str:
    return complete_with_metadata(prompt, max_tokens, system=system).text
