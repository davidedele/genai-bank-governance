# Verification record - 15 October 2026

This record is a snapshot of version 0.2.0 on the date above. The test suite has grown since, and the current count is in the README.

Baseline: the supplied source at commit `86acc191419f109ea131a80b7e011607dc69a6d1`. Its 28 existing Python tests passed before modification.

## Executed locally

| Check | Result |
|---|---|
| Revised Python test suite | 113 tests passed on Python 3.13 |
| Policy invariant enumeration | 1,440 valid combinations checked within the test suite |
| Synthetic dataset validation | 64 prompts / 24 semantic scenarios; no model calls |
| Chromium workflow checks | Overview, manual review/save, revision history, exports, framework/validation pages, mobile layout passed |
| Browser runtime | No captured JavaScript page or console errors |
| Screenshot review | Desktop overview, assessment, register and validation; mobile overview |

The browser ran the actual HTML/CSS/JavaScript against a real FastAPI TestClient and temporary SQLite database using an offline fetch bridge. This avoids touching an existing workspace. It is not a deployment/network-browser test or live-model evaluation. Ordinary backend route and security-header behavior was separately exercised by API tests.

Provider-contract tests use mocked clients to verify request parameter names, retries, timeouts and metadata. They do not establish live endpoint availability or model quality. Hook tests invoke its Python script with synthetic inputs; they do not prove correct installation in the host application.

## Reproduce

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m eval.run_eval --validate-only
python scripts/check_package.py
```

Optional isolated browser run:

```bash
python -m pip install -r requirements-ui-test.txt
python -m playwright install chromium
python scripts/check_ui.py
# Or use an existing Chromium executable:
python scripts/check_ui.py --browser /path/to/chromium
```

Screenshots and the browser report are written under `.runtime/ui-check/` by default. The script uses synthetic records in a disposable database and does not call a model.

## Not executed

Live LLM evaluation; bank-data testing; independent banking-expert adjudication; live plugin installation; remote CI; production authentication/encryption/availability testing. Consequently there is no claimed classifier accuracy, bank risk reduction, compliance outcome or production-readiness certification.

Machine-readable evidence: [verification.json](verification.json).
