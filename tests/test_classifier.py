import json
import pytest
from classifier import parse_classification, ClassificationError, classify_use_case, _validate, build_system_prompt
from schema import UNKNOWN, normalize_case, ValidationError
from providers import Completion
import classifier
from demo_examples import BASE
DESCRIPTION = 'An approved enterprise assistant summarized public material for routine internal administration. I reviewed the draft within my expertise.'
VALID = {**BASE, 'rationale': 'Description-based extraction.', 'evidence': {k: DESCRIPTION for k in BASE if k != 'forms'}}

@pytest.mark.parametrize('raw', [None, [], False, 1, 'x', {'forms': [{}]}, {**BASE, 'tool_access': []}])
def test_malformed_schema_fails_cleanly(raw):
    with pytest.raises((ClassificationError, ValidationError)):
        _validate(raw)

def test_valid_extraction():
    assert parse_classification(json.dumps(VALID), DESCRIPTION)['forms'] == ['document_processing']

def test_code_fence_is_accepted():
    assert parse_classification('```json\n' + json.dumps(VALID) + '\n```', DESCRIPTION)['forms']

@pytest.mark.parametrize('suffix', ['Here is your answer.', '{"forms":[]}'])
def test_trailing_prose_or_second_object_is_rejected(suffix):
    with pytest.raises(ClassificationError):
        parse_classification(json.dumps(VALID) + suffix, DESCRIPTION)

def test_duplicate_keys_rejected():
    with pytest.raises(ClassificationError):
        parse_classification('{"forms":[],"forms":[]}', DESCRIPTION)

def test_evidence_must_occur_in_input():
    bad = {**VALID, 'evidence': {**VALID['evidence'], 'tool_access': 'Never said this'}}
    with pytest.raises(ClassificationError):
        parse_classification(json.dumps(bad), DESCRIPTION)

def test_known_values_require_evidence():
    with pytest.raises(ClassificationError):
        parse_classification(json.dumps({**VALID, 'evidence': {}}), DESCRIPTION)

def test_unknown_values_need_no_invented_evidence():
    raw = {d: UNKNOWN for d in classifier.DIMENSION_IDS}
    raw.update(forms=[], approval_status=UNKNOWN, evidence={}, rationale='Insufficient context.')
    assert parse_classification(json.dumps(raw), 'Help me.')['tool_access'] == UNKNOWN

def test_multiple_forms():
    raw = {**VALID, 'forms': ['communication', 'document_processing']}
    assert len(parse_classification(json.dumps(raw), DESCRIPTION)['forms']) == 2

def test_approval_contradiction():
    with pytest.raises(ValidationError):
        normalize_case({**BASE, 'tool_access': 'Public service, not approved for this task'})

@pytest.mark.parametrize('description', ['', '   ', None, 'a' * 1501])
def test_invalid_input_never_calls_provider(description, monkeypatch):
    monkeypatch.setattr(classifier, 'complete_with_metadata', lambda *a, **k: pytest.fail('Provider should not run'))
    with pytest.raises(ClassificationError):
        classify_use_case(description)

def test_provider_metadata_and_parser(monkeypatch):
    monkeypatch.setattr(classifier, 'complete_with_metadata', lambda *a, **k: Completion(json.dumps(VALID), 'test', 'fixed-model', 'fixed-model', 50, 50))
    case, meta = classifier.classify_with_metadata(DESCRIPTION)
    assert case['tool_access'] == BASE['tool_access']
    assert meta['prompt_sha256'] and meta['requested_model'] == 'fixed-model'

def test_prompt_separates_unknown_from_risk_and_approval():
    text = build_system_prompt()
    assert 'untrusted data' in text and 'Do not infer approval' in text and (UNKNOWN in text)
