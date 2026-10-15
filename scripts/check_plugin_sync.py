#!/usr/bin/env python3
"""
Guard against the genai-usage-logger plugin's prompt drifting from
classifier.py's.

register.ts cannot import data/framework.py or classifier.py (it runs in
its own sandboxed TypeScript environment with no access to this project's
Python modules), so FORMS_OF_USE, DIMENSIONS, and the banking_process note
are duplicated there by hand. That duplication already drifted out of sync
once during development (the plugin kept an older, looser banking_process
wording after classifier.py's was tightened). This script catches that
before it happens again silently.

This does not parse the TypeScript; it just checks that every string that
must be identical between the two sides (dimension ids/names/questions/
options, form ids/names/descriptions, and the banking_process note's exact
wording) appears verbatim inside register.ts's source text. Weaker than
parsing the TS AST, but dependency-free, fast, and it catches the failure
mode that actually happened.

Run this:
    python3 scripts/check_plugin_sync.py

Exits 0 and prints nothing but a confirmation on success; exits 1 and
prints exactly what's out of sync on failure. Intended to run before any
commit that touches classifier.py, data/framework.py, or register.ts, and
wired into CI (see .github/workflows/check-plugin-sync.yml) so a drifting
PR fails loudly instead of shipping quietly.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from classifier import _build_prompt  # noqa: E402
from data.framework import DIMENSIONS, FORMS_OF_USE  # noqa: E402

REGISTER_TS_PATHS = [
    REPO_ROOT / "claude-plugin" / "genai-usage-logger" / "hooks" / "register.ts",
]

# The banking_process note's exact wording, as classifier.py currently
# generates it. Extracted by slicing _build_prompt's own output between two
# fixed anchors already present on both sides, rather than re-typing the
# note a third time somewhere, which would just be a third copy to drift.
_PROMPT = _build_prompt("placeholder description")
_NOTE_START = "Note on banking_process specifically:"
_NOTE_END = "Employee's description of what they did:"


def _extract_banking_process_note(prompt: str) -> str:
    start = prompt.index(_NOTE_START)
    end = prompt.index(_NOTE_END, start)
    return prompt[start:end].strip()


def main() -> int:
    failures: list[str] = []

    note = _extract_banking_process_note(_PROMPT)

    for ts_path in REGISTER_TS_PATHS:
        if not ts_path.exists():
            failures.append(f"missing file: {ts_path}")
            continue
        ts_source = ts_path.read_text(encoding="utf-8")

        for form in FORMS_OF_USE:
            for field in ("id", "name", "description"):
                value = form[field]
                if value not in ts_source:
                    failures.append(
                        f"{ts_path.name}: missing form {form['id']!r} field "
                        f"{field!r} ({value!r})"
                    )

        for dim in DIMENSIONS:
            for field in ("id", "name", "question"):
                value = dim[field]
                if value not in ts_source:
                    failures.append(
                        f"{ts_path.name}: missing dimension {dim['id']!r} "
                        f"field {field!r} ({value!r})"
                    )
            for option in dim["options"]:
                if option not in ts_source:
                    failures.append(
                        f"{ts_path.name}: missing option {option!r} for "
                        f"dimension {dim['id']!r}"
                    )

        if note not in ts_source:
            failures.append(
                f"{ts_path.name}: banking_process note text does not match "
                "classifier.py's _build_prompt() verbatim"
            )

    if failures:
        print("Plugin/classifier drift detected:\n", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print(
            "\nFix: update the mismatched copy in register.ts (or "
            "classifier.py/data/framework.py) so the text matches exactly, "
            "then re-run this script.",
            file=sys.stderr,
        )
        return 1

    print("OK: register.ts matches classifier.py / data/framework.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
