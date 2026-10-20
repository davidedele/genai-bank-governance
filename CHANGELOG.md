# Change log

## Unreleased

- Gave the demo page a link preview (title, description and image), so a shared link shows a card instead of a bare address.
- Rewrote the README for readers who skim: the idea in one minute, the reasoning behind the design, the link from the thesis to the software, a full section on the Claude Code plugin, a section on the AI suggestions and a facts table.

## 0.3.0 - 2026-10-20

- The live demo now serves its own Python runtime instead of loading it from a public network. The build downloads the official Pyodide release, checks it against a fixed SHA-256 value and ships only the files the demo needs (about 16 MB), so the page contacts no third party (`scripts/fetch_pyodide.py`).
- The demo overview now opens at once. The start-up data is produced by the real app at build time and shown while Python downloads in the background. The downloads run side by side, and a status line shows steps 1 to 3 and what still waits.
- The background Claude Code run that suggests answers for captured prompts now starts with no tools and no MCP servers, so a captured prompt can never make it do more than answer.
- Malformed Host headers and non-ASCII workspace tokens now get a clean refusal instead of a server error, and validation errors no longer echo the submitted value, which fixed a server error on a JSON body containing NaN.
- The demo page carries a content security policy that allows only its own site, and its start-up settings moved out of an inline script. The runtime archive is unpacked with a check that refuses links and paths outside the target folder.
- Narrowed the permissions of the demo workflow.
- Added a short "What this shows" section, status badges and a short recording of the demo to the README, and refreshed the screenshots for this version.
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
