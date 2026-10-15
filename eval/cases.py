"""
A small, hand-written, synthetic set of employee generative AI use-case
descriptions, each labeled with the five dimensions a human reviewer would
assign. None of this describes a real bank, a real employee or real client
data; every case was written for this project to test whether the
classifier in classifier.py can recover the same dimension values a person
would assign from a plain-language description.

This directly addresses the one thing the thesis itself says it could not
do (Section 2.5, Section 6): test the proposed framework against data,
rather than only arguing for it analytically.
"""

CASES = [
    {
        "description": (
            "I used ChatGPT's free public website to summarize a new EU "
            "banking regulation update for my own understanding. Nothing "
            "confidential, just the public regulatory text."
        ),
        "ground_truth": {
            "form": "document_processing",
            "tool_access": "Public service, not approved for this task",
            "information_involved": "Public information",
            "role_of_output": "Initial draft, reviewed and revised by the employee",
            "banking_process": "Internal administrative process",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "I pasted a client's loan application and financial statements "
            "into the public ChatGPT website and asked it to assess their "
            "creditworthiness and recommend whether to approve the loan."
        ),
        "ground_truth": {
            "form": "analytical",
            "tool_access": "Public service, not approved for this task",
            "information_involved": "Personal or client data",
            "role_of_output": "Recommendation used to support a decision",
            "banking_process": "Process involving customers",
            "task_expertise": "Non-routine or specialist, within expertise",
        },
    },
    {
        "description": (
            "Our enterprise Copilot summarized a long internal meeting "
            "transcript into bullet points for our team wiki. Nothing "
            "about customers was discussed."
        ),
        "ground_truth": {
            "form": "document_processing",
            "tool_access": "Enterprise tool",
            "information_involved": "Internal, non-sensitive information",
            "role_of_output": "Initial draft, reviewed and revised by the employee",
            "banking_process": "Internal administrative process",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "I asked the enterprise AI assistant to draft a response to a "
            "customer complaint about a mischarged fee on their account. "
            "I reviewed and edited the draft before sending it."
        ),
        "ground_truth": {
            "form": "communication",
            "tool_access": "Enterprise tool",
            "information_involved": "Personal or client data",
            "role_of_output": "Initial draft, reviewed and revised by the employee",
            "banking_process": "Process involving customers",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "I used our internal AI coding assistant, connected to the dev "
            "environment, to write a script that updates exchange rates in "
            "the core payments system. It went through standard code "
            "review before deployment."
        ),
        "ground_truth": {
            "form": "technical",
            "tool_access": "Internal application connected to bank systems",
            "information_involved": "Internal, non-sensitive information",
            "role_of_output": "Generated code deployed to an internal system",
            "banking_process": "Process involving compliance or regulation",
            "task_expertise": "Non-routine or specialist, within expertise",
        },
    },
    {
        "description": (
            "I used Gemini, which IT has approved for general non-sensitive "
            "drafting, to write a generic thank-you email template for new "
            "interns. No real names or data were involved, and I sent it "
            "as generated."
        ),
        "ground_truth": {
            "form": "communication",
            "tool_access": "Public service, approved for this task",
            "information_involved": "Public information",
            "role_of_output": "Content used with limited or no review",
            "banking_process": "Internal administrative process",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "Using the internal AI tool connected to our AML case database, "
            "I asked it to flag suspicious transaction patterns across "
            "accounts for the fraud investigation team to review."
        ),
        "ground_truth": {
            "form": "analytical",
            "tool_access": "Internal application connected to bank systems",
            "information_involved": "Personal or client data",
            "role_of_output": "Recommendation used to support a decision",
            "banking_process": "Process involving compliance or regulation",
            "task_expertise": "Non-routine or specialist, within expertise",
        },
    },
    {
        "description": (
            "I used the enterprise AI assistant to look up and summarize "
            "our internal HR leave policy for a colleague who asked. Pure "
            "internal admin question, nothing about any customer."
        ),
        "ground_truth": {
            "form": "document_processing",
            "tool_access": "Enterprise tool",
            "information_involved": "Internal, non-sensitive information",
            "role_of_output": "Initial draft, reviewed and revised by the employee",
            "banking_process": "Internal administrative process",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "A junior analyst used the public ChatGPT app, which isn't an "
            "approved bank tool, to help debug a script that pulls data "
            "for an internal reporting dashboard. It isn't deployed "
            "anywhere yet, just a draft on their own laptop that they're "
            "still reviewing."
        ),
        "ground_truth": {
            "form": "technical",
            "tool_access": "Public service, not approved for this task",
            "information_involved": "Internal, non-sensitive information",
            "role_of_output": "Initial draft, reviewed and revised by the employee",
            "banking_process": "Internal administrative process",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "I used our approved AI research tool to pull together a "
            "summary of new ECB guidance for the compliance newsletter we "
            "send to all staff. All the source material came from the "
            "ECB's public website."
        ),
        "ground_truth": {
            "form": "document_processing",
            "tool_access": "Public service, approved for this task",
            "information_involved": "Public information",
            "role_of_output": "Initial draft, reviewed and revised by the employee",
            "banking_process": "Process involving compliance or regulation",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "Without checking with anyone first, I uploaded a spreadsheet "
            "of about 200 customer account balances to a free online AI "
            "tool and asked it to find unusual patterns, because our "
            "internal tool was down that day."
        ),
        "ground_truth": {
            "form": "analytical",
            "tool_access": "Public service, not approved for this task",
            "information_involved": "Personal or client data",
            "role_of_output": "Recommendation used to support a decision",
            "banking_process": "Process involving customers",
            "task_expertise": "Non-routine or specialist, within expertise",
        },
    },
    {
        "description": (
            "I asked our enterprise AI assistant to draft talking points "
            "for a client pitch meeting. A colleague who specializes in "
            "that client's industry checked the content before the "
            "meeting."
        ),
        "ground_truth": {
            "form": "communication",
            "tool_access": "Enterprise tool",
            "information_involved": "Confidential or proprietary information",
            "role_of_output": "Initial draft, reviewed and revised by the employee",
            "banking_process": "Process involving customers",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "I used a public, unapproved AI tool to translate a public "
            "press release from Italian to English for our website. "
            "Nothing sensitive was involved."
        ),
        "ground_truth": {
            "form": "communication",
            "tool_access": "Public service, not approved for this task",
            "information_involved": "Public information",
            "role_of_output": "Initial draft, reviewed and revised by the employee",
            "banking_process": "Internal administrative process",
            "task_expertise": "Routine, within the employee's expertise",
        },
    },
    {
        "description": (
            "Using the internal AI assistant wired into our document "
            "management system, I had it generate a first draft of a "
            "credit risk memo pulling from the client's full file. I "
            "revised it myself before it went to the credit committee."
        ),
        "ground_truth": {
            "form": "analytical",
            "tool_access": "Internal application connected to bank systems",
            "information_involved": "Personal or client data",
            "role_of_output": "Recommendation used to support a decision",
            "banking_process": "Process involving compliance or regulation",
            "task_expertise": "Non-routine or specialist, within expertise",
        },
    },
    {
        "description": (
            "A new hire used ChatGPT's free public version, since they "
            "weren't yet aware of our internal AI policy, to ask for an "
            "explanation of how letters of credit work, just as general "
            "self-training."
        ),
        "ground_truth": {
            "form": "document_processing",
            "tool_access": "Public service, not approved for this task",
            "information_involved": "Public information",
            "role_of_output": "Content used with limited or no review",
            "banking_process": "Internal administrative process",
            "task_expertise": "Outside the employee's expertise",
        },
    },
    {
        "description": (
            "I used our enterprise coding assistant to refactor an "
            "internal reporting script. The change went through our "
            "standard peer review and testing process before being "
            "merged."
        ),
        "ground_truth": {
            "form": "technical",
            "tool_access": "Enterprise tool",
            "information_involved": "Internal, non-sensitive information",
            "role_of_output": "Generated code deployed to an internal system",
            "banking_process": "Internal administrative process",
            "task_expertise": "Non-routine or specialist, within expertise",
        },
    },
]
