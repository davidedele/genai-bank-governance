"""Explainable use-case triage. The policy is illustrative, not a risk rating."""
import hashlib
import json
from pathlib import Path
from copy import deepcopy
from data.framework import DIMENSIONS, RISK_AREAS
from schema import FRAMEWORK_VERSION, SCHEMA_VERSION, UNKNOWN, APPROVAL_OPTIONS, normalize_case, unresolved_fields
POLICY_PATH = Path(__file__).resolve().parent / 'data' / 'policy.json'
OUTCOMES = ['Standard controls', 'Clarification required', 'Review required', 'Do not proceed']

def load_policy(path: Path=POLICY_PATH) -> dict:
    policy = json.loads(Path(path).read_text(encoding='utf-8'))
    validate_policy(policy)
    return policy

def validate_policy(policy: dict) -> None:
    allowed = {d['id']: d['options'] + [UNKNOWN] for d in DIMENSIONS}
    allowed['approval_status'] = APPROVAL_OPTIONS
    risk_ids = {r['id'] for r in RISK_AREAS}
    if not isinstance(policy, dict) or not isinstance(policy.get('version'), str) or (not policy['version']):
        raise ValueError('Policy needs a nonempty version.')
    for group in ('risk_rules', 'triage_rules'):
        rules = policy.get(group)
        if not isinstance(rules, list) or not rules:
            raise ValueError('Policy rule groups must be nonempty lists.')
        ids = set()
        for rule in rules:
            if not isinstance(rule, dict) or not isinstance(rule.get('id'), str) or rule['id'] in ids:
                raise ValueError('Policy identifiers must be unique within a group.')
            ids.add(rule['id'])
            if not isinstance(rule.get('reason'), str) or not rule['reason']:
                raise ValueError('Every rule needs a reason.')
            if group == 'risk_rules' and rule['id'] not in risk_ids:
                raise ValueError('Policy references an unknown thesis risk area.')
            if group == 'triage_rules' and rule.get('outcome') not in OUTCOMES[2:]:
                raise ValueError('Triage rules may only escalate to review or do-not-proceed.')
            if not (rule.get('any') or rule.get('all')):
                raise ValueError('Unconditional policy rules are not supported.')
            for key in ('any', 'all'):
                if key in rule and (not isinstance(rule[key], list) or not rule[key]):
                    raise ValueError('Condition lists must be nonempty.')
                for c in rule.get(key, []):
                    if not isinstance(c, dict) or c.get('field') not in allowed or (not isinstance(c.get('in'), list)) or (not c['in']):
                        raise ValueError('Invalid policy condition.')
                    if any((v not in allowed[c['field']] for v in c['in'])):
                        raise ValueError('Policy contains an unknown category.')

def _matches(rule: dict, case: dict) -> bool:
    test = lambda c: case[c['field']] in c['in']
    return (not rule.get('all') or all((test(c) for c in rule['all']))) and (not rule.get('any') or any((test(c) for c in rule['any'])))

def assess_use_case(raw: dict, policy: dict | None=None) -> dict:
    case = normalize_case(raw)
    policy = load_policy() if policy is None else deepcopy(policy)
    validate_policy(policy)
    risks = [r for r in policy['risk_rules'] if _matches(r, case)]
    hits = [r for r in policy['triage_rules'] if _matches(r, case)]
    missing = unresolved_fields(case)
    if any((r['outcome'] == 'Do not proceed' for r in hits)):
        outcome = 'Do not proceed'
    elif hits:
        outcome = 'Review required'
    elif missing:
        outcome = 'Clarification required'
    else:
        outcome = 'Standard controls'
    # The thesis combines security and provider dependency in one descriptive label.
    contexts = []
    if case['tool_access'] == 'Internal application connected to bank systems':
        contexts.append('Connected-access security applies; third-party dependency is not established by this category alone.')
    if missing:
        contexts.append('Missing information must be resolved; known review or stop reasons remain in force.')
    if not hits and (not missing):
        contexts.append('No additional escalation under this illustrative policy. Baseline controls still apply; this is not approval.')
    policy_bytes = json.dumps(policy, sort_keys=True, separators=(',', ':')).encode()
    return {'outcome': outcome, 'risk_ids': [r['id'] for r in RISK_AREAS if any((r['id'] == x['id'] for x in risks))], 'risk_reasons': {r['id']: r['reason'] for r in risks}, 'rule_hits': [{'id': r['id'], 'reason': r['reason'], 'outcome': r['outcome']} for r in hits], 'unresolved': missing, 'notes': contexts, 'baseline_controls': ['Use only within the assessed purpose and approved data boundary.', 'Verify material outputs and retain proportionate review evidence.'], 'policy_version': policy['version'], 'policy_sha256': hashlib.sha256(policy_bytes).hexdigest(), 'policy_snapshot': policy, 'framework_version': FRAMEWORK_VERSION, 'schema_version': SCHEMA_VERSION, 'risk_details': deepcopy([r for r in RISK_AREAS if any((r['id'] == x['id'] for x in risks))]), 'framework_sha256': hashlib.sha256(json.dumps(RISK_AREAS, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}

def flagged_risk_ids(use_case: dict) -> list[str]:
    return assess_use_case(use_case)['risk_ids']

def recommended_action(use_case: dict) -> str:
    return assess_use_case(use_case)['outcome']

def risk_areas_by_id() -> dict:
    return {r['id']: r for r in RISK_AREAS}
