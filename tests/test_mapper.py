"""
Regression tests for mapper.py's risk-flagging and recommended_action logic.

These are the thesis's own Table 4 illustrative scenarios (data/framework.py
ILLUSTRATIVE_USE_CASES) plus the cases from the manual testing done earlier
in development that caught and fixed the Block-recommended over-triggering
bug (recommended_action used to fire on "regulated process" alone, which
blocked things like summarizing a public press release purely because the
classifier defaults tool_access to "not approved" when a description
doesn't name a tool). Checked in here so that regression stays caught by
`pytest` rather than depending on someone re-running a one-off script.
"""

from data.framework import ILLUSTRATIVE_USE_CASES
from mapper import flagged_risk_ids, recommended_action


def test_illustrative_use_cases_all_classify_without_error():
    # Every thesis Table 4 example should run through both functions
    # cleanly; this is a smoke test that the dict shape mapper.py expects
    # matches what data/framework.py actually provides.
    for case in ILLUSTRATIVE_USE_CASES:
        recommended_action(case)
        flagged_risk_ids(case)


def test_block_requires_both_unapproved_tool_and_sensitive_info():
    # The thesis's own flagship risk scenario: confidential/client data
    # reaching a public, unapproved tool. This must still Block.
    blocked = {
        "information_involved": "Personal or client data",
        "tool_access": "Public service, not approved for this task",
        "role_of_output": "Recommendation used to support a decision",
        "banking_process": "Process involving customers",
    }
    assert recommended_action(blocked) == "Block recommended"


def test_regulated_topic_alone_does_not_block():
    # The bug: summarizing public information about a regulated topic (an
    # ECB rate decision, say) with an unapproved tool used to Block purely
    # because the process looked "regulated" by topic, not because
    # anything sensitive was actually at risk. It must now only be Flagged
    # at most, never Blocked, since information_involved isn't sensitive.
    public_summary = {
        "information_involved": "Public information",
        "tool_access": "Public service, not approved for this task",
        "role_of_output": "Content used with limited or no review",
        "banking_process": "Process involving compliance or regulation",
    }
    assert recommended_action(public_summary) != "Block recommended"


def test_sensitive_info_with_approved_tool_is_flagged_not_blocked():
    # Sensitive information alone (tool is fine) should be flagged for
    # review, not escalated all the way to Block, since Block is reserved
    # for the unapproved-tool-plus-sensitive-info combination specifically.
    case = {
        "information_involved": "Confidential or proprietary information",
        "tool_access": "Enterprise tool",
        "role_of_output": "Initial draft, reviewed and revised by the employee",
        "banking_process": "Internal administrative process",
    }
    assert recommended_action(case) == "Flagged for review"


def test_purely_internal_routine_use_is_just_logged():
    case = {
        "information_involved": "Internal, non-sensitive information",
        "tool_access": "Enterprise tool",
        "role_of_output": "Initial draft, reviewed and revised by the employee",
        "banking_process": "Internal administrative process",
    }
    assert recommended_action(case) == "Logged"


def test_flagged_risk_ids_returns_known_ids_in_framework_order():
    from data.framework import RISK_AREAS

    known_ids = {r["id"] for r in RISK_AREAS}
    case = {
        "information_involved": "Personal or client data",
        "tool_access": "Public service, not approved for this task",
        "role_of_output": "Generated code deployed to an internal system",
        "banking_process": "Process involving customers",
        "task_expertise": "Outside the employee's expertise",
    }
    ids = flagged_risk_ids(case)
    assert ids, "expected at least one risk area to be flagged"
    assert set(ids) <= known_ids
    # order must follow RISK_AREAS, not insertion/set order
    ordered_ids = [r["id"] for r in RISK_AREAS]
    assert ids == [rid for rid in ordered_ids if rid in ids]
