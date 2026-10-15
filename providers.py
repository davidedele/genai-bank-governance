"""
Provider-agnostic LLM calling for classifier.py.

The classifier only needs one thing from a model: send a prompt, get back
text. Anthropic, OpenAI, xAI (Grok) and Google (Gemini) all expose that
same shape, and three of the four (OpenAI, Grok, Gemini) speak OpenAI's own
wire format, either natively or through a published "OpenAI-compatible"
endpoint. So instead of a separate branch of request/response code per
company, this module keeps exactly two code paths: Anthropic's own SDK, and
the OpenAI SDK pointed at whichever base_url the chosen provider uses.
Adding another OpenAI-compatible provider later (e.g. a local vLLM server,
DeepSeek, Mistral's API) means adding one entry to PROVIDERS, not a new
branch.

Which provider is used is controlled by two environment variables:

    LLM_PROVIDER   one of PROVIDERS below. Defaults to "anthropic".
    LLM_MODEL      overrides that provider's default model name. Optional,
                   since model names change far more often than providers.

See .env.example for the API-key variable each provider reads.
"""

import os
import time

# How many times to retry a single completion call after a transient failure
# (timeout, rate limit, connection reset), and how long to wait between
# attempts. A bad API key or missing package fails the same way every time,
# so complete() below only retries once the first attempt has actually
# reached the provider and failed there, not for setup errors it already
# caught before calling the SDK.
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5

PROVIDERS = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "sdk": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": None,
        "default_model": "claude-haiku-4-5",
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "openai": {
        "label": "OpenAI (GPT)",
        "sdk": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,  # OpenAI SDK's own default
        "default_model": "gpt-4o-mini",
        "key_url": "https://platform.openai.com/api-keys",
    },
    "grok": {
        "label": "xAI (Grok)",
        "sdk": "openai",  # xAI publishes an OpenAI-compatible endpoint
        "api_key_env": "XAI_API_KEY",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "key_url": "https://console.x.ai",
    },
    "gemini": {
        "label": "Google (Gemini)",
        "sdk": "openai",  # Gemini also publishes an OpenAI-compatible endpoint
        "api_key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.0-flash",
        "key_url": "https://aistudio.google.com/apikey",
    },
}


class ProviderError(Exception):
    pass


def current_provider_id() -> str:
    provider = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    if provider not in PROVIDERS:
        raise ProviderError(
            f"Unknown LLM_PROVIDER {provider!r}. Choose one of: "
            + ", ".join(PROVIDERS)
        )
    return provider


def current_model(provider_id: str) -> str:
    return os.environ.get("LLM_MODEL") or PROVIDERS[provider_id]["default_model"]


def complete(prompt: str, max_tokens: int = 400) -> str:
    """Send a single-turn prompt to whichever provider LLM_PROVIDER selects
    and return the raw text of the reply. Raises ProviderError for any
    configuration or request problem, with a message naming the provider
    actually in use, since that's no longer always Anthropic."""
    provider_id = current_provider_id()
    provider = PROVIDERS[provider_id]
    model = current_model(provider_id)

    api_key = os.environ.get(provider["api_key_env"])
    if not api_key:
        raise ProviderError(
            f"{provider['api_key_env']} is not set. LLM_PROVIDER is "
            f"{provider_id!r} ({provider['label']}), which reads its key "
            f"from that variable. Get one at {provider['key_url']}, add it "
            "to .env, and load it (e.g. `export $(cat .env | xargs)`) "
            "before running."
        )

    if provider["sdk"] == "anthropic":
        try:
            import anthropic
        except ImportError as e:
            raise ProviderError(
                "The 'anthropic' package is not installed. Run: "
                "pip install anthropic"
            ) from e

        def _call_anthropic():
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()

        return _with_retries(_call_anthropic, provider["label"], model)

    # Everything else (OpenAI itself, and OpenAI-compatible providers like
    # Grok and Gemini) goes through the same openai.OpenAI client, just
    # pointed at a different base_url.
    try:
        import openai
    except ImportError as e:
        raise ProviderError(
            "The 'openai' package is not installed. Run: pip install openai"
        ) from e

    def _call_openai_compatible():
        client = openai.OpenAI(api_key=api_key, base_url=provider["base_url"])
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    return _with_retries(_call_openai_compatible, provider["label"], model)


def _with_retries(call, provider_label: str, model: str) -> str:
    """Run `call()` up to MAX_ATTEMPTS times, pausing between failures.

    A single flaky request (timeout, rate limit, dropped connection) would
    otherwise permanently fail one classification. Retrying here, where the
    actual network call happens, covers every caller at once.
    """
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return call()
        except Exception as e:  # noqa: BLE001 - deliberately broad: SDKs
            # raise their own distinct exception types per provider, and all
            # of them are worth one retry before giving up.
            last_error = e
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise ProviderError(
        f"{provider_label} API call failed (model {model!r}) after "
        f"{MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error
