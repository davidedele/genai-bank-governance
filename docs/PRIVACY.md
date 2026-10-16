# Privacy boundaries and hook migration

## Default operation

The manual workspace is local. It has no telemetry or CDN dependencies. The launcher binds to `127.0.0.1`, rejects unexpected Host/Origin values, and requires a workspace token for mutations. These checks do not authenticate a user. Anybody able to access the local process or database may access its contents.

Live classification is off until `ENABLE_LIVE_CLASSIFICATION=1`, and the interface requires per-request consent. The description is sent to the configured external provider. Its processing terms, retention and regional settings must be reviewed separately; this project does not configure or certify them.

Record names, owner/reviewer fields and review notes are always retained. Description, rationale and evidence excerpts are retained only when selected. Do not enter customer information or secrets, including in names and notes. Pending extraction data resides in process memory, with count-bounded storage and expiry cleanup during subsequent operations; restart the app to release the process. There is no encryption at rest or secure-memory-erasure claim.

## Public demo mode

`GOVERNANCE_DEMO=1` is for a throwaway copy online, deployed with `render.yaml`. In this mode the app also accepts the host names in `GOVERNANCE_ALLOWED_HOSTS` and `RENDER_EXTERNAL_HOSTNAME`, and nothing else. Live AI classification and prompt capture are off even if their settings are present. Every visitor sees the same register, it lives in a temporary file that is lost when the service restarts, and it stops accepting new cases at 300. There is still no login, so the demo must only ever hold made-up information, and the page says so. Do not set `GOVERNANCE_DEMO=1` for real use.

## The old logger is not preserved

The previous hook recorded raw prompts and sent them for background classification after submission. That created an additional sensitive-content store and processing path without preventing the original action. Its in-memory/update logic was also a poor basis for durable concurrent records.

By default the replacement observes **only** timestamp, event type, random event ID and prompt character count. Prompt text is kept only if you also set `GENAI_CAPTURE_PROMPTS=1`, as described in [PLUGIN.md](PLUGIN.md). It does not retain a prompt hash, transcript path, session ID or working directory. In the default mode no prompt content is kept and no model is called. A prompt event is not a complete business use case and is not inserted into the use-case register.

### Migrate before testing

Disable/uninstall the old `genai-usage-logger` installation in the host's plugin manager and close existing sessions. Updating this repository does not unload a cached, already installed older plugin. Leave metadata logging disabled until you have installed the replacement and verified its command-hook configuration. Do not enable both versions.

The command-hook definition is in `claude-plugin/genai-usage-logger/hooks/hooks.json`. It invokes the bundled Python script for `UserPromptSubmit`. The script is opt-in:

```bash
export GENAI_LOG_METADATA=1
export GENAI_EVENT_DB="$HOME/.local/share/genai-governance/events.sqlite"
```

The path must be absolute. Directories created by the hook request mode 0700 and the database requests 0600 on POSIX. There are at most 1,000 retained events; entries older than seven days are removed during the next successful write. **No scheduler deletes them when no further events occur.** Disable logging by unsetting `GENAI_LOG_METADATA`. Stop the host before deleting its event database when permanent local removal is intended; this is not forensic secure erasure and does not remove backups.

Starting the app with the same metadata environment variables shows the retained event count separately from assessment records. Tests verify the hook's Python behavior, metadata-only persistence and concurrent writes. Installation inside a real Claude Code session has not been exercised for this release.

## Existing local files

The uploaded working directory included ignored local configuration and raw-log files. Neither is included in the release. The upgrade installer intentionally leaves existing `.env`, logs and databases untouched. Review their retention locally. Do not publish an archive of the whole working folder.

After reviewing and committing only the intended source, a source-only archive can be created with:

```bash
git archive --format=zip --output=../genai-bank-governance-source.zip HEAD
```

The release hygiene check detects common runtime/private artifacts in tracked files. It is not a comprehensive secret scanner and cannot revoke credentials previously disclosed elsewhere.

## Attribution

The shared project settings disable commit, PR and session-link attribution. No history, author or committer metadata is shipped in the source release. The installer neither stages nor commits anything. Existing local or managed settings may take precedence; ordinary Git author identity remains your own Git configuration. Avoid applying mail patches with an unwanted author header.

Settings reference: https://code.claude.com/docs/en/settings-reference


## Optional prompt capture and suggestions

With `GENAI_CAPTURE_PROMPTS=1` the hook also keeps the prompt text (up to 8,000 characters) in a local file, `~/.local/share/genai-governance/events.sqlite` unless `GENAI_EVENT_DB` says otherwise, readable only by you, with at most 1,000 prompts and a seven day limit. Claude Code, run in non-interactive mode with your existing login, then suggests answers for each prompt in the background. That step sends the prompt to the same service that is already answering it, and counts against your Claude usage, bounded by `GENAI_CLASSIFY_LIMIT`. Set `GENAI_AUTO_CLASSIFY=0` to keep the text without any suggestion step. The workspace validates every suggestion, never counts a captured prompt as a reviewed use case, and can delete one or all captured prompts. Details and settings are in [PLUGIN.md](PLUGIN.md).
