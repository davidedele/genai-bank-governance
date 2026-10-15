# GenAI Use-Case Register for Banks

Built on my Bachelor's thesis at Bocconi University:

> Delegeanu, D. (2026). *The Use of Generative Artificial Intelligence in Banks: Governance, Risks, and Internal Controls.* Bachelor's thesis, Bocconi University.

The thesis argues that employee generative AI use in banks cannot be governed by looking at the tool alone. It develops a framework built around four recurring **forms of use**, five **dimensions** for comparing individual use cases, and an integrated table connecting the resulting risk mechanisms to control objectives, illustrative controls and responsible parties, organized around the Three Lines Model. It also explicitly says what it doesn't do: it identifies circumstances in which risk mechanisms may arise, but it does not test the framework against data (Sections 2.5 and 6).

This project does two things the thesis itself doesn't. It turns the framework into a working **use-case register**, the control the thesis proposes in Section 5.2 but only describes on paper. And it adds an **automatic classifier** on top of that register: instead of filling in a form, you describe what you did in plain language, and an LLM reads the description and infers the five dimensions itself, the way a real usage log sitting behind an enterprise AI gateway would need to work. A small labeled evaluation set then tests how well that classification actually holds up, which is a first, modest answer to the thesis's own open question about validating the framework against data.

## What it does

- **Auto-classify.** Describe a use case in your own words (e.g. "I pasted a client's loan file into ChatGPT's public website and asked it to recommend whether to approve the loan"). An LLM classifies it against the thesis's five dimensions, the app maps that to the relevant risk areas and a recommended action (Logged, Flagged for review, or Block recommended), and logs the entry automatically with a timestamp.
- **Register.** A running log of every use case, manual or auto-classified, pre-loaded with the six illustrative examples from the thesis (Table 4). Exportable as CSV.
- **Add manually.** The original form-based entry: pick the form of use and a value for each dimension directly.
- **Classifier accuracy.** Points at `eval/`, where the classifier is tested against 16 hand-written, synthetic, labeled use cases, with per-dimension accuracy reported.
- **The framework.** The underlying tables from the thesis (four forms of use, five dimensions, the full nine-area risk-to-control comparison) laid out for reference.

## Why this design

The risk-to-action logic in `mapper.py` is a simplified, rule-based heuristic, not a formal risk engine, deliberately mirroring the thesis's own disclaimer that it identifies circumstances in which risk mechanisms may arise rather than assigning formal risk ratings (Section 1.2). The thresholds follow the proportionality logic set out in Section 5.2: individual assessment matters more when the tool can reach confidential information, when the output is customer-facing or supports regulated work, when generated code enters an internal system, or when the employee cannot evaluate the output independently.

The classifier is intentionally conservative: when a description doesn't make a dimension clear, the prompt tells it to pick the higher-risk plausible value rather than guess low, since under-classifying is worse than over-classifying.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # add your own ANTHROPIC_API_KEY
export $(cat .env | xargs)
streamlit run app.py
```

The Register, Add manually and The framework tabs work without an API key. Auto-classify and the evaluation script need one.

## Evaluating the classifier

```bash
python eval/run_eval.py
```

This runs the classifier against the 16 cases in `eval/cases.py` and writes a full per-dimension accuracy report to `eval/results.md`. None of the test cases describe a real bank or real client data, they were written for this project to test whether the classifier recovers the same dimension values a human reviewer would assign from a plain description.

## Project structure

```
data/framework.py    the four forms of use, five dimensions and risk-to-control table, as data
mapper.py             rule-based mapping from a use case's dimensions to risk areas and an action
classifier.py          LLM-based classification of a free-text description into the five dimensions
eval/cases.py         16 hand-labeled synthetic use cases
eval/run_eval.py      runs the classifier against eval/cases.py and reports accuracy
app.py                 the Streamlit app
```

## A note on how this was built

I built this with the help of generative AI, which helped turn the thesis's tables into structured data and app logic, and helped build the classifier and evaluation harness. The framework, the thesis it's drawn from, the project direction and the evaluation design are my own.
