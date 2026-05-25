---
name: deep-answer
description: Use when answering architecture, solution design, technical selection, or other open-ended strategy questions where direct Q&A would stay too narrow and a structured deep-research workflow is needed.
---

# Deep Answer Skill

## Overview

`deep-answer` is a research orchestration skill for high-level strategy prompts. It pauses before providing a quick judgment, clarifies the true decision space, and coordinates research steps so that responses expand the user’s view rather than echo the original question.

## When to Use

- The user compares architectures, solution candidates, or complex technical strategies and needs trade-off visibility.
- Direct Q&A would stay narrow because multiple routes, dimensions, or benchmarks must be contrasted.
- The prompt asks for a research-style report, evidence trail, or multi-faceted recommendation rather than a single bullet answer.

## When Not to Use

- The prompt is a pure fact lookup, quick debugging help, or straightforward how-to.
- Constraints are locked in and the user only needs an execution plan for a known solution.
- The user explicitly rejects structured research and wants a one-sentence verdict.

## Core Principle

This skill exists to expand the user’s decision space. Every invocation should clarify boundaries, propose a structured investigation, and keep the discussion grounded in research instead of literal answers.

## Workflow Stages

### Stage 1: Problem Clarification

- **Goal:** Surface the real decision behind the user’s request, including trade-offs that matter.
- **Actions:** Ask follow-up questions, present 2–3 candidate interpretations, and define research boundaries, comparison dimensions, benchmarks, and success criteria.
- **Deliverable:** `Problem Clarification Results` that records the core question, study boundary, out-of-scope clarifications, dimensions to compare, relevant benchmark systems, and what success looks like.

### Stage 2: Research Design

- **Goal:** Turn the clarified question into discrete research tasks.
- **Actions:** Split the investigation into 2–4 tasks (e.g., technical path, engineering cost, risk profile, organizational impact) and specify the evidence each task needs.
- **Deliverable:** `Research Plan` listing each task, its objective, expected evidence type, and preferred deliverable format.

### Stage 3: Research Execution

- **Goal:** Gather structured evidence through agentic research or an agreed-upon alternative.
- **Actions:** Confirm with the user whether to launch sub-agents; if not feasible, note that the investigation will pause while preserving the plan; otherwise, execute the research tasks and capture findings.
- **Deliverable:** Evidence snippets and findings packets (e.g., sourced observations, data points, or quote-backed notes) that Stage 4 can synthesize.
- **Constraint:** Research execution is capped at two ReAct rounds. After the second round the flow must pivot to Stage 4; no additional exploratory searches are permitted.

#### Source Quality Gate

- **Tier A:** official documentation, standards, research papers, technical reports, primary data, first-party announcements.
- **Tier B:** high-quality engineering writeups, mature expert analysis, reputable long-form industry reporting with concrete evidence.
- **Tier C:** ordinary blogs, community posts, forum threads, aggregators, unsourced summaries.
- **Tier D:** anonymous reposts, content farms, clickbait, pure marketing copy, unverifiable opinions.

- **Use rule:** build key conclusions from Tier A/B sources first.
- **C-source rule:** Tier C sources may suggest leads, keywords, or dispute points, but may not stand alone as support for a key conclusion.
- **D-source rule:** Tier D sources are excluded from the evidence base.
- **Verification rule:** any claim that materially changes the final recommendation must be supported by either two independent high-quality sources or one strong primary source plus one independent validation source.
- **Fallback rule:** if evidence quality is weak, downgrade the claim to `conditional` or `unverified` and carry it into the information-gap list instead of presenting it as a settled finding.

#### ReAct Iteration Cap

1. **Round 1** — gather initial evidence, log supporting facts, and surface the most pressing information gaps.
2. **Round 2** — only revisit the highest-value gaps or verify the most contested claims before stopping exploration and proceeding to synthesis.

### Stage 4: Evidence Synthesis

- **Goal:** Synthesize collected data into comparable conclusions.
- **Actions:** Deduplicate, categorize, note conflicts, and label each insight as high-confidence, conditional, or hypothesized while documenting remaining gaps.
- **Evidence handling:** separate core evidence from low-quality leads, record source quality when it materially affects confidence, and do not allow low-quality or single-source claims to become headline findings without explicit qualification.
- **Deliverable:** `Research Findings` summarizing key findings, route comparisons, evidence strength, major disputes, and outstanding information gaps.

### Stage 5: User-Focused Answer

- **Goal:** Translate the research into a decision recommendation that answers the clarified question.
- **Actions:** Map findings to candidate routes, explain applicability conditions, justify trade-offs, and restate unknowns.
- **Deliverable:** `Answer to the Core Question` that provides the final judgement, recommended route, applicability limits, rejected options with rationale, and suggested next steps.

### Stage 6: Downgrade Escalation

- **Trigger:** Research cannot proceed (tooling unavailable, user declines agentic execution, or evidence stalled).
- **Response:** Pause active investigation, preserve the current research state, and hand the user a usable downgrade package they can continue with elsewhere.
- **Downgrade handoff checklist:** preserve the clarification state, the current research plan, reusable prompts/tools for external work, any preliminary judgement or direction, and the most critical outstanding information gaps.

## Output Contract

Every response must include the following sections with the specified fields:

### 1. Problem Clarification Results

- Core question
- Study boundary
- Out-of-scope items
- Comparison dimensions
- Benchmark or reference systems
- Success criteria

### 2. Research Findings

- Key findings
- Route comparisons
- Evidence quality
- Major disputes
- Information gaps

### 3. Answer to the Core Question

- Final conclusion
- Recommended route
- Applicability conditions
- Rejected route(s) with rationale
- Next steps

The final section should clearly separate what was observed (research findings) from interpretation or recommendation.

## Sub-Agent Coordination

- **Route Research Agent:** maps candidate routes, dependencies, and scenario fit so the decision space is explicit.
- **Evidence Challenge Agent:** validates key claims, surfaces counterexamples, and flags boundary conditions that force deeper scrutiny.
- **Engineering & Risk Agent:** evaluates implementation complexity, migration cost, organizational impact, and maintenance risk so trade-offs stay grounded.

- **Anti-Glue Rule:** the main agent must rewrite the synthesis into a single, coherent conclusion; it may not simply paste child-agent notes into the final answer.

## Anti-Pattern Guards

1. **Answering only the literal question:** Must expand the response with candidate routes, comparison dimensions, and benchmark context instead of stopping at the surface prompt.
2. **Dumping search results without synthesis:** Must turn raw evidence into structured findings before presenting them in `Research Findings`.
3. **Stating inference as fact:** Must label which statements are sourced evidence and which are the agent’s integrative judgements.
4. **Searching indefinitely:** Must stop after two ReAct rounds and move to synthesis, never continuing recursive follow-up queries.
5. **Pasting child-agent output directly:** Must rewrite sub-agent notes into a single coherent narrative; copying blocks verbatim is forbidden.
6. **Giving conclusions that do not answer the user’s decision:** Must tie the final section back to the clarified core question with a recommendation and trade-off rationale.
7. **Treating low-quality sources as evidence:** Must filter source quality before synthesis; weak or unverifiable sources may generate leads, but they cannot anchor the final recommendation.

## Quality Checklist

- Did I expand routes, dimensions, and benchmark before drawing conclusions?
- Did I separate the evidence findings from the recommendation language?
- Did I filter low-quality sources out of the core evidence base and mark weak claims as conditional or unverified?
- Did I stop research after two ReAct rounds before synthesizing?
- Did the response include all three output sections with their required fields?
- If I downgraded, did I still provide a usable research plan, prompts, and gap list?
