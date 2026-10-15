"""
GenAI Use-Case Register for Banks
----------------------------------
A working prototype of the "use-case register" proposed in Section 5.2 of
the thesis this project is based on, extended with an automatic classifier
(classifier.py) that reads a plain-language description of what an
employee did and infers the five comparison dimensions itself, the same way
a real usage log behind an LLM gateway would need to. Every entry, manual
or automatic, is run through the same risk-to-control mapping drawn from
the thesis's Chapter 5. The classifier is not tied to one model vendor;
providers.py dispatches the actual API call to Anthropic, OpenAI, xAI
(Grok) or Google (Gemini) depending on the LLM_PROVIDER setting in .env.

Run locally with: streamlit run app.py
"""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from data.framework import DIMENSIONS, FORMS_OF_USE, ILLUSTRATIVE_USE_CASES, RISK_AREAS
from mapper import flagged_risk_ids, recommended_action, risk_areas_by_id
from classifier import classify_use_case, ClassificationError, MAX_DESCRIPTION_CHARS
from providers import PROVIDERS, current_provider_id, current_model, ProviderError

MAX_CLASSIFICATIONS_PER_SESSION = 30

st.set_page_config(page_title="GenAI Use-Case Register", layout="wide")

RISK_BY_ID = risk_areas_by_id()
FORM_BY_ID = {f["id"]: f for f in FORMS_OF_USE}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# st.session_state persists for one browser tab's session, not across restarts
# or between different users, so the register and the classification count
# below both reset whenever the app process restarts. That's fine for a demo;
# a real deployment would need to persist the register somewhere durable.
if "register" not in st.session_state:
    st.session_state.register = [
        {**dict(uc), "source": "synthetic example (inspired by Table 4)", "logged_at": "—"}
        for uc in ILLUSTRATIVE_USE_CASES
    ]


def render_risk_panel(use_case: dict):
    """Shared by the Auto-classify and Add manually tabs: both end up with a
    dict of the same five dimension values, just from a different source
    (the LLM vs. the radio buttons), so both can reuse this exact same
    risk-area and action rendering."""
    flagged = flagged_risk_ids(use_case)
    action = recommended_action(use_case)

    # Streamlit's markdown color syntax, :color[text], just styles the badge;
    # the actual logic deciding Logged/Flagged/Block lives in mapper.py.
    action_color = {"Logged": "green", "Flagged for review": "orange", "Block recommended": "red"}[action]
    st.markdown(f"**Action:** :{action_color}[{action}]")

    if not flagged:
        st.info(
            "No risk area from the thesis's framework is flagged for this "
            "combination. That does not mean the use case is risk-free, only "
            "that it does not trip the illustrative thresholds this prototype "
            "checks."
        )
        return

    for rid in flagged:
        risk = RISK_BY_ID[rid]
        with st.expander(risk["name"], expanded=True):
            st.markdown(f"**Mechanism.** {risk['mechanism']}")
            st.markdown(f"**Control objective.** {risk['control_objective']}")
            st.markdown("**Illustrative controls.**")
            for c in risk["illustrative_controls"]:
                st.markdown(f"- {c}")
            st.markdown(f"**Main responsible parties.** {risk['responsible_parties']}")
            st.markdown(f"**Remaining limitation.** {risk['remaining_limitation']}")


st.title("GenAI Use-Case Register for Banks")
st.caption(
    "Built on the use-case register proposed in Section 5.2 of "
    "“The Use of Generative Artificial Intelligence in Banks: Governance, "
    "Risks, and Internal Controls,” a Bachelor's thesis at Bocconi University, "
    "with an automatic classifier added on top of the thesis's own framework."
)

tab_auto, tab_register, tab_manual, tab_eval, tab_framework = st.tabs(
    ["Auto-classify", "Register", "Add manually", "Classifier accuracy", "The framework"]
)

with tab_auto:
    st.subheader("Describe what you did, in your own words")
    st.write(
        "This is the part of the project that goes beyond the thesis: instead "
        "of picking the five dimensions from a form, you describe the activity "
        "the way an employee actually would, and an LLM classifies it against "
        "the thesis's own framework, logs it, and flags it if it crosses a "
        "risk threshold. The same way an LLM gateway in front of a bank's "
        "approved AI tools would need to."
    )

    description = st.text_area(
        "What did you do?",
        placeholder=(
            "e.g. \"I pasted a client's loan file into ChatGPT's public website "
            "and asked it to recommend whether to approve the loan.\""
        ),
        height=100,
        max_chars=MAX_DESCRIPTION_CHARS,
    )

    try:
        _provider_id = current_provider_id()
        st.caption(
            f"Using **{PROVIDERS[_provider_id]['label']}** "
            f"(model `{current_model(_provider_id)}`), set via `LLM_PROVIDER` "
            "in `.env`. Other supported providers: "
            + ", ".join(p["label"] for pid, p in PROVIDERS.items() if pid != _provider_id)
            + "."
        )
    except ProviderError as e:
        st.caption(f"⚠️ {e}")

    if "classification_count" not in st.session_state:
        st.session_state.classification_count = 0
    budget_left = MAX_CLASSIFICATIONS_PER_SESSION - st.session_state.classification_count
    st.caption(
        f"{budget_left} of {MAX_CLASSIFICATIONS_PER_SESSION} classifications left this "
        "session. A simple cap so one session can't run up an unbounded API bill, "
        "relevant if this ever runs somewhere other than your own machine."
    )

    classify_clicked = st.button(
        "Classify and log",
        type="primary",
        disabled=not description or budget_left <= 0,
    )
    if budget_left <= 0:
        st.warning("Session classification limit reached. Restart the app to reset it.")

    if classify_clicked:
        # Counted even if the call below fails, intentionally: the API call
        # already happened and was already billed, so the budget should
        # reflect attempts, not just successes.
        st.session_state.classification_count += 1
        with st.spinner("Classifying..."):
            try:
                pred = classify_use_case(description)
            except ClassificationError as e:
                st.error(str(e))
                pred = None

        if pred:
            st.success("Classified and logged.")
            # One metric tile per dimension, in the same order classifier.py
            # asks the model for them.
            cols = st.columns(5)
            labels = {
                "tool_access": "Tool and access",
                "information_involved": "Information involved",
                "role_of_output": "Role of output",
                "banking_process": "Banking process",
                "task_expertise": "Task and expertise",
            }
            for col, (key, label) in zip(cols, labels.items()):
                with col:
                    st.metric(label, pred[key])
            st.caption(f"Model's rationale: {pred.get('rationale', '—')}")

            st.divider()
            render_risk_panel(pred)

            entry = {
                "name": description[:80],
                "form": pred["form"],
                "tool_access": pred["tool_access"],
                "information_involved": pred["information_involved"],
                "role_of_output": pred["role_of_output"],
                "banking_process": pred["banking_process"],
                "task_expertise": pred["task_expertise"],
                "source": "auto-classified",
                "logged_at": now(),
            }
            st.session_state.register.append(entry)

with tab_register:
    st.subheader("Use-case register")
    st.write(
        "Every entry, however it was logged, is scored against the same five "
        "dimensions and the same risk-to-control table. The first six rows are "
        "synthetic examples inspired by the thesis's Table 4, not findings."
    )

    # Re-run the mapper over every entry on each page load, rather than
    # storing the flagged risks and action at the time an entry was added.
    # That way an edit to mapper.py's rules is reflected immediately for
    # every past entry too, not just new ones.
    rows = []
    for entry in st.session_state.register:
        flagged = flagged_risk_ids(entry)
        rows.append(
            {
                "Logged at": entry.get("logged_at", "—"),
                "Source": entry.get("source", "manual"),
                "Use case": entry["name"],
                "Form of use": FORM_BY_ID[entry["form"]]["name"],
                "Action": recommended_action(entry),
                "Risk areas flagged": ", ".join(RISK_BY_ID[r]["name"] for r in flagged) or "None",
                "Tool and access": entry["tool_access"],
                "Information involved": entry["information_involved"],
                "Role of output": entry["role_of_output"],
                "Banking process": entry["banking_process"],
                "Task and expertise": entry["task_expertise"],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    st.download_button("Download register as CSV", csv, "use_case_register.csv", "text/csv")

with tab_manual:
    st.subheader("Describe a new use case by picking its characteristics")
    st.write(
        "The original, form-based way to add a use case: pick the form of "
        "use and a value for each dimension directly, rather than letting "
        "the classifier infer them from free text."
    )

    name = st.text_input(
        "Short name for this use case",
        placeholder="e.g. Summarizing a loan file for a relationship manager",
    )

    form_options = {f["name"]: f["id"] for f in FORMS_OF_USE}
    form_name = st.selectbox("Form of use", list(form_options.keys()))
    form_id = form_options[form_name]
    st.caption(FORM_BY_ID[form_id]["description"])

    answers = {}
    cols = st.columns(len(DIMENSIONS))
    for col, dim in zip(cols, DIMENSIONS):
        with col:
            answers[dim["id"]] = st.radio(
                dim["name"], dim["options"], help=dim["question"], key=f"dim_{dim['id']}"
            )

    st.divider()
    st.subheader("Risk areas and controls that apply")
    render_risk_panel(answers)

    if st.button("Add this use case to the register", type="primary", disabled=not name):
        entry = {"name": name, "form": form_id, **answers, "source": "manual", "logged_at": now()}
        st.session_state.register.append(entry)
        st.success(f"Added “{name}” to the register.")

with tab_eval:
    st.subheader("How accurate is the classifier?")
    st.write(
        "The thesis explicitly does not validate its framework against data "
        "(Section 2.5, Section 6). This is a small attempt to do exactly "
        "that: eval/cases.py holds 16 hand-labeled, synthetic use-case "
        "descriptions, and eval/run_eval.py runs the classifier against them "
        "and reports per-dimension accuracy."
    )
    st.code("python eval/run_eval.py", language="bash")
    st.write(
        "It needs a key for whichever provider `LLM_PROVIDER` selects in your "
        ".env (see .env.example) and writes a full report to eval/results.md. "
        "Run it locally and the report there is the real result, this tab "
        "doesn't fabricate one."
    )

with tab_framework:
    st.subheader("Four forms of employee generative AI use")
    st.table(
        pd.DataFrame(
            [
                {
                    "Form": f["name"],
                    "Description": f["description"],
                    "Illustrative examples": "; ".join(f["examples"]),
                }
                for f in FORMS_OF_USE
            ]
        )
    )

    st.subheader("Five dimensions for comparing use cases")
    st.table(
        pd.DataFrame(
            [
                {
                    "Dimension": d["name"],
                    "Question": d["question"],
                    "Illustrative variations": "; ".join(d["options"]),
                }
                for d in DIMENSIONS
            ]
        )
    )

    st.subheader("Full risk-to-control table")
    st.table(
        pd.DataFrame(
            [
                {
                    "Risk area": r["name"],
                    "Mechanism": r["mechanism"],
                    "Control objective": r["control_objective"],
                    "Illustrative controls": "; ".join(r["illustrative_controls"]),
                    "Main responsible parties": r["responsible_parties"],
                }
                for r in RISK_AREAS
            ]
        )
    )

st.divider()
st.caption(
    "Built on the framework developed in Delegeanu, D. (2026), “The Use of "
    "Generative Artificial Intelligence in Banks: Governance, Risks, and "
    "Internal Controls,” Bachelor's thesis, Bocconi University. This tool is "
    "an illustrative demonstration, not a validated risk-management product, "
    "and it does not assign formal risk ratings."
)
