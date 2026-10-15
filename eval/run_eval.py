"""Separate extraction evaluation from policy tests. No live calls without --live."""
import argparse
import hashlib
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from eval.cases import CASES, DATASET, DATASET_PATH
from schema import DIMENSION_IDS, normalize_case
from mapper import assess_use_case, load_policy
from classifier import classify_with_metadata, ClassificationError
FIELDS = ['forms', *DIMENSION_IDS, 'approval_status']

def validate_benchmark():
    ids = set()
    for c in CASES:
        assert c['id'] not in ids
        ids.add(c['id'])
        assert len(c['description']) <= 1500
        normalize_case(c['ground_truth'], require_all=True)
        assert c['expected_outcome'] in ['Standard controls', 'Clarification required', 'Review required', 'Do not proceed']
    return {'prompts': len(CASES), 'semantic_scenarios': len({c['scenario_id'] for c in CASES}), 'dataset_sha256': hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()}

def summarize(cases, results):
    if len(cases) != len(results):
        raise ValueError('Every attempted case must have a result, including failures.')
    n = len(cases)
    correct = {f: 0 for f in FIELDS}
    failures = exact = risk_exact = action_exact = missed = 0
    tp = fp = fn = required = 0
    for c, r in zip(cases, results):
        expected = c['expected_outcome']
        needs_review = expected in ['Review required', 'Do not proceed']
        required += int(needs_review)
        if r.get('error') or r.get('prediction') is None:
            failures += 1
            missed += int(needs_review)
            fn += len(c['expected_risk_ids'])
            continue
        predicted = normalize_case(r['prediction'])
        truth = normalize_case(c['ground_truth'])
        matches = [predicted[f] == truth[f] for f in FIELDS]
        for f, match in zip(FIELDS, matches):
            correct[f] += int(match)
        exact += int(all(matches))
        assessment = assess_use_case(predicted)
        actual_risks = set(assessment['risk_ids'])
        expected_risks = set(c['expected_risk_ids'])
        tp += len(actual_risks & expected_risks)
        fp += len(actual_risks - expected_risks)
        fn += len(expected_risks - actual_risks)
        risk_exact += int(actual_risks == expected_risks)
        actual = assessment['outcome']
        action_exact += int(actual == expected)
        missed += int(needs_review and (actual not in ['Review required', 'Do not proceed'] or (expected == 'Do not proceed' and actual != 'Do not proceed')))
    rate = lambda x, d: round(x / d, 6) if d else None
    return {'attempted': n, 'failures': failures, 'failure_rate': rate(failures, n), 'field_accuracy_all_attempts': {f: rate(x, n) for f, x in correct.items()}, 'exact_classification_all_attempts': rate(exact, n), 'risk_set_exact_all_attempts': rate(risk_exact, n), 'action_exact_all_attempts': rate(action_exact, n), 'risk_precision': rate(tp, tp + fp), 'risk_recall_including_failures': rate(tp, tp + fn), 'required_escalation_cases': required, 'missed_escalations_including_failures': missed, 'scope': 'Agreement with synthetic labels and illustrative policy, not empirical risk reduction.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--split', choices=['all', 'development', 'holdout'], default='all')
    parser.add_argument('--output', type=Path, default=Path('eval/results/run.json'))
    args = parser.parse_args()
    coverage = validate_benchmark()
    if not args.live or args.validate_only:
        print(json.dumps({**coverage, 'live_calls': 0, 'accuracy': 'not measured'}, indent=2))
        return
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
    if os.environ.get('ENABLE_LIVE_CLASSIFICATION') != '1':
        parser.error('Enable live classification explicitly in your local configuration first.')
    from providers import current_provider_id, current_model, PROVIDERS, ProviderError
    try:
        pid = current_provider_id()
        current_model(pid)
        if not os.environ.get(PROVIDERS[pid]['api_key_env'], '').strip():
            raise ProviderError('The selected provider key is not configured.')
    except ProviderError as e:
        parser.error(str(e))
    if args.output.exists():
        parser.error('Output already exists. Choose a new filename before making API calls.')
    selected = [c for c in CASES if args.split == 'all' or c['split'] == args.split]
    results = []
    for c in selected:
        started = time.monotonic()
        try:
            prediction, metadata = classify_with_metadata(c['description'])
            row = {'id': c['id'], 'prediction': prediction, 'metadata': metadata}
        except ClassificationError as e:
            row = {'id': c['id'], 'prediction': None, 'error': str(e)}
        row['elapsed_seconds'] = round(time.monotonic() - started, 4)
        results.append(row)
        print(c['id'], 'failed' if row.get('error') else 'completed')
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(), 'dataset_version': DATASET['version'], **coverage, 'split': args.split, 'policy_snapshot': load_policy(), 'summary': summarize(selected, results), 'results': results, 'limitations': ['Synthetic cases and correlated variants; not independent observations.', 'No banking-expert adjudication or evidence of reduced operational risk.', 'Token usage is returned per successful request; it may omit charges from failed attempts.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print('Report:', args.output)
if __name__ == '__main__':
    main()
