"""
Rule-based mapping from a use case's five dimension values to the relevant
risk areas in data/framework.py.

This operationalizes the proportionate, risk-based logic the thesis itself
describes in Section 5.2: an individual assessment becomes more relevant
when the tool can reach confidential information, when the output is
customer-facing or supports regulated work, when generated code enters an
internal system, or when the employee cannot independently evaluate the
result. It is a simplified, illustrative heuristic, not a formal risk
rating, consistent with the thesis's own disclaimer that it does not assign
risk ratings to individual use cases (Section 1.2).
"""

from data.framework import RISK_AREAS

SENSITIVE_INFO = {"Confidential or proprietary information", "Personal or client data"}
EXTERNAL_TOOL = {
    "Public service, not approved for this task",
    "Public service, approved for this task",
    "Enterprise tool",
}
UNAPPROVED_TOOL = {"Public service, not approved for this task"}
HEAVY_RELIANCE_OUTPUT = {
    "Recommendation used to support a decision",
    "Content used with limited or no review",
}
REGULATED_PROCESS = {"Process involving customers", "Process involving compliance or regulation"}
LOW_EXPERTISE = {"Outside the employee's expertise"}


def flagged_risk_ids(use_case: dict) -> list[str]:
    """Given a dict with tool_access, information_involved, role_of_output,
    banking_process and task_expertise keys, return the ids of the risk
    areas that apply."""
    flags = set()

    info = use_case["information_involved"]
    tool = use_case["tool_access"]
    role = use_case["role_of_output"]
    process = use_case["banking_process"]
    expertise = use_case["task_expertise"]

    if info in SENSITIVE_INFO:
        flags.add("confidentiality")
    if info == "Personal or client data":
        flags.add("privacy")
    if tool in EXTERNAL_TOOL:
        flags.add("infosec_third_party")
    if role in HEAVY_RELIANCE_OUTPUT or expertise in LOW_EXPERTISE:
        flags.add("output_reliability")
        flags.add("human_review")
    if role == "Generated code deployed to an internal system":
        flags.add("generated_code")
    if tool in UNAPPROVED_TOOL:
        flags.add("shadow_ai")

    # "Significant" uses, per the thesis's own proportionality test in 5.2:
    # the tool reaches confidential information, the output is customer-facing
    # or supports regulated work, generated code enters a system, or the
    # employee cannot evaluate the output independently.
    significant = (
        info in SENSITIVE_INFO
        or process in REGULATED_PROCESS
        or role in HEAVY_RELIANCE_OUTPUT
        or role == "Generated code deployed to an internal system"
        or expertise in LOW_EXPERTISE
    )
    if significant:
        flags.add("traceability")
        flags.add("accountability")

    # keep RISK_AREAS order rather than set order
    ordered_ids = [r["id"] for r in RISK_AREAS]
    return [rid for rid in ordered_ids if rid in flags]


def risk_areas_by_id() -> dict:
    return {r["id"]: r for r in RISK_AREAS}
