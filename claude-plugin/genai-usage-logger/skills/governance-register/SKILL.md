---
name: governance-register
description: Look up the user's saved GenAI use-case reviews (the governance register). Use when the user asks whether a similar use was already reviewed, what outcome it got, or what the register contains.
---

# Governance register lookup

The user keeps a register of reviewed uses of generative AI in a local workspace. Use this skill to answer questions about it.

1. Run `python3 lookup_register.py <keywords>` from this skill's folder (the script sits next to this file). Keywords are optional, each one must appear somewhere in the entry, and the output is one JSON object per line.
2. If the script says `GOVERNANCE_DB_PATH` is not set, tell the user to set it to the absolute path of the register file, which is `.runtime/register.sqlite` inside their genai-bank-governance folder unless they changed it.
3. Answer only from what the script printed. Do not invent entries, owners or reasons.
4. Report each outcome as "what review the sample policy indicates", not as an approval. The four outcomes are Standard controls, Clarification required, Review required and Do not proceed.
5. The script never returns owners, reviewer names or notes. If the user wants those, tell them to open the workspace.

Do not edit the register. It is read only.
