# GenAI Use-Case Register for Banks

Built on my Bachelor's thesis at Bocconi University:

> Delegeanu, D. (2026). *The Use of Generative Artificial Intelligence in Banks: Governance, Risks, and Internal Controls.* Bachelor's thesis, Bocconi University.

The thesis argues that employee generative AI use in banks cannot be governed by looking at the tool alone. It develops a framework built around four recurring **forms of use**, five **dimensions** for comparing individual use cases, and an integrated table connecting the resulting risk mechanisms to control objectives, illustrative controls and responsible parties, organized around the Three Lines Model. It also explicitly says what it doesn't do: it identifies circumstances in which risk mechanisms may arise, but it does not test the framework against data (Sections 2.5 and 6).

This project does two things the thesis itself doesn't. It turns the framework into a working **use-case register**, the control the thesis proposes in Section 5.2 but only describes on paper. And it adds an **automatic classifier** on top of that register: instead of filling in a form, you describe what you did in plain language, and an LLM reads the description and infers the five dimensions itself, the way a real usage log sitting behind an enterprise AI gateway would need to work. A small labeled evaluation set then tests how well that classification actually holds up, which is a first, modest answer to the thesis's own open question about validating the framework against data.

## What it does

- **Auto-classify.** Describe a use case in your own words (e.g. "I pasted a client's loan file into ChatGPT's public website and asked it to recommend whether to approve the loan"). An LLM classifies it against the thesis's five dimensions, the app maps that to the relevant risk areas and a recommended action (Logged, Flagged for review, or Block recommended), and logs the entry automatically with a timestamp.
- **Register.** A running log of every use case, manual or auto-classified, pre-loaded with six synthetic examples inspired by the thesis's Table 4. Exportable as CSV.
- **Add manually.** The original form-based entry: pick the form of use and a value for each dimension directly.
- **Classifier accuracy.** Points at `eval/`, where the classifier is tested against 16 hand-written, synthetic, labeled use cases, with per-dimension accuracy reported.
- **The framework.** The underlying tables from the thesis (four forms of use, five dimensions, the full nine-area risk-to-control comparison) laid out for reference.

## How to use it

Once `streamlit run app.py` opens the app in your browser, there are five tabs across the top.

**Auto-classify** is the main one. Type a plain-language description of something a bank employee did with a generative AI tool, for example "I pasted a client's loan file into ChatGPT's public website and asked it to recommend whether to approve the loan," and click Classify and log. You'll get back five tiles (one per dimension the thesis defines), the model's one-line reasoning, and a panel below showing every risk area that applies, each with its control objective, suggested controls, who'd typically be responsible, and the thesis's own stated limitation of that control. At the top of that panel is an Action badge: green "Logged" for routine, low-risk activity, orange "Flagged for review" for something a bank's compliance or risk team would want to look at, red "Block recommended" for a combination (like confidential client data going to an unapproved public tool) that a policy would typically stop outright. Every classification, successful or not, counts against a session limit shown just above the button, there to cap how many paid API calls one sitting can rack up; it resets if you restart the app.

**Register** is the running log, every use case you've added, by hand or through Auto-classify, in one table, downloadable as a CSV. It starts pre-loaded with six synthetic example use cases inspired by the thesis's Table 4 (their category values are illustrations, not findings from the thesis), so there's always something to look at even before you add your own.

**Add manually** is the same risk and control analysis, but you build the use case yourself from dropdowns instead of typing a description, useful for testing a specific combination directly, or if you don't want to use an API key at all for that part.

**Classifier accuracy** explains, and points you to, the evaluation script. It doesn't run anything itself, the actual numbers only exist once you run `python eval/run_eval.py` yourself.

**The framework** is pure reference, the thesis's own tables (the four forms of use, the five dimensions, the full risk-to-control comparison) laid out so you can look something up without re-opening the thesis PDF.

## Why this design

The risk-to-action logic in `mapper.py` is a simplified, rule-based heuristic, not a formal risk engine, deliberately mirroring the thesis's own disclaimer that it identifies circumstances in which risk mechanisms may arise rather than assigning formal risk ratings (Section 1.2). The thresholds follow the proportionality logic set out in Section 5.2: individual assessment matters more when the tool can reach confidential information, when the output is customer-facing or supports regulated work, when generated code enters an internal system, or when the employee cannot evaluate the output independently.

The classifier is intentionally conservative: when a description doesn't make a dimension clear, the prompt tells it to pick the higher-risk plausible value rather than guess low, since under-classifying is worse than over-classifying.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # pick LLM_PROVIDER and add that provider's API key
export $(cat .env | xargs)
streamlit run app.py
```

The Register, Add manually and The framework tabs work without an API key. Auto-classify and the evaluation script need one.

### Choosing a model provider

The classifier isn't tied to one vendor. `providers.py` supports four, selected by `LLM_PROVIDER` in `.env` (default `anthropic`):

| `LLM_PROVIDER` | Model used (default) | Key variable | Get a key |
|---|---|---|---|
| `anthropic` | `claude-haiku-4-5` | `ANTHROPIC_API_KEY` | console.anthropic.com/settings/keys |
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` | platform.openai.com/api-keys |
| `grok` | `grok-2-latest` | `XAI_API_KEY` | console.x.ai |
| `gemini` | `gemini-2.0-flash` | `GEMINI_API_KEY` | aistudio.google.com/apikey |

Set `LLM_MODEL` in `.env` to override the default model for whichever provider you picked, without touching code. OpenAI, Grok and Gemini all go through the `openai` Python package (Grok and Gemini each publish an OpenAI-compatible endpoint, so `providers.py` just points the same client at a different `base_url`); Anthropic goes through its own SDK. The Auto-classify tab shows which provider and model are active.

## Evaluating the classifier

```bash
python eval/run_eval.py
```

This runs the classifier against the 16 cases in `eval/cases.py` and writes a full per-dimension accuracy report to `eval/results.md`. None of the test cases describe a real bank or real client data, they were written for this project to test whether the classifier recovers the same dimension values a human reviewer would assign from a plain description.

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest tests/
```

`tests/test_mapper.py` and `tests/test_classifier.py` cover the deterministic logic (risk mapping, JSON extraction, validation) without calling any real provider; `tests/test_providers.py` covers provider selection and the retry-on-transient-failure wrapper; `tests/test_hook.py` covers the optional prompt-event hook described below. These run in CI on every push (`.github/workflows/tests.yml`), along with `python scripts/check_package.py`, which fails if the tracked tree contains an environment file, a raw log, a database, a patch or a bundle.

## Optional prompt-event hook

`claude-plugin/genai-usage-logger` is a small, opt-in Claude Code plugin. It no longer reads or classifies prompts. For each submitted prompt it records only a timestamp, the event type, a random event id and the prompt's character count, in a local SQLite file. It keeps no prompt text, no content hash, no session id, no transcript path and no working directory, and it makes no model call. A prompt event is not a complete business use case, and a count of events is not evidence that anything was reviewed.

It does nothing unless you turn it on in the shell that starts the coding tool:

```bash
export GENAI_LOG_METADATA=1
export GENAI_EVENT_DB="$HOME/.local/share/genai-governance/events.sqlite"
```

The path must be absolute. At most 1,000 events are kept, and events older than seven days are removed on the next write.

The earlier version of this plugin appended every raw prompt to `data/auto_log.jsonl` and classified it in the background. That created a second store of potentially confidential text and a second path to a model provider, so it has been removed. Updating this repository does not unload an already installed copy of the old plugin: disable it in your plugin manager before using the replacement. Existing `data/auto_log.jsonl` files are not imported or deleted, and the Register tab no longer reads them; review and remove them yourself if you no longer need them.

## Security notes

This is a local script, not a hosted web app, so most of a typical web security checklist (authentication, user roles, database hardening, CORS) doesn't apply, there's no server, no accounts and no database. What does apply, and what this project actually does:

- The API key is only ever read from an environment variable (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY` or `GEMINI_API_KEY`, depending on `LLM_PROVIDER`), never hardcoded. `.env` is in `.gitignore` and was never committed; checked against the full git history, not just the latest commit.
- The classifier's output is validated against a fixed allow-list of values before it's used for anything (`classifier._validate`). A free-text description that tried to manipulate the model into returning an arbitrary classification would just fail validation, not get accepted.
- Free-text input is capped at 1,500 characters, both in the UI and server-side, to bound API cost per request.
- Classifications are capped per session (30 by default) as a simple guard against runaway API spend if this is ever deployed somewhere other than your own machine.
- Streamlit escapes rendered text by default; nothing in this app uses `unsafe_allow_html`, `eval`, `exec` or `pickle`.
- The optional prompt-event hook stores no prompt content (see above), and it is off unless you opt in.

If you ever do deploy this somewhere public (Streamlit Community Cloud, for instance), the one thing worth adding before you do is a real rate limit tied to IP or an auth layer, not just the per-session counter above, since a new session resets it.

## Project structure

```
data/framework.py    the four forms of use, five dimensions and risk-to-control table, as data
mapper.py             rule-based mapping from a use case's dimensions to risk areas and an action
classifier.py          LLM-based classification of a free-text description into the five dimensions
providers.py           picks and calls the model provider (Anthropic, OpenAI, Grok, Gemini) behind classifier.py
eval/cases.py         16 hand-labeled synthetic use cases
eval/run_eval.py      runs the classifier against eval/cases.py and reports accuracy
app.py                 the Streamlit app
claude-plugin/         optional metadata-only prompt-event hook
tests/                 pytest suite for mapper.py, classifier.py and providers.py (no real API calls)
scripts/check_package.py       fails if runtime or private files are tracked, or attribution settings change
```

## A note on how this was built

I built this with the help of generative AI, which helped turn the thesis's tables into structured data and app logic, and helped build the classifier and evaluation harness. The framework, the thesis it's drawn from, the project direction and the evaluation design are my own.
