"""
GenAI Use-Case Register for Banks
----------------------------------
A working prototype of the "use-case register" proposed in Section 5.2 of
the thesis this project is based on: a tool that lets a bank record an
employee generative AI use case against the five comparison dimensions
developed in the thesis (Chapter 3), and see the risk areas and controls
that apply, drawn directly from the integrated risk-to-control comparison
in Chapter 5.

Run locally with: streamlit run app.py
"""

import pandas as pd
import streamlit as st

from data.framework import DIMENSIONS, FORMS_OF_USE, ILLUSTRATIVE_USE_CASES, RISK_AREAS
from mapper import flagged_risk_ids, risk_areas_by_id

st.set_page_config(page_title="GenAI Use-Case Register", layout="wide")

RISK_BY_ID = risk_areas_by_id()
FORM_BY_ID = {f["id"]: f for f in FORMS_OF_USE}

if "register" not in st.session_state:
    st.session_state.register = [dict(uc) for uc in ILLUSTRATIVE_USE_CASES]

st.title("GenAI Use-Case Register for Banks")
st.caption(
    "A working prototype of the use-case register proposed in Section 5.2 of "
    "“The Use of Generative Artificial Intelligence in Banks: Governance, "
    "Risks, and Internal Controls,” a Bachelor's thesis at Bocconi University. "
    "Pick a use case's characteristics and see the risk areas and controls the "
    "thesis's own framework points to."
)

tab_register, tab_entry, tab_framework = st.tabs(
    ["Register", "Add a use case", "The framework"]
)

with tab_entry:
    st.subheader("Describe a new employee generative AI use case")
    st.write(
        "This mirrors the register the thesis proposes: pick the form of use and "
        "a value for each of the five comparison dimensions, and the risk areas "
        "and controls below update to match."
    )

    name = st.text_input("Short name for this use case", placeholder="e.g. Summarizing a loan file for a relationship manager")

    form_options = {f["name"]: f["id"] for f in FORMS_OF_USE}
    form_name = st.selectbox("Form of use", list(form_options.keys()))
    form_id = form_options[form_name]
    st.caption(FORM_BY_ID[form_id]["description"])

    answers = {}
    cols = st.columns(len(DIMENSIONS))
    for col, dim in zip(cols, DIMENSIONS):
        with col:
            answers[dim["id"]] = st.radio(
                dim["name"],
                dim["options"],
                help=dim["question"],
                key=f"dim_{dim['id']}",
            )

    flagged = flagged_risk_ids(answers)

    st.divider()
    st.subheader("Risk areas and controls that apply")

    if not flagged:
        st.info(
            "No risk area from the thesis's framework is flagged for this "
            "combination. That does not mean the use case is risk-free, only "
            "that it does not trip the illustrative thresholds this prototype "
            "checks."
        )
    for rid in flagged:
        risk = RISK_BY_ID[rid]
        with st.expander(f"{risk['name']}", expanded=True):
            st.markdown(f"**Mechanism.** {risk['mechanism']}")
            st.markdown(f"**Control objective.** {risk['control_objective']}")
            st.markdown("**Illustrative controls.**")
            for c in risk["illustrative_controls"]:
                st.markdown(f"- {c}")
            st.markdown(f"**Main responsible parties.** {risk['responsible_parties']}")
            st.markdown(f"**Remaining limitation.** {risk['remaining_limitation']}")

    if st.button("Add this use case to the register", type="primary", disabled=not name):
        entry = {"name": name, "form": form_id, **answers}
        st.session_state.register.append(entry)
        st.success(f"Added “{name}” to the register.")

with tab_register:
    st.subheader("Use-case register")
    st.write(
        "Every entry below is scored against the same five dimensions and "
        "mapped to the same risk-to-control table, so the register stays "
        "consistent as new use cases are added. The first six entries are the "
        "illustrative examples from the thesis itself (Table 4)."
    )

    rows = []
    for entry in st.session_state.register:
        flagged = flagged_risk_ids(entry)
        rows.append(
            {
                "Use case": entry["name"],
                "Form of use": FORM_BY_ID[entry["form"]]["name"],
                "Tool and access": entry["tool_access"],
                "Information involved": entry["information_involved"],
                "Role of output": entry["role_of_output"],
                "Banking process": entry["banking_process"],
                "Task and expertise": entry["task_expertise"],
                "Risk areas flagged": ", ".join(RISK_BY_ID[r]["name"] for r in flagged) or "None",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    st.download_button("Download register as CSV", csv, "use_case_register.csv", "text/csv")

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
    "an illustrative demonstration of the thesis's proposed use-case register, "
    "not a validated risk-management product, and it does not assign formal "
    "risk ratings."
)
