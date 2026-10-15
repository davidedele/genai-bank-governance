"""
Automatic classification of a free-text employee generative AI use-case
description into the five dimensions developed in Chapter 3 of the thesis.

This is the part of the project that goes beyond the thesis itself: the
thesis defines the dimensions and argues, analytically, that they matter.
It does not attempt to detect them automatically or test whether that is
even feasible. This module does, using an LLM to read a plain description
of what an employee is doing and return a structured classification, which
the rest of the app then runs through the same risk-to-control mapping used
for manually entered use cases.

Requires an Anthropic API key in the ANTHROPIC_API_KEY environment
variable. See .env.example.
"""

import json
import os

from data.framework import DIMENSIONS, FORMS_OF_USE

MODEL = "claude-haiku-4-5"


class ClassificationError(Exception):
    pass


def _build_prompt(description: str) -> str:
    forms_block = "\n".join(
        f"- {f['id']}: {f['name']} ({f['description']})" for f in FORMS_OF_USE
    )
    dims_block = "\n\n".join(
        f"{d['id']} ({d['name']}): {d['question']}\nAllowed values: "
        + " | ".join(d["options"])
        for d in DIMENSIONS
    )
    return f"""You are classifying a short, plain-language description of something a bank
employee did with a generative AI tool, against a fixed set of categories.

Forms of use (pick exactly one id):
{forms_block}

Dimensions (pick exactly one of the allowed values for each, copied verbatim):
{dims_block}

Employee's description of what they did:
\"\"\"{description}\"\"\"

Classify this use case. Use only information stated or clearly implied by the
description. If a dimension cannot be determined from the description, pick
the most conservative (highest-risk) plausible value rather than guessing low,
since under-classifying risk is worse than over-classifying it.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{{
  "form": "<one form id>",
  "tool_access": "<one allowed value>",
  "information_involved": "<one allowed value>",
  "role_of_output": "<one allowed value>",
  "banking_process": "<one allowed value>",
  "task_expertise": "<one allowed value>",
  "rationale": "<one sentence on why you picked these>"
}}"""


def classify_use_case(description: str) -> dict:
    """Classify a free-text use-case description into the five dimensions.

    Returns a dict with keys: form, tool_access, information_involved,
    role_of_output, banking_process, task_expertise, rationale.
    Raises ClassificationError if the API call fails or the model's
    response cannot be parsed into a valid classification.
    """
    try:
        import anthropic
    except ImportError as e:
        raise ClassificationError(
            "The 'anthropic' package is not installed. Run: pip install anthropic"
        ) from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ClassificationError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env, add your "
            "key, and load it (e.g. `export $(cat .env | xargs)`) before running."
        )

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": _build_prompt(description)}],
        )
        raw = response.content[0].text.strip()
    except Exception as e:
        raise ClassificationError(f"Anthropic API call failed: {e}") from e

    # The model is asked for raw JSON; strip code fences defensively in case
    # it wraps the output anyway.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ClassificationError(f"Could not parse model output as JSON: {raw!r}") from e

    _validate(parsed)
    return parsed


def _validate(parsed: dict) -> None:
    form_ids = {f["id"] for f in FORMS_OF_USE}
    if parsed.get("form") not in form_ids:
        raise ClassificationError(f"Unrecognized form id: {parsed.get('form')!r}")
    for dim in DIMENSIONS:
        value = parsed.get(dim["id"])
        if value not in dim["options"]:
            raise ClassificationError(
                f"Unrecognized value for {dim['id']}: {value!r}"
            )
