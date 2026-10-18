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


def _variant(name, description, **changes):
    return {'name': name, 'description': 'Synthetic example: ' + description, 'case': normalize_case({**BASE, **changes})}

def lookalike_pairs():
    """Pairs of made-up activities that read alike but differ in one detail the policy cares about."""
    return [
        {'id': 'information', 'title': 'Same assistant. Same task. Same careful review.',
         'a': _variant('Summarizing a public report', 'an approved enterprise assistant summarizes a public report for internal awareness.'),
         'b': _variant('Summarizing a client file', 'the same assistant summarizes personal client records for internal awareness.', information_involved='Personal or client data')},
        {'id': 'review', 'title': 'Same assistant. Same note. Different checking.',
         'a': _variant('Drafting an internal note, then reading it', 'an employee drafts an internal note with the assistant and revises it before sharing.', information_involved='Internal, non-sensitive information'),
         'b': _variant('Drafting an internal note, sent as is', 'an employee drafts an internal note with the assistant and shares it with little or no review.', information_involved='Internal, non-sensitive information', role_of_output='Content used with limited or no review')},
        {'id': 'expertise', 'title': 'Same assistant. Same kind of task. Different familiarity.',
         'a': _variant('Summarizing a topic you know well', 'an employee summarizes material in their own field and can judge whether the result is right.'),
         'b': _variant('Summarizing a topic you cannot judge', 'an employee summarizes material outside their field and cannot independently judge whether the result is right.', task_expertise="Outside the employee's expertise")},
        {'id': 'approval', 'title': 'Same enterprise tool. Same data. Different permission.',
         'a': _variant('Using the tool for a task it was approved for', 'an employee uses the enterprise assistant for the task it was approved to support.'),
         'b': _variant('Using the tool for a task nobody approved', 'an employee uses the enterprise assistant for a task that was never considered when it was approved.', approval_status='Not approved for this use')},
        {'id': 'code', 'title': 'Same code assistant. Different destination.',
         'a': _variant('Generating code to read through', 'an employee asks the assistant for code and reviews it before doing anything else.', forms=['technical'], information_involved='Internal, non-sensitive information'),
         'b': _variant('Generating code that goes live internally', 'an employee has the assistant generate code and deploys it to an internal system.', forms=['technical'], information_involved='Internal, non-sensitive information', role_of_output='Generated code deployed to an internal system')},
        {'id': 'public-tool', 'title': 'Same public AI service. Same client data. Different permission.',
         'a': _variant('Client data in a service approved for the task', 'an employee uses a public AI service that was approved for this task with personal client data.', tool_access='Public service, approved for this task', information_involved='Personal or client data'),
         'b': _variant('Client data in a service not approved', 'an employee puts personal client data into a public AI service that was not approved for this task.', tool_access='Public service, not approved for this task', information_involved='Personal or client data', approval_status='Not approved for this use')},
    ]
