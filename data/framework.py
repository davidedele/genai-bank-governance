"""
Structured representation of the governance framework developed in:

Delegeanu, D. (2026). "The Use of Generative Artificial Intelligence in Banks:
Governance, Risks, and Internal Controls." Bachelor's thesis, Bocconi University.

This module encodes, as data, the four forms of employee generative AI use
(Table 2), the five dimensions for comparing use cases (Table 3), the
illustrative risk-mechanism examples (Table 4), and the integrated
risk-to-control comparison (Table 5) developed in the thesis. It is the
single source of truth the app is built on top of, so updating the thesis's
framing only requires editing this file.
"""

FORMS_OF_USE = [
    {
        "id": "communication",
        "name": "Communication and content creation",
        "description": "Drafting or revising material for colleagues, customers or other recipients.",
        "examples": [
            "Legal, marketing and customer-service drafting",
            "Email drafting",
        ],
    },
    {
        "id": "document_processing",
        "name": "Document and knowledge processing",
        "description": "Summarizing, extracting or retrieving information from existing material.",
        "examples": [
            "Document summarization and retrieval",
            "Regulatory research",
        ],
    },
    {
        "id": "analytical",
        "name": "Analytical and decision-support activities",
        "description": "Interpreting information or supporting an assessment or recommendation.",
        "examples": [
            "Risk-assessment and advisory insights",
            "Financing-approval and fraud-investigation support",
        ],
    },
    {
        "id": "technical",
        "name": "Technical assistance",
        "description": "Developing, modifying or maintaining internal software and systems.",
        "examples": [
            "Coding and programming support",
            "AI coding assistants",
        ],
    },
]

DIMENSIONS = [
    {
        "id": "tool_access",
        "name": "Tool and access arrangement",
        "question": "Which generative AI tool is used, and how does the employee access it?",
        "options": [
            "Public service, not approved for this task",
            "Public service, approved for this task",
            "Enterprise tool",
            "Internal application connected to bank systems",
        ],
    },
    {
        "id": "information_involved",
        "name": "Information involved",
        "question": "What information is entered, retrieved or made accessible to the tool?",
        "options": [
            "Public information",
            "Internal, non-sensitive information",
            "Confidential or proprietary information",
            "Personal or client data",
        ],
    },
    {
        "id": "role_of_output",
        "name": "Role of the output",
        "question": "How is the generated output used in the employee's work?",
        "options": [
            "Initial draft, reviewed and revised by the employee",
            "Recommendation used to support a decision",
            "Content used with limited or no review",
            "Generated code deployed to an internal system",
        ],
    },
    {
        "id": "banking_process",
        "name": "Banking process supported",
        "question": "In which banking process is the activity performed?",
        "options": [
            "Internal administrative process",
            "Process involving customers",
            "Process involving compliance or regulation",
        ],
    },
    {
        "id": "task_expertise",
        "name": "Task and employee expertise",
        "question": "What is the nature of the task, and can the employee independently evaluate the output?",
        "options": [
            "Routine, within the employee's expertise",
            "Non-routine or specialist, within expertise",
            "Outside the employee's expertise",
        ],
    },
]

# Table 5: Integrated comparison of employee generative AI risks and controls
RISK_AREAS = [
    {
        "id": "confidentiality",
        "name": "Confidentiality",
        "mechanism": "Proprietary, confidential or client information is disclosed to an unauthorized party.",
        "relevant_dimensions": ["information_involved", "tool_access"],
        "control_objective": "Prevent unauthorized disclosure and limit access to the information required for the activity.",
        "illustrative_controls": [
            "Data classification",
            "Prompt and upload restrictions",
            "Least-privilege access",
            "Data-loss prevention",
            "Access monitoring",
        ],
        "responsible_parties": "Employee and manager; business owner, information security, IT and risk management.",
        "remaining_limitation": "Sensitive information may not always be detected, and authorized access can still be excessive.",
    },
    {
        "id": "privacy",
        "name": "Privacy and data protection",
        "mechanism": "Personal data are processed, retained or reused in ways that are incompatible with the purpose for which they were collected or otherwise inconsistent with applicable requirements.",
        "relevant_dimensions": ["information_involved", "tool_access", "banking_process"],
        "control_objective": "Keep the processing of personal data within the assessed purpose and applicable data-protection requirements.",
        "illustrative_controls": [
            "Approved-purpose restrictions",
            "Retention and deletion rules",
            "Restrictions on provider reuse",
            "Data protection impact assessment where the legal threshold is met",
        ],
        "responsible_parties": "Business owner; data protection, compliance, IT and risk management.",
        "remaining_limitation": "The bank may have incomplete visibility over provider processing or later changes in how the information is used.",
    },
    {
        "id": "infosec_third_party",
        "name": "Information security and third-party dependency",
        "mechanism": "Hosting, connected data, prompt injection or third-party providers create information-security and dependency risks.",
        "relevant_dimensions": ["tool_access", "information_involved"],
        "control_objective": "Control connected access, external processing and security weaknesses.",
        "illustrative_controls": [
            "Security testing",
            "Connector boundaries",
            "Access logs",
            "Due diligence",
            "Contractual safeguards",
            "Incident notification and provider monitoring",
        ],
        "responsible_parties": "IT and information security; procurement, legal, risk management and business owner.",
        "remaining_limitation": "The bank may have limited visibility into provider practices and remain dependent on external or concentrated services.",
    },
    {
        "id": "output_reliability",
        "name": "Output reliability and bias",
        "mechanism": "An incorrect, incomplete, inconsistent or biased output influences customer-facing, regulated or important work.",
        "relevant_dimensions": ["role_of_output", "banking_process", "task_expertise"],
        "control_objective": "Identify unreliable or biased outputs before they affect the work.",
        "illustrative_controls": [
            "Source verification",
            "Task-specific and consistency testing",
            "Review of errors affecting groups",
            "Independent review and escalation thresholds",
        ],
        "responsible_parties": "Employee and manager; relevant subject-matter or control function.",
        "remaining_limitation": "Testing cannot cover every case, and convincing errors or bias may remain difficult to detect.",
    },
    {
        "id": "human_review",
        "name": "Human review and reliance",
        "mechanism": "The employee cannot adequately verify the output or relies on it without meaningful review.",
        "relevant_dimensions": ["task_expertise", "role_of_output", "banking_process"],
        "control_objective": "Ensure that review is performed by a person with the evidence, competence, time and authority to challenge the output.",
        "illustrative_controls": [
            "Access to original sources",
            "Defined review steps",
            "Role-specific training",
            "Suitable subject-matter expertise",
            "Rejection and escalation rules",
            "Evidence that review occurred",
        ],
        "responsible_parties": "Employee and manager; relevant subject-matter or control function.",
        "remaining_limitation": "Formal sign-off may become routine, while workload pressure or limited expertise can still lead to shortcuts.",
    },
    {
        "id": "generated_code",
        "name": "Generated code",
        "mechanism": "Generated code enters an internal system with an undetected error.",
        "relevant_dimensions": ["role_of_output", "banking_process", "task_expertise"],
        "control_objective": "Prevent untested or unauthorized code from affecting an internal system.",
        "illustrative_controls": [
            "Peer review",
            "Functional and security testing",
            "Security scanning",
            "Change approval and deployment controls",
        ],
        "responsible_parties": "Developer and manager; system owner, IT risk and information security.",
        "remaining_limitation": "Testing cannot identify every defect, and common tools may create similar weaknesses across institutions.",
    },
    {
        "id": "shadow_ai",
        "name": "Shadow AI and organizational visibility",
        "mechanism": "The bank does not know that generative AI is being used, or an approved tool is used for an unapproved purpose.",
        "relevant_dimensions": ["tool_access", "information_involved", "banking_process"],
        "control_objective": "Make significant uses visible and keep approval aligned with actual practice.",
        "illustrative_controls": [
            "Acceptable-use rules",
            "Approved-tool list",
            "Use-case register",
            "Approval and escalation thresholds",
            "Good-faith reporting",
            "Usage logs and proportionate monitoring",
        ],
        "responsible_parties": "Employee and manager; risk, compliance, IT and information security.",
        "remaining_limitation": "Employees may conceal use, and practices may develop faster than policies and controls.",
    },
    {
        "id": "traceability",
        "name": "Traceability",
        "mechanism": "The bank cannot reconstruct how generative AI contributed materially to a document, assessment or action.",
        "relevant_dimensions": ["role_of_output", "tool_access", "banking_process"],
        "control_objective": "Preserve proportionate evidence of material AI use and the review performed.",
        "illustrative_controls": [
            "AI-use disclosure",
            "Records of purpose, sources, outputs and important revisions",
            "System logs",
            "Review records and incident records",
        ],
        "responsible_parties": "Employee and manager; business or system owner; relevant second-line functions. Internal audit provides independent assurance.",
        "remaining_limitation": "Records may be incomplete, and logs do not show whether the employee understood or adequately checked the output.",
    },
    {
        "id": "accountability",
        "name": "Accountability",
        "mechanism": "Responsibility for reviewing the AI contribution or explaining the final action is unclear.",
        "relevant_dimensions": ["role_of_output", "banking_process", "task_expertise"],
        "control_objective": "Assign effective responsibility for use, review, escalation and oversight.",
        "illustrative_controls": [
            "Assigned use-case ownership",
            "Defined review responsibilities",
            "Escalation procedures",
            "Three Lines Model oversight and senior-management reporting",
        ],
        "responsible_parties": "First-line owner and managers; second-line oversight functions; internal audit for independent assurance; senior management for design and operation; board for oversight.",
        "remaining_limitation": "Formal assignment does not prove that meaningful review occurred, and dispersed use may still blur ownership.",
    },
]

# Synthetic software examples inspired by Table 4; populated category values are not verbatim thesis findings.
ILLUSTRATIVE_USE_CASES = [
    {
        "name": "Entering confidential or proprietary information into a public tool",
        "form": "document_processing",
        "tool_access": "Public service, not approved for this task",
        "information_involved": "Confidential or proprietary information",
        "role_of_output": "Initial draft, reviewed and revised by the employee",
        "banking_process": "Internal administrative process",
        "task_expertise": "Routine, within the employee's expertise",
    },
    {
        "name": "Using AI output for an assessment the employee cannot independently evaluate",
        "form": "analytical",
        "tool_access": "Enterprise tool",
        "information_involved": "Internal, non-sensitive information",
        "role_of_output": "Recommendation used to support a decision",
        "banking_process": "Process involving compliance or regulation",
        "task_expertise": "Outside the employee's expertise",
    },
    {
        "name": "Relying on generative AI for document tasks under high digital job demands",
        "form": "document_processing",
        "tool_access": "Enterprise tool",
        "information_involved": "Internal, non-sensitive information",
        "role_of_output": "Content used with limited or no review",
        "banking_process": "Internal administrative process",
        "task_expertise": "Routine, within the employee's expertise",
    },
    {
        "name": "Generating code deployed in an important internal system",
        "form": "technical",
        "tool_access": "Enterprise tool",
        "information_involved": "Internal, non-sensitive information",
        "role_of_output": "Generated code deployed to an internal system",
        "banking_process": "Process involving compliance or regulation",
        "task_expertise": "Non-routine or specialist, within expertise",
    },
    {
        "name": "Using an approved tool for a purpose not considered when it was approved",
        "form": "analytical",
        "tool_access": "Enterprise tool",
        "approval_status": "Not approved for this use",
        "information_involved": "Personal or client data",
        "role_of_output": "Recommendation used to support a decision",
        "banking_process": "Process involving customers",
        "task_expertise": "Non-routine or specialist, within expertise",
    },
    {
        "name": "Combining AI output with other sources without disclosing the contribution",
        "form": "communication",
        "tool_access": "Internal application connected to bank systems",
        "information_involved": "Confidential or proprietary information",
        "role_of_output": "Content used with limited or no review",
        "banking_process": "Process involving customers",
        "task_expertise": "Routine, within the employee's expertise",
    },
]
