# Research-to-software mapping

| Thesis element | Software representation | Boundary |
|---|---|---|
| Four forms of employee use, Section 3.2 | Multi-label `forms` field | Categories can overlap; no forced single form. |
| Five use-case dimensions, Section 3.3 / Table 3 | Validated categorical fields | Unknown values are added to avoid unsupported inference. |
| Tool approval differs from approval of a use, Section 5.2 | Separate `approval_status` | Enterprise access never automatically establishes approval. |
| Use-case register, Section 5.2 | Local reviewed records with owner and revision history | Self-declared ownership is not authentication or organizational acceptance. |
| Generated-code controls, Section 5.4 | Explicit review predicate and corresponding controls | No claim the software performs code review or testing. |
| Proportionate traceability, Section 5.5 | Opt-in description retention and frozen assessment evidence | Logs alone do not demonstrate meaningful review. |
| Three Lines responsibilities, Section 5.5 | Retained control owners and assurance roles | The app does not assign real roles or independence inside an organization. |
| Nine descriptive risk areas, Table 5 | `RISK_AREAS` and frozen control snapshots | These are not numerical ratings or exhaustive legal categories. |
| Limits stated in the Conclusion | Visible research/prototype boundaries | No empirical bank validation or legal compliance assertion. |

The thesis's contribution is the analytical connection between activity characteristics, risks, controls and responsibilities. Optional LLM extraction, deterministic triage, the benchmark and the interface are software extensions. The triage rules must not be attributed to a regulator merely because the thesis cites financial authorities.

The scenario library is inspired by the thesis; it is not a collection of observed employee interactions. One original sample stated that an approved tool was used for an unconsidered purpose but encoded the use as approved. That contradiction is corrected. A second example now refers to the employee's ability to evaluate an assessment rather than silently equating employee expertise with model capability.
