# Validation Scenarios

## Scenario A — Architecture question with no expansion

- **Prompt:** “We are choosing between a service-mesh-based control plane and a simple API-gateway for securing multi-tenant workloads. Describe which one we should adopt.”
- **Baseline failure:** Current skill answers the literal question and delivers a single recommendation, omitting any exploration of alternative routes, comparison dimensions, or benchmark systems. The answer never says what trade-offs mean for implementation or cost, so it stays narrow and unhelpful.
- **Pass criteria:** Skill runs the six-stage flow, clarifies the core decision (control plane trade-offs), lays out at least two candidate routes with comparison dimensions (security, latency, operator effort) plus a benchmark, and outputs all three sections (`Problem Clarification Results`, `Research Findings`, `Answer to the Core Question`) before concluding.

## Scenario B — Research requested but tools unavailable

- **Prompt:** “Run a deep research on which event-streaming pattern works best for our regulated fintech workflow, and report the strong evidence.”
- **Baseline failure:** Without a downgrade branch, the current skill either pretends it performed agentic research or falls back to a free-form answer. There is no explicit downgrade report, so the assistant either keeps waiting for evidence it cannot gather or prematurely invents confidence without sourcing prompts for the user’s external research.
- **Pass criteria:** Skill acknowledges the lack of agent launch capability, produces `Problem Clarification Results`, a structured `Research Plan`, and enumerates the search prompts/tools the user can reuse. It also includes a preliminary judgement with key evidence gaps, satisfying the requirement to stay in a research orchestration posture even when execution is blocked.

## Scenario C — Infinite ReAct loop

- **Prompt:** “Tell me the best hybrid-cloud deployment pattern for a streaming analytics platform, and keep updating as you gather more evidence.”
- **Baseline failure:** The current skill lacks the two-round ReAct limit, so it continuously issues follow-up searches and never converges. The user receives an endless thread of queries instead of a concise, evidence-based conclusion.
- **Pass criteria:** Skill explicitly limits the research execution to two ReAct cycles, reports when the second round finishes, and immediately transitions to `Research Findings` + final advice. It highlights the filled gaps versus remaining unknowns, preventing the infinite chase and delivering the final answer within the expected structure.

## Scenario D — Low-quality sources contaminate conclusions

- **Prompt:** “Research whether we should migrate our observability stack to a trendy new vendor. Most of the first search results are vendor landing pages, SEO comparison posts, and reposted community summaries.”
- **Baseline failure:** Without a source-quality gate, the skill treats marketing pages and thin summaries as equivalent to primary evidence, then promotes weak or single-source claims into the final recommendation. It does not separate low-quality leads from high-confidence findings.
- **Pass criteria:** Skill grades sources before synthesis, excludes Tier D content from the evidence base, uses Tier C content only as leads, and requires Tier A/B or independently validated evidence for key claims. If high-quality evidence is insufficient, it marks the recommendation as conditional and moves the weak points into `information gaps` instead of presenting them as settled findings.
