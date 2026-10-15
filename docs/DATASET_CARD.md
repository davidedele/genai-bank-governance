# Dataset card: employee-use extraction benchmark

**File:** `eval/benchmark.json`  
**Version:** synthetic-0.2.0  
**Size:** 64 prompts across 24 semantic scenarios  
**Origin:** authored synthetic cases; no bank, customer or employee observations

Twenty scenarios have three related wording/order variants. Four additional scenarios test sparse, ambiguous or adversarial descriptions. The 64 prompts must not be described as 64 independent observations or as a representative distribution of employee activity.

## Labels

Each case contains a reviewed specification of its expected categories, relevant risk IDs and illustrative triage outcome. Expected policy outcomes and risks are stored explicitly; they are not computed by calling the mapper to generate the answer key. This prevents the earlier evaluation design from validating the mapper against itself.

Labels were prepared for software development, not adjudicated by an independent banking panel. A benchmark can disagree with a practitioner because the task is ambiguous, the policy is underspecified or a label is wrong. Such disagreements should be recorded, not hidden by redefining a correct answer after seeing model predictions.

## Splits

Scenarios S01-S10 are development cases; remaining scenarios are holdout cases. Related wording variants stay in the same split. All cases are public, so this is a procedural development/holdout separation, not a secret benchmark or contamination guarantee.

## Reported measurements

The evaluator reports attempted cases and failures; per-field and exact-case agreement over all attempts; exact risk-set and action agreement; risk precision and recall; and missed required escalations including failures. A failed stop/review case counts as missed escalation. Token usage and elapsed time are recorded per available provider response. Failed requests can still incur charges not captured in successful-response token totals.

No live-model results are included in this release. `--validate-only` checks dataset structure and coverage without contacting providers. Unit-test success and dataset validity are not classification accuracy.

## Reproducible next experiment

Choose an explicit model available in your account. Use the development split to identify prompt errors; record all changes. Freeze the prompt and policy, then run the holdout split with a new report filename. Repeat against another provider only after the first run is inspected. Report per-scenario failures and recurring ambiguity, not only an overall percentage.

Independent expert labels and real-world observational validation would be separate studies. This dataset cannot establish reduced operational risk, legal compliance or commercial demand.
