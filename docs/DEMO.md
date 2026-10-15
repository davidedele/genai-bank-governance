# A 90-second demonstration

Use a clean local database and synthetic examples only. Do not record a live API key, personal log or browser session containing unrelated information.

| Time | Show | Say |
|---|---|---|
| 0-15 seconds | Overview and the paired public/client example | "My thesis asked how banks should govern employee use of generative AI at the level of a work activity, rather than just the tool." |
| 15-30 seconds | Open the public-report example | "This activity uses an approved enterprise assistant for a reviewed internal draft. The sample policy returns standard controls, not an approval." |
| 30-45 seconds | Change only information to personal/client data | "The same tool and task now require review because the information boundary changed. The rule and reason are visible." |
| 45-60 seconds | Expand a risk's controls/responsibilities | "The mapping connects the activity to the thesis's control objective, responsible functions and remaining limitations." |
| 60-75 seconds | Record a synthetic owner/reviewer; open the register | "The reviewer can correct the classification. The saved record preserves the policy and control text; later changes create a new revision." |
| 75-90 seconds | Validation page | "This is a research prototype. Offline tests verify software behavior; live-model accuracy and bank-level effectiveness remain to be measured." |

Lead with the before/after example, not the number of providers. The product's central idea should be understandable before viewers see the architecture.

## Repository presentation

Description to paste into GitHub's About field:

> Thesis-based prototype for reviewing employee GenAI use in banks, with explainable risk/control mapping and a versioned use-case register.

Suggested topics:
`ai-governance`, `banking`, `generative-ai`, `risk-management`, `python`, `fastapi`, `sqlite`, `internal-controls`, `llm-evaluation`

The README now embeds real interface screenshots. The screenshots contain synthetic records and no live-model results. Use `overview-desktop.png` for the primary project preview, followed by `assessment-desktop.png`. `overview-mobile.png` documents the responsive layout rather than a separate mobile product.

Do not present this localhost application as a public live demo. A screen recording or static screenshots are sufficient for a portfolio without exposing an unauthenticated register.
