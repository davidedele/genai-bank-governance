"""
Runs the classifier in classifier.py against the labeled synthetic cases in
eval/cases.py and reports per-dimension accuracy, plus how often the
resulting risk-area flags and recommended action match what the hand-labeled
ground truth would produce.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python eval/run_eval.py

Writes a report to eval/results.md and prints a summary to the terminal.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.framework import DIMENSIONS
from mapper import flagged_risk_ids, recommended_action
from classifier import classify_use_case, ClassificationError
from eval.cases import CASES

DIM_IDS = [d["id"] for d in DIMENSIONS]


def main():
    per_dim_correct = {dim_id: 0 for dim_id in DIM_IDS}
    per_dim_correct["form"] = 0
    risk_set_matches = 0
    action_matches = 0
    rows = []
    failures = 0

    for i, case in enumerate(CASES, start=1):
        gt = case["ground_truth"]
        try:
            pred = classify_use_case(case["description"])
        except ClassificationError as e:
            print(f"[{i}] classification failed: {e}")
            failures += 1
            continue

        correct_fields = []
        for key in ["form"] + DIM_IDS:
            is_correct = pred.get(key) == gt.get(key)
            per_dim_correct[key] += int(is_correct)
            correct_fields.append(is_correct)

        gt_risks = set(flagged_risk_ids(gt))
        pred_risks = set(flagged_risk_ids(pred))
        risks_match = gt_risks == pred_risks
        risk_set_matches += int(risks_match)

        gt_action = recommended_action(gt)
        pred_action = recommended_action(pred)
        action_match = gt_action == pred_action
        action_matches += int(action_match)

        rows.append(
            {
                "n": i,
                "description": case["description"][:70] + "...",
                "fields_correct": f"{sum(correct_fields)}/{len(correct_fields)}",
                "risk_sets_match": "yes" if risks_match else "no",
                "action_match": f"{'yes' if action_match else 'no'} ({pred_action} vs {gt_action})",
            }
        )

    total = len(CASES) - failures
    if total == 0:
        print("All classifications failed, nothing to report.")
        return

    lines = ["# Classifier evaluation results\n"]
    lines.append(f"Evaluated {total} of {len(CASES)} synthetic cases ({failures} failed to classify).\n")
    lines.append("## Per-dimension accuracy\n")
    lines.append("| Dimension | Accuracy |")
    lines.append("|---|---|")
    lines.append(f"| form of use | {per_dim_correct['form']}/{total} |")
    for dim_id in DIM_IDS:
        lines.append(f"| {dim_id} | {per_dim_correct[dim_id]}/{total} |")
    lines.append("")
    lines.append(f"**Risk-area set exact match:** {risk_set_matches}/{total}")
    lines.append(f"**Recommended-action match:** {action_matches}/{total}\n")
    lines.append("## Per-case detail\n")
    lines.append("| # | Description | Fields correct | Risk sets match | Action match |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['n']} | {r['description']} | {r['fields_correct']} | "
            f"{r['risk_sets_match']} | {r['action_match']} |"
        )

    report = "\n".join(lines)
    out_path = Path(__file__).resolve().parent / "results.md"
    out_path.write_text(report)
    print(report)
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
