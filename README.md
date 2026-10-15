# GenAI Use-Case Register for Banks

A working prototype of the **use-case register** proposed in Section 5.2 of my Bachelor's thesis at Bocconi University:

> Delegeanu, D. (2026). *The Use of Generative Artificial Intelligence in Banks: Governance, Risks, and Internal Controls.* Bachelor's thesis, Bocconi University.

The thesis argues that employee generative AI use in banks cannot be governed by looking at the tool alone. It develops a framework built around four recurring **forms of use**, five **dimensions** for comparing individual use cases, and an integrated table connecting the resulting risk mechanisms to control objectives, illustrative controls and responsible parties, organized around the Three Lines Model.

This project turns that framework into something you can actually use: pick a use case's characteristics, and see the risk areas and controls the thesis's own framework points to.

## What it does

- **Add a use case.** Describe an employee generative AI activity against the thesis's five dimensions (tool and access arrangement, information involved, role of the output, banking process supported, task and employee expertise). The app flags the relevant risk areas and shows, for each one, the risk mechanism, the control objective, illustrative controls, the main responsible parties and the thesis's own stated limitation of that control.
- **Register.** A running table of every use case entered, pre-loaded with the six illustrative examples from the thesis (Table 4), exportable as CSV, the same way the thesis proposes a bank would log and review significant uses.
- **The framework.** The underlying tables from the thesis (the four forms of use, the five dimensions, the full nine-area risk-to-control comparison) laid out for reference.

## Why this design

The risk flagging is a simplified, rule-based heuristic, not a formal risk engine. That's deliberate; the thesis itself is explicit that it identifies circumstances in which risk mechanisms may arise rather than assigning formal risk ratings to individual use cases (Section 1.2). The rules here follow the same proportionality logic the thesis sets out in Section 5.2: individual assessment matters more when the tool can reach confidential information, when the output is customer-facing or supports regulated work, when generated code enters an internal system, or when the employee cannot evaluate the output independently.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
data/framework.py   the four forms of use, five dimensions and risk-to-control table, as data
mapper.py            rule-based mapping from a use case's dimension values to risk areas
app.py                the Streamlit app
```

## A note on how this was built

I built this with the help of generative AI, which helped turn the thesis's tables into the structured data and app logic above. The framework, the thesis it's drawn from and the direction of the project are my own.
