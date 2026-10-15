"""Classification contract. Unknown values are application extensions to the thesis."""
from copy import deepcopy
from data.framework import DIMENSIONS, FORMS_OF_USE
APP_VERSION = '0.2.0'
SCHEMA_VERSION = '2.0'
FRAMEWORK_VERSION = 'thesis-2026'
UNKNOWN = 'Unknown - clarification required'
APPROVAL_OPTIONS = ['Approved for this use', 'Not approved for this use', UNKNOWN]
DIMENSION_IDS = [d['id'] for d in DIMENSIONS]
FORM_IDS = [f['id'] for f in FORMS_OF_USE]

class ValidationError(ValueError):
    pass

def normalize_case(raw: dict, *, require_all: bool=False) -> dict:
    """Return a typed, bounded case. Never turn missing information into an assertion."""
    if not isinstance(raw, dict):
        raise ValidationError('Classification must be a JSON object.')
    out = {}
    for dim in DIMENSIONS:
        key = dim['id']
        if require_all and key not in raw:
            raise ValidationError(f'Missing dimension: {key}')
        value = raw.get(key, UNKNOWN)
        if not isinstance(value, str) or value not in dim['options'] + [UNKNOWN]:
            raise ValidationError(f'Invalid category for {key}.')
        out[key] = value
    forms = raw.get('forms')
    if forms is None:
        form = raw.get('form', 'unknown')
        forms = [] if form == 'unknown' else [form]
    if not isinstance(forms, list) or len(forms) > len(FORM_IDS):
        raise ValidationError('Forms must be a list of known identifiers.')
    if any((not isinstance(f, str) or f not in FORM_IDS for f in forms)):
        raise ValidationError('Invalid form of use.')
    out['forms'] = [f for f in FORM_IDS if f in forms]
    out['form'] = out['forms'][0] if out['forms'] else 'unknown'
    approval = raw.get('approval_status', UNKNOWN)
    tool = out['tool_access']
    implied = {'Public service, not approved for this task': APPROVAL_OPTIONS[1], 'Public service, approved for this task': APPROVAL_OPTIONS[0]}.get(tool)
    if approval == UNKNOWN and implied:
        approval = implied
    if not isinstance(approval, str) or approval not in APPROVAL_OPTIONS:
        raise ValidationError('Invalid use-approval status.')
    if implied and approval != implied:
        raise ValidationError('Tool category and use-approval status contradict each other.')
    out['approval_status'] = approval
    rationale = raw.get('rationale', '')
    if not isinstance(rationale, str) or len(rationale) > 1500:
        raise ValidationError('Rationale must be text of at most 1,500 characters.')
    out['rationale'] = rationale
    evidence = raw.get('evidence', {})
    if not isinstance(evidence, dict) or any((k not in DIMENSION_IDS + ['approval_status'] for k in evidence)):
        raise ValidationError('Evidence must refer to known fields.')
    if any((not isinstance(v, str) or len(v) > 1500 for v in evidence.values())):
        raise ValidationError('Each evidence excerpt must be bounded text.')
    out['evidence'] = deepcopy(evidence)
    return out

def unresolved_fields(case: dict) -> list[str]:
    fields = [key for key in DIMENSION_IDS + ['approval_status'] if case[key] == UNKNOWN]
    if not case['forms']:
        fields.append('forms')
    return fields
