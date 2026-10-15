"""
Tests for classifier.py's JSON-extraction, validation, and error handling.

No test here makes a real API call (no key is assumed to be configured).
`providers.complete` is monkeypatched to return canned text, which is
enough to exercise classify_use_case/_build_prompt/_validate directly.
This parsing/validation layer, not the network call itself, is the part
most likely to break when switching providers.
"""

import json

import pytest

import classifier
from classifier import (
    ClassificationError,
    _extract_json_object,
    _validate,
    classify_use_case,
)

VALID = {
    "form": "communication",
    "tool_access": "Enterprise tool",
    "information_involved": "Internal, non-sensitive information",
    "role_of_output": "Initial draft, reviewed and revised by the employee",
    "banking_process": "Internal administrative process",
    "task_expertise": "Routine, within the employee's expertise",
    "rationale": "Routine internal drafting with an approved tool.",
}


def test_validate_accepts_well_formed_classification():
    _validate(VALID)  # should not raise


def test_validate_rejects_unknown_form():
    bad = dict(VALID, form="not_a_real_form")
    with pytest.raises(ClassificationError):
        _validate(bad)


def test_validate_rejects_unknown_dimension_value():
    bad = dict(VALID, banking_process="Something made up")
    with pytest.raises(ClassificationError):
        _validate(bad)


def test_extract_json_object_handles_bare_json():
    raw = json.dumps(VALID)
    assert json.loads(_extract_json_object(raw)) == VALID


def test_extract_json_object_handles_code_fence():
    raw = "```json\n" + json.dumps(VALID) + "\n```"
    assert json.loads(_extract_json_object(raw)) == VALID


def test_extract_json_object_handles_trailing_commentary():
    # Some providers (GPT-4o-mini observed to do this) add a sentence after
    # the JSON object despite being asked for only JSON.
    raw = json.dumps(VALID) + "\n\nLet me know if you need anything else!"
    assert json.loads(_extract_json_object(raw)) == VALID


def test_extract_json_object_ignores_braces_inside_strings():
    # A rationale that itself contains literal braces (e.g. quoting a code
    # snippet) must not be mistaken for the end of the JSON object.
    tricky = dict(VALID, rationale='Looks like {"a": "b"} in the paste.')
    raw = json.dumps(tricky) + " (end)"
    assert json.loads(_extract_json_object(raw)) == tricky


def test_classify_use_case_rejects_empty_description():
    with pytest.raises(ClassificationError):
        classify_use_case("   ")


def test_classify_use_case_rejects_overlong_description():
    with pytest.raises(ClassificationError):
        classify_use_case("x" * (classifier.MAX_DESCRIPTION_CHARS + 1))


def test_classify_use_case_happy_path(monkeypatch):
    monkeypatch.setattr(classifier, "complete", lambda prompt, max_tokens=400: json.dumps(VALID))
    result = classify_use_case("Drafted an internal memo with an approved enterprise tool.")
    assert result == VALID


def test_classify_use_case_handles_fenced_and_commented_reply(monkeypatch):
    raw = "```json\n" + json.dumps(VALID) + "\n```\nHope that helps!"
    monkeypatch.setattr(classifier, "complete", lambda prompt, max_tokens=400: raw)
    result = classify_use_case("Drafted an internal memo with an approved enterprise tool.")
    assert result == VALID


def test_classify_use_case_wraps_provider_error(monkeypatch):
    def _boom(prompt, max_tokens=400):
        raise classifier.ProviderError("simulated outage")

    monkeypatch.setattr(classifier, "complete", _boom)
    with pytest.raises(ClassificationError):
        classify_use_case("Drafted an internal memo.")


def test_classify_use_case_rejects_unparseable_reply(monkeypatch):
    monkeypatch.setattr(classifier, "complete", lambda prompt, max_tokens=400: "not json at all")
    with pytest.raises(ClassificationError):
        classify_use_case("Drafted an internal memo.")
