"""
Tests for providers.py: provider selection, error messages, and the
transient-failure retry wrapper added to fix a real gap (a single flaky
request used to permanently fail that one classification).

The retry tests monkeypatch _with_retries' `call` argument directly rather
than mocking the anthropic/openai SDKs, since only the retry loop is this
project's own code to test, not the SDKs' request/response handling.
"""

import pytest

import providers
from providers import MAX_ATTEMPTS, ProviderError, _with_retries, current_model, current_provider_id


def test_current_provider_id_defaults_to_anthropic(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert current_provider_id() == "anthropic"


def test_current_provider_id_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "not-a-real-provider")
    with pytest.raises(ProviderError):
        current_provider_id()


def test_current_provider_id_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "OpenAI")
    assert current_provider_id() == "openai"


def test_current_model_uses_provider_default_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert current_model("anthropic") == providers.PROVIDERS["anthropic"]["default_model"]


def test_current_model_prefers_explicit_override(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "some-custom-model")
    assert current_model("anthropic") == "some-custom-model"


def test_complete_requires_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProviderError):
        providers.complete("a prompt")


def test_with_retries_succeeds_without_retrying_on_first_try(monkeypatch):
    monkeypatch.setattr(providers.time, "sleep", lambda _seconds: None)
    calls = []

    def call():
        calls.append(1)
        return "ok"

    assert _with_retries(call, "Test Provider", "test-model") == "ok"
    assert len(calls) == 1


def test_with_retries_recovers_after_transient_failures(monkeypatch):
    # Simulates exactly the gap found in review: a flaky first attempt
    # (timeout/rate limit) that succeeds on a later try. Before this retry
    # wrapper existed, this would have permanently failed the whole
    # classification on one bad request.
    monkeypatch.setattr(providers.time, "sleep", lambda _seconds: None)
    attempts = {"count": 0}

    def flaky_then_ok():
        attempts["count"] += 1
        if attempts["count"] < MAX_ATTEMPTS:
            raise RuntimeError("simulated transient network error")
        return "recovered"

    assert _with_retries(flaky_then_ok, "Test Provider", "test-model") == "recovered"
    assert attempts["count"] == MAX_ATTEMPTS


def test_with_retries_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(providers.time, "sleep", lambda _seconds: None)
    attempts = {"count": 0}

    def always_fails():
        attempts["count"] += 1
        raise RuntimeError("simulated persistent outage")

    with pytest.raises(ProviderError):
        _with_retries(always_fails, "Test Provider", "test-model")
    assert attempts["count"] == MAX_ATTEMPTS
