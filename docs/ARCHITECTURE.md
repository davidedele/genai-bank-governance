# Architecture and implementation notes

## Processing path

```text
Known facts / optional model extraction
                 |
       schema and evidence validation
                 |
      explicit reviewer corrections
                 |
    declarative policy + thesis controls
                 |
   versioned local assessment / export
```

The model does not authorize activities or invent controls. It extracts categories and evidence into a bounded contract. The policy layer uses known predicates and returns reasons. Missing information remains visible even when a known fact already triggers review or a stop recommendation.

`data/framework.py` retains the thesis's nine descriptive risk areas, including the combined information-security/third-party label. A connected internal application triggers its security component without establishing that an external provider is involved. The code explicitly explains that distinction.

## Records and corrections

SQLite stores a new row for every assessment revision. Saving a revision requires the latest parent ID; stale edits are rejected. A transaction covers parent checking and insertion. JSON export preserves all revisions, classifications, policy snapshots, control wording and provenance; CSV is a smaller summary with formula-leading cells escaped.

Model predictions are held server-side so a browser cannot manufacture provider provenance simply by submitting a provider name. Pending classifications are capped at 100 and expire after 20 minutes when the next classification/save cleanup runs; shutdown releases the process. The prototype does not promise immediate memory erasure at the expiry boundary.

When a reviewer changes a field, the record retains its original and corrected values and removes stale evidence for that field. Text retention is explicit: with retention off, rationale and excerpts are removed from both versions before persistence. Original model/request identifiers, token counts and prompt version/hash remain as non-content provenance.

The exact applied controls are frozen with their framework hash. A later reassessment is a new revision under the then-current policy. SQLite immutability is an application convention, not cryptographic tamper resistance or access control.

## Provider adapters

Anthropic uses its Messages endpoint. OpenAI, xAI and Gemini use the OpenAI-compatible Chat Completions interface. OpenAI requests use `max_completion_tokens`; the other compatibility adapters use `max_tokens`. Model-specific endpoint support still requires a real smoke test in the user's account.

There is one application retry layer. Only transient failures (timeouts, connections, 408, 409, 429 and 5xx) are retried, at most three times. Permanent authentication and validation errors are not retried. Long Retry-After values stop the operation instead of waiting unboundedly. SDK retries are set to zero. Provider error bodies are not copied into the UI or stored records.

Sampling uses provider defaults; it is not claimed deterministic. Response and requested model identifiers are retained where available. A token cap may include reasoning tokens depending on the model; a truncated response becomes a failed classification rather than a partial assessment.

## Interface decision

The interface is a small, dependency-light FastAPI backend and ordinary browser assets. This gives direct control over the reading order, review workflow, responsive layout and API-level tests without introducing a frontend build system. The tradeoff is maintaining explicit HTTP routes and browser state.

No Node build is required. Python 3.10+ is required by the type syntax. The release was executed locally under Python 3.13; the included CI matrix targets 3.10 and 3.12 but has not been run remotely for this release.

## Technical references checked for this release

- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Python SQLite: https://docs.python.org/3/library/sqlite3.html
- OpenAI Python client: https://github.com/openai/openai-python
- OpenAI completion token limits: https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create
- Gemini compatibility: https://ai.google.dev/gemini-api/docs/openai
- xAI Chat Completions: https://docs.x.ai/developers/rest-api-reference/inference/chat-completions
- Claude Code hooks: https://code.claude.com/docs/en/hooks

These references support API and implementation choices, not banking-policy correctness.
