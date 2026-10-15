# Illustrative policy decision table

The thesis identifies risk mechanisms and controls. It does not prescribe the following automated outcomes. These are explicit software-design choices that an organization would need to review and replace with its own policy.

| Condition | Outcome | Rationale |
|---|---|---|
| Confidential/proprietary or personal/client information AND explicitly unapproved use | Do not proceed | Prevent proceeding with sensitive information outside the authorized use. |
| Explicitly unapproved use without the sensitive-data combination | Review required | A record alone must not imply permission. |
| Confidential/proprietary or personal/client information | Review required | Check purpose, access, handling and review arrangements. |
| Generated code deployed to an internal system | Review required | Require peer/security testing and change controls before reliance. |
| Task outside the employee's expertise | Review required | The reviewer may not be able to challenge the result. |
| Recommendation used in a decision, or content used with little/no review | Review required | Material reliance requires appropriate verification. |
| Customer or compliance/regulatory process | Review required | An explicit workflow sensitivity signal triggers review under this sample policy. |
| No escalation predicate, but unknown characteristic/form/approval | Clarification required | Missing facts are not evidence of permission. |
| None of the above | Standard controls | Baseline controls still apply; the tool does not grant approval. |

Known escalation takes precedence over missing data. Both the known reasons and unresolved fields are returned. The combined confidentiality/approval condition takes precedence over review conditions.

All rules contain stable IDs and reasons. The validator rejects unknown categories, invalid predicates and unconditional rules. Historical assessments retain the applied policy and its hash, so merely editing a rule does not change previously recorded outcomes.

`tests/test_mapper.py` contains scenario-specific expectations plus an exhaustive invariant check across 1,440 valid combinations. This is verification of the implemented sample policy, not evidence that the policy is complete or optimal for a bank.

### Limits of the five-dimensional simplification

The taxonomy does not represent transaction size, business criticality, legal classification, validated reviewer competence, actual tool permissions or whether a control was performed. Consequently the application is a structured intake/review prototype, not a bank-grade approval or risk-calculation engine. A generated-code result is deliberately routed for review rather than assigned a numerical severity the inputs cannot justify.
