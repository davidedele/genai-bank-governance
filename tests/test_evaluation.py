from copy import deepcopy
import pytest
from eval.cases import CASES
from eval.run_eval import summarize, validate_benchmark

def test_dataset_scope_is_explicit():
    meta = validate_benchmark()
    assert meta['prompts'] == 64 and meta['semantic_scenarios'] == 24

def test_failures_stay_in_denominator():
    cases = [CASES[0], CASES[3]]
    results = [{'prediction': cases[0]['ground_truth']}, {'error': 'unavailable', 'prediction': None}]
    metrics = summarize(cases, results)
    assert metrics['attempted'] == 2 and metrics['failure_rate'] == 0.5
    assert metrics['field_accuracy_all_attempts']['tool_access'] == 0.5
    assert metrics['missed_escalations_including_failures'] == 1

def test_policy_expected_results_are_not_recalculated_from_gold():
    case = deepcopy(CASES[0])
    case['expected_outcome'] = 'Do not proceed'
    metrics = summarize([case], [{'prediction': case['ground_truth']}])
    assert metrics['action_exact_all_attempts'] == 0 and metrics['missed_escalations_including_failures'] == 1

def test_every_attempt_needs_a_result():
    with pytest.raises(ValueError):
        summarize(CASES, [])
