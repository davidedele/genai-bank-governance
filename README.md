# GenAI Bank Governance

**A research prototype for reviewing employee AI use, not just approving AI tools.**

An independent software extension of Davide Delegeanu's Bocconi bachelor's thesis, *The Use of Generative Artificial Intelligence in Banks: Governance, Risks, and Internal Controls* (2026).

The workspace describes an employee activity across five dimensions, maps relevant risks to the thesis's controls and responsible functions, and records a human-reviewed assessment. Optional model extraction assists data entry; a separate, inspectable policy determines the illustrative triage outcome.

![Workspace overview with a paired public-information and client-information example](docs/images/overview-desktop.png)

## Run locally

Python 3.10 or newer. The complete manual workflow runs without model credentials.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m eval.run_eval --validate-only
python app.py
```

Open **http://127.0.0.1:8501**. On Windows, activate the environment with `.venv\Scripts\activate`.

This release uses **FastAPI and a local HTML/CSS/JavaScript interface**, replacing the original Streamlit frontend. The launcher is now `python app.py`, not `streamlit run app.py`. The Python framework, optional provider layer and deterministic policy remain independently usable.

## What the application does

1. Start with a blank use case or a clearly labelled synthetic example.
2. Enter the known characteristics manually, or explicitly request extraction from a configured model.
3. Resolve unknowns and correct the classification. Tool approval and approval of this particular use are separate.
4. Examine triggered rules, relevant controls, responsible functions and remaining limitations.
5. Record the owner, reviewer and review note. Saving does not grant permission to use a tool.
6. Create new revisions rather than overwriting assessments. Export the complete history as JSON or a spreadsheet-safe CSV summary.

The five thesis dimensions are **tool/access, information, role of output, banking process, and task/employee expertise**. Multiple forms of use can apply. Approval status, explicit unknowns, triage rules and record versions are software extensions, not additional empirical findings of the thesis.

### Triage, not a risk score

| Outcome | Interpretation |
|---|---|
| Standard controls | No additional escalation under the illustrative policy; baseline controls still apply. Not approval. |
| Clarification required | Information needed for assessment is absent. |
| Review required | At least one explicit review condition applies. Unresolved information may still remain. |
| Do not proceed | Sensitive information and an explicitly unapproved use trigger a stop recommendation under the sample policy. Not technical enforcement. |

Policy rules are in [`data/policy.json`](data/policy.json). Each saved revision includes the exact policy, its hash, the applicable control text, the original prediction when available, reviewer corrections and model provenance. Historical records are not recalculated when a policy changes.

![Assessment showing rule explanations, uncertainty and control responsibilities](docs/images/assessment-desktop.png)

## Optional model extraction

```bash
python -m pip install -r requirements-llm.txt
```

Create a local `.env` by copying `.env.example` **only when you do not already have a `.env`**. Set:

```dotenv
ENABLE_LIVE_CLASSIFICATION=1
LLM_PROVIDER=anthropic
LLM_MODEL=your-account-model-identifier
ANTHROPIC_API_KEY=your-local-key
```

Supported adapter choices are `anthropic`, `openai`, `grok` and `gemini`; use the corresponding key name from `.env.example`. Choose a model that supports the selected text endpoint. No model availability, cost or accuracy is implied. Restart the app after editing configuration.

Extraction requires explicit confirmation in the interface before a description is sent to the provider. JSON/schema validation catches malformed output, not all semantic errors or prompt injection. Exact evidence excerpts aid review; they are not proof that an inferred category is true. Models can return unknown values, and reviewers can correct fields before saving.

The workspace caps daily classification operations at 30. An operation can contain up to three provider attempts; this is not a monetary spending cap. SDK retries are disabled to avoid multiplying retries. Individual requests have a 25-second timeout. See [architecture and provider notes](docs/ARCHITECTURE.md).

## Verification

This release was checked locally with **113 passing Python tests**. One test enumerates **1,440 valid combinations** to check policy invariants. These are not 1,440 model evaluations.

The evaluation dataset contains **64 synthetic prompts representing 24 semantic scenarios**. Several prompts are correlated wording variants; labels are not independently adjudicated by banking experts. No live-model accuracy is published or implied.

```bash
python -m pytest -q
python -m eval.run_eval --validate-only
# Explicitly configured, billable model evaluation:
python -m eval.run_eval --live --split holdout --output eval/results/holdout-run-01.json
```

The live evaluator includes failures in attempted-case denominators and compares outcomes against independently specified sample-policy expectations. Existing report files are never overwritten. Published reports must retain their model, dataset and policy metadata.

See the [verification record](docs/VERIFICATION.md), [dataset card](docs/DATASET_CARD.md) and [policy decision table](docs/POLICY.md).

## Privacy and deployment boundaries

**Local, single-user research prototype. Do not deploy this publicly or enter real banking/customer data.**

The database is local SQLite. Descriptions, model excerpts and rationales are not persisted unless explicitly selected; record names, owner/reviewer fields and notes are always stored. Pending model classifications remain in process memory until expiry cleanup, eviction or shutdown. Do not place secrets in any field.

There is no authenticated reviewer identity, encryption at rest, tamper-proof log, legal classification or enterprise approval workflow. A database record does not prove that a control operated. Local origin/token checks are defense in depth, not a substitute for authentication.

The optional prompt hook is **metadata-only, opt-in and retrospective**. It makes no classification call and cannot prevent a submitted prompt. The previous raw-prompt auto-classification hook has been removed. Updating source does not unload an already installed old plugin: disable the old installation before testing the replacement. See [privacy and hook migration](docs/PRIVACY.md).

![Saved synthetic assessments in the local register](docs/images/register-desktop.png)

## Project structure

```text
app.py                 Local HTTP application and boundary checks
web/                   Responsive browser interface
schema.py              Classification contract and explicit unknown values
data/framework.py      Thesis taxonomy, controls and illustrative examples
data/policy.json       Versioned, declarative triage rules
classifier.py          Model extraction and output validation
providers.py           Optional provider adapters and bounded retries
mapper.py              Explainable risk/control mapping and triage
storage.py             Local revision records and CSV/JSON export
eval/                  Synthetic benchmark and reporting
tests/                 Offline regression and integration checks
claude-plugin/         Optional metadata-only prompt-event hook
scripts/               Release hygiene and isolated UI verification
```

## Research basis

Delegeanu, D. (2026). *The Use of Generative Artificial Intelligence in Banks: Governance, Risks, and Internal Controls*. Bocconi University. Sections 3.2-3.3 define the forms and dimensions; Sections 5.2-5.6 connect use cases, controls and responsibilities. The thesis is a literature-based analytical synthesis, not empirical validation using bank workflows.

This repository does not assert compliance with the AI Act, GDPR, DORA or any other legal framework. The controls and policy are illustrative. An organization would need to define its own acceptable uses, review requirements and risk acceptance.

[Research-to-software mapping](docs/RESEARCH_MAPPING.md) · [Demonstration script](docs/DEMO.md) · [Change log](CHANGELOG.md)
