"""
Reads the shared auto-classification log that the genai-usage-logger Claude
Code plugin/mod writes to.

That mod is a separate piece entirely, written as a hooks module (not
Python), that watches every prompt in a Claude Code session, logs it as
"pending", and periodically classifies pending entries against the same
five dimensions classifier.py uses, duplicated there since the mod's
environment cannot import this project's own code. This module is the
other half of that link: it reads the JSON-lines file the mod writes to
and turns "classified" entries into the same dict shape app.py's register
expects, so they show up in the Register tab without the employee typing
anything into Auto-classify themselves, the way a real usage log sitting
behind an enterprise AI gateway would need to work.

The file is line-delimited JSON (one entry per line) rather than a single
JSON array so the mod can append without re-parsing the whole file, and so
a reader here is tolerant of a line being mid-write: a line that fails to
parse is skipped rather than failing the whole read.
"""

import json
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "data" / "auto_log.jsonl"


def read_classified_entries(path: Path = DEFAULT_LOG_PATH) -> list[dict]:
    """Return every "classified" entry in the log, as register-shaped dicts.

    "pending" entries (not yet classified) and "failed" ones (the model's
    reply didn't validate) are left out: the Register tab should only ever
    show entries that actually carry all five dimensions.
    """
    if not path.exists():
        return []

    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            # Can happen if this read races the mod's own write; the next
            # scan interval will have a complete line to read instead.
            continue

        if raw.get("status") != "classified":
            continue

        entries.append(
            {
                "id": raw.get("id"),
                "name": raw.get("name", raw.get("text", "")[:80]),
                "form": raw.get("form"),
                "tool_access": raw.get("tool_access"),
                "information_involved": raw.get("information_involved"),
                "role_of_output": raw.get("role_of_output"),
                "banking_process": raw.get("banking_process"),
                "task_expertise": raw.get("task_expertise"),
                "source": "claude-code-auto",
                "logged_at": raw.get("classifiedAt", raw.get("loggedAt", "—")),
            }
        )
    return entries
