# Change log

## Unreleased

- Fixed saving with an empty parent identifier, which crashed the server instead of saving a new case.
- Closed a gap in the request size limit: chunked uploads had no declared length and were accepted at any size. They are now refused with a clear error.
- Made the tests independent of the machine they run on. A setting in your shell, a saved register or captured prompts could previously make three of them fail.
- Fixed the heading order and landmarks reported by an accessibility scan, and made the wording of the demo honest about where saved cases live.

- Added a live demo on GitHub Pages. The real app runs in the visitor's browser through Pyodide, so there is no server, no account and no cost, and GitHub rebuilds it on every push (`scripts/build_pages.py`, `.github/workflows/pages.yml`).
- Added an optional server demo mode (`GOVERNANCE_DEMO=1`) that turns off AI suggestions and prompt capture, accepts only named host names, caps the shared register and shows a demo notice.

## 0.2.0 - 2026-10-15

- Added an optional Claude Code plugin mode that saves prompts locally, lets Claude Code suggest answers in the background, lists them under Captured prompts in the Register, and adds a read-only skill for looking up saved reviews.
- Added explicit unknowns, overlapping forms of use and task-specific approval status.
- Separated the thesis taxonomy from a versioned, validated sample policy with reason IDs.
- Corrected generated-code, reviewer-expertise, unapproved-use and connected-system handling.
- Replaced the Streamlit frontend with a responsive local FastAPI/browser workspace.
- Added human correction, immutable SQLite revisions, policy/control snapshots and CSV/JSON export.
- Added server-side extraction provenance, bounded pending state and opt-in description retention.
- Replaced raw-prompt background logging with an opt-in, metadata-only command hook.
- Added independently specified policy scenarios and a 64-prompt synthetic extraction benchmark.
- Added API, storage, privacy, provider-contract, dataset and hook regression tests.
- Added project-level attribution settings; no commit or history changes are part of this release.
- Replaced unsupported security/accuracy language with explicit validation boundaries.

### Migration breaks

Run `python app.py`, not `streamlit run app.py`. The old session-only register is not automatically imported. Existing raw-prompt logs are neither imported nor deleted. Disable the installed old logger before installing the replacement. The new UI must not be exposed as an unauthenticated public service.
