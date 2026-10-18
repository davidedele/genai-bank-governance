import itertools
import pytest
from data.framework import DIMENSIONS, ILLUSTRATIVE_USE_CASES
from demo_examples import BASE
from schema import UNKNOWN, ValidationError
from mapper import assess_use_case, load_policy, validate_policy
from eval.cases import CASES

@pytest.mark.parametrize('case', [c for c in CASES if c['id'].endswith('V1') or '-V' not in c['id']], ids=lambda c: c['id'])
def test_independent_policy_scenarios(case):
    result = assess_use_case(case['ground_truth'])
    assert result['outcome'] == case['expected_outcome']
    assert set(result['risk_ids']) == set(case['expected_risk_ids'])

def test_examples_do_not_crash():
    for c in ILLUSTRATIVE_USE_CASES:
        assess_use_case(c)

def test_existing_sample_contradiction_is_fixed():
    c = next((c for c in ILLUSTRATIVE_USE_CASES if c['name'].startswith('Using an approved tool')))
    assert c['approval_status'] == 'Not approved for this use'
    assert 'shadow_ai' in assess_use_case(c)['risk_ids']

def test_internal_connection_flags_security_without_inventing_external_provider():
    a = assess_use_case({**BASE, 'tool_access': 'Internal application connected to bank systems'})
    assert 'infosec_third_party' in a['risk_ids']
    assert 'not established' in a['notes'][0]

def test_no_silent_default_approval():
    c = {k: v for k, v in BASE.items() if k != 'approval_status'}
    assert assess_use_case(c)['outcome'] == 'Clarification required'

def test_known_block_survives_unknown_expertise():
    c = {**BASE, 'information_involved': 'Personal or client data', 'approval_status': 'Not approved for this use', 'task_expertise': UNKNOWN}
    a = assess_use_case(c)
    assert a['outcome'] == 'Do not proceed' and 'task_expertise' in a['unresolved']

def test_missing_data_never_means_standard_controls():
    policy = load_policy()
    for key in [d['id'] for d in DIMENSIONS] + ['approval_status']:
        assert assess_use_case({**BASE, key: UNKNOWN}, policy)['outcome'] != 'Standard controls'

@pytest.mark.parametrize('key,bad', [('version', ''), ('risk_rules', []), ('triage_rules', [])])
def test_policy_schema_rejects_empty_sections(key, bad):
    p = load_policy()
    p[key] = bad
    with pytest.raises(ValueError):
        validate_policy(p)

def test_policy_hash_changes_when_rules_change():
    p = load_policy()
    a = assess_use_case(BASE, p)
    p['triage_rules'][0]['reason'] += ' Changed.'
    b = assess_use_case(BASE, p)
    assert a['policy_sha256'] != b['policy_sha256']

def test_exhaustive_fully_known_combinations():
    policy = load_policy()
    count = 0
    for values in itertools.product(*(d['options'] for d in DIMENSIONS)):
        for approval in ['Approved for this use', 'Not approved for this use', UNKNOWN]:
            c = {**dict(zip([d['id'] for d in DIMENSIONS], values)), 'forms': ['document_processing'], 'approval_status': approval}
            try:
                a = assess_use_case(c, policy)
            except ValidationError:
                continue
            count += 1
            if a['outcome'] == 'Standard controls':
                assert not a['unresolved'] and (not a['rule_hits'])
                assert c['task_expertise'] != "Outside the employee's expertise"
                assert c['role_of_output'] == 'Initial draft, reviewed and revised by the employee'
            if c['information_involved'] in ['Personal or client data', 'Confidential or proprietary information'] and c['approval_status'] == 'Not approved for this use':
                assert a['outcome'] == 'Do not proceed'
    assert count == 1440
