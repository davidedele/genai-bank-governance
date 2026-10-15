"""Synthetic examples, not observations of bank employees or validated labels."""
from copy import deepcopy
from data.framework import ILLUSTRATIVE_USE_CASES
from schema import normalize_case
BASE = {'forms': ['document_processing'], 'tool_access': 'Enterprise tool', 'approval_status': 'Approved for this use', 'information_involved': 'Public information', 'role_of_output': 'Initial draft, reviewed and revised by the employee', 'banking_process': 'Internal administrative process', 'task_expertise': "Routine, within the employee's expertise"}

def examples():
    public = {'id': 'public-summary', 'name': 'Summarizing a public report', 'description': 'Synthetic example: an approved enterprise assistant summarizes a public report for internal awareness. The employee has the expertise to review and revise the draft.', 'case': normalize_case(BASE)}
    private = {'id': 'client-summary', 'name': 'Summarizing a client file', 'description': 'Synthetic example: the same approved enterprise assistant summarizes personal client records for internal awareness. The employee has the expertise to review and revise the draft.', 'case': normalize_case({**BASE, 'information_involved': 'Personal or client data'})}
    result = [public, private]
    for i, original in enumerate(ILLUSTRATIVE_USE_CASES, 1):
        case = deepcopy(original)
        result.append({'id': f'thesis-inspired-{i}', 'name': case.pop('name'), 'description': 'Synthetic software illustration inspired by thesis Table 4. Unstated details remain unknown.', 'case': normalize_case(case)})
    return result
