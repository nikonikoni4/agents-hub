---
name: agent-trainer
description: Guide users to create domain-specific training content for AI agents when they lack expertise in the target domain. Searches best practices, filters quality sources, and generates structured knowledge base and constraints.
---

# Agent Trainer Skill

## Overview

`agent-trainer` helps users create training content for AI agents in domains where the user lacks expertise. Instead of leaving agents with blank configuration, this skill searches domain best practices, evaluates source quality, and generates structured training materials (knowledge base + constraints).

## When to Use

- User wants to create or improve an agent for a domain they're unfamiliar with (video editing, legal consultation, content creation, etc.)
- Agent currently has no domain-specific constraints, leading to unstable output
- User wants the agent to maintain consistent style/behavior across multiple projects
- User explicitly requests "training" or "configuring" an agent

## When Not to Use

- User already knows exactly what rules to write and just needs file editing help
- Agent is for a domain the user is expert in (they should write rules directly)
- User wants to modify an existing well-configured agent (direct editing is faster)
- Request is about debugging agent behavior, not initial training

## Core Principle

This skill exists to **transform scattered domain knowledge into structured agent configuration** when the user cannot do it themselves. Every invocation should clarify the agent's role boundaries, search credible best practices, filter low-quality sources, and output production-ready training materials.

## Workflow Stages

### Stage 1: Agent Role Definition

**Goal:** Clarify the agent's domain, core responsibilities, and operational boundaries.

**Actions:**
- Ask the user: What is this agent's primary function?
- Identify the agent's domain (programming, video editing, content creation, legal, finance, etc.)
- Define what the agent **should do** and what it **should not do**
- Determine who the agent will collaborate with (developers, creators, clients, etc.)
- Identify the target platform (Claude Code / Codex / OpenCode)

**Deliverable:** `Agent Role Definition` containing:
- Agent name
- Target platform
- Primary domain
- Core responsibilities (3-5 bullet points)
- Out-of-scope activities
- Expected collaboration context
- Success criteria (what makes this agent "good"?)

**User confirmation required:** Present the role definition and get explicit approval before proceeding.

### Stage 2: Knowledge Requirements Analysis

**Goal:** Determine what types of knowledge and constraints this agent needs.

**Actions:**
- Based on the domain, identify knowledge categories needed:
  - **Domain fundamentals:** Core concepts, terminology, common workflows
  - **Best practices:** Industry standards, proven patterns, quality criteria
  - **Style guidelines:** Output format, tone, aesthetic preferences (if applicable)
  - **Tool/technology constraints:** Specific tools, libraries, frameworks to use/avoid
  - **Quality standards:** How to evaluate the agent's output
  - **Common pitfalls:** Mistakes to avoid, anti-patterns

- Classify each requirement as:
  - **Hard constraint:** Must be enforced (goes in AGENTS.md/CLAUDE.md)
  - **Soft constraint:** Guideline or preference (goes in knowledge/)

**Deliverable:** `Knowledge Requirements Map` listing:
- Knowledge categories needed for this domain
- For each category: hard vs soft classification
- Search keywords for finding quality sources
- Minimum information needed to make the agent functional

### Stage 3: Knowledge Search & Quality Filtering

**Goal:** Gather structured evidence from credible sources, filtered by quality tier.

**Actions:**
- Execute web searches using the keywords from Stage 2
- For each search result, evaluate source quality using the Source Quality Gate (below)
- Extract relevant information: best practices, standards, guidelines, examples
- Track source URLs and quality tier for each piece of information
- **Stop after 2 ReAct rounds** — no infinite searching

**Source Quality Gate:**

- **Tier A:** Official documentation, industry standards, academic research, technical specifications, primary sources (e.g., official React docs, W3C standards, IEEE papers)
- **Tier B:** High-quality professional articles, expert analysis with concrete examples, reputable industry publications, established practitioner guides (e.g., thoughtful engineering blogs, conference talks from recognized experts)
- **Tier C:** General tutorials, community discussions, forum posts, aggregator sites, personal blogs without verification (e.g., Medium posts, Reddit threads, generic how-to guides)
- **Tier D:** Marketing content, clickbait, unverifiable claims, anonymous sources, content farms

**Use Rules:**
- Build core constraints from **Tier A/B sources only**
- Tier C sources may suggest **leads or keywords**, but cannot stand alone as evidence for hard constraints
- **Exclude Tier D sources** from the evidence base
- Any hard constraint must be supported by **either** two independent Tier A/B sources **or** one Tier A source plus one Tier B validation
- If evidence quality is weak, **downgrade to soft constraint** or mark as "unverified guideline"

**ReAct Iteration Cap:**
1. **Round 1:** Gather initial evidence across all knowledge categories, identify major information gaps
2. **Round 2:** Fill the highest-priority gaps or verify contested claims, then stop and proceed to synthesis

**Deliverable:** `Evidence Collection` containing:
- For each knowledge category: collected information with source URLs and quality tier
- High-confidence findings (Tier A/B supported)
- Conditional findings (single source or Tier C supported)
- Information gaps (categories where quality evidence is missing)

### Stage 4: Rule Extraction & Classification

**Goal:** Synthesize collected evidence into concrete, actionable rules.

**Actions:**
- Review all high-confidence findings from Stage 3
- Extract specific, actionable rules (not vague advice)
- For each rule, determine:
  - Is this a **hard constraint** (must follow) or **soft guideline** (should consider)?
  - Is this supported by Tier A/B evidence?
  - Is this applicable across projects or context-specific?
- Group rules by category (workflow, style, tools, quality, pitfalls)
- Deduplicate and resolve conflicts
- Mark any rule based on weak evidence as "suggested practice (unverified)"

**Classification criteria:**
- **Hard constraint** → AGENTS.md/CLAUDE.md:
  - Tier A/B supported
  - Prevents common critical errors
  - Enforces essential quality standards
  - Specifies required tools/technologies
  
- **Soft guideline** → knowledge/:
  - Tier B/C supported or single-source
  - Style preferences, not correctness
  - Contextual best practices
  - Background knowledge, examples, references

**Deliverable:** `Extracted Rules` containing:
- Hard constraints list (each with source tier and rationale)
- Soft guidelines list (grouped by knowledge category)
- Rules excluded due to weak evidence (moved to information gaps)
- Conflict resolutions (if sources disagreed)

**User confirmation required:** Present the extracted rules and get feedback before generating files.

### Stage 5: Training Material Generation

**Goal:** Generate production-ready training files in the agent's work_root.

**Actions:**
- Determine target platform and system prompt file:
  - Codex → `AGENTS.md`
  - Claude Code → `CLAUDE.md`
  - OpenCode → `AGENTS.md`

- Generate system prompt file structure:
  ```markdown
  # Agent Training Content
  
  ## Role Definition
  [From Stage 1]
  
  ## Hard Constraints
  [From Stage 4 - hard constraints]
  
  ## Knowledge Base
  See the following documents for domain knowledge and best practices:
  - [Domain Fundamentals](./knowledge/domain-fundamentals.md)
  - [Best Practices](./knowledge/best-practices.md)
  - [Style Guide](./knowledge/style-guide.md) [if applicable]
  ```

- Generate knowledge base files in `knowledge/`:
  - `domain-fundamentals.md`: Core concepts, terminology, workflows
  - `best-practices.md`: Proven patterns, quality criteria, examples
  - `style-guide.md`: Output format, tone, aesthetic guidelines (if applicable)
  - Each file includes source references at the bottom

- Write files to `local_data/agents/<agent_name>/work_root/`

**File format standards:**
- Use clear headers and bullet points
- Include concrete examples where possible
- Cite sources (Tier A/B) at the end of each section
- Mark unverified content with "(suggested practice, not verified)"
- Keep hard constraints concise and enforceable

**Deliverable:** Generated files written to disk:
- `work_root/AGENTS.md` or `CLAUDE.md`
- `work_root/knowledge/domain-fundamentals.md`
- `work_root/knowledge/best-practices.md`
- `work_root/knowledge/style-guide.md` (if applicable)

### Stage 6: Validation & Iteration

**Goal:** Ensure the training materials meet user expectations and are immediately usable.

**Actions:**
- Show the user what was generated (file paths and key content summary)
- Ask: "Does this match your expectations? Any adjustments needed?"
- If user requests changes:
  - Make specific edits (don't regenerate everything)
  - Update only the affected sections
  - Preserve source citations
- If user approves:
  - Confirm the agent is ready to use
  - Suggest testing the agent in a real scenario

**Deliverable:** `Training Summary` containing:
- Agent name and platform
- Files created (with paths)
- Key constraints enforced
- Knowledge areas covered
- Information gaps (what the training doesn't cover yet)
- Suggested next steps (test scenarios, manual refinements)

### Stage 7: Downgrade Escalation

**Trigger:** Cannot complete training (web search unavailable, user declines search, evidence stalled)

**Response:**
- Preserve current progress (role definition, knowledge requirements)
- Provide a manual research guide:
  - Specific search keywords
  - Quality evaluation checklist
  - Template files to fill in
  - Example rules from similar domains
- Document what was attempted and what's missing

**Downgrade handoff checklist:**
- Role definition (from Stage 1)
- Knowledge requirements map (from Stage 2)
- Search keywords and quality criteria
- Template files for manual editing
- Information gaps list

## Output Contract

Every successful training session must produce:

### 1. Agent Role Definition
- Agent name
- Target platform
- Primary domain
- Core responsibilities
- Out-of-scope activities
- Collaboration context
- Success criteria

### 2. Evidence Quality Report
- High-confidence findings (Tier A/B)
- Conditional findings (weaker evidence)
- Information gaps
- Source summary (number of sources per tier)

### 3. Generated Training Files
- System prompt file (AGENTS.md or CLAUDE.md)
- Knowledge base files (knowledge/*.md)
- Source citations included

### 4. Training Summary
- Files created
- Key constraints
- Knowledge coverage
- Known limitations
- Next steps

## Anti-Pattern Guards

1. **Accepting Tier C/D sources as evidence for hard constraints:** Must filter quality before making rules; weak sources can only suggest leads
2. **Searching indefinitely:** Must stop after 2 ReAct rounds and synthesize what was found
3. **Generating vague rules:** Must extract specific, actionable constraints (e.g., "Use TypeScript with strict mode" not "Write good code")
4. **Skipping user confirmation:** Must get approval after Stage 1 (role definition) and Stage 4 (extracted rules) before generating files
5. **Mixing hard and soft constraints:** Must clearly separate "must follow" rules (in system prompt) from "should consider" guidelines (in knowledge/)
6. **Ignoring information gaps:** Must document what couldn't be found with quality evidence, don't pretend everything is covered
7. **Creating agent without clear scope:** Must complete Stage 1 role definition before any research; no generic "helpful assistant" agents

## Quality Checklist

- Did I get user confirmation on the role definition (Stage 1)?
- Did I filter sources by quality tier and exclude Tier C/D from hard constraints?
- Did I stop research after 2 ReAct rounds?
- Did I separate hard constraints (system prompt) from soft guidelines (knowledge/)?
- Did I cite Tier A/B sources for all hard constraints?
- Did I document information gaps rather than filling them with speculation?
- Did I get user approval on extracted rules (Stage 4) before generating files?
- Did the final output include all required sections (role definition, evidence report, files, training summary)?

## Domain-Specific Adaptations

The workflow is domain-agnostic, but different domains may emphasize different knowledge categories:

**Programming/Development:**
- Focus on: tools/frameworks, code quality, security, performance
- Hard constraints: language/framework choice, security practices, required testing
- Soft guidelines: style preferences, architecture patterns, naming conventions

**Content Creation (writing, video, design):**
- Focus on: style guidelines, audience targeting, format specifications
- Hard constraints: format requirements, legal/ethical boundaries, brand guidelines
- Soft guidelines: tone, aesthetic preferences, storytelling techniques

**Professional Services (legal, finance, consulting):**
- Focus on: regulatory compliance, terminology precision, documentation standards
- Hard constraints: legal requirements, industry regulations, ethical standards
- Soft guidelines: client communication style, report formats, analysis frameworks

**Creative/Artistic (video editing, music, design):**
- Focus on: aesthetic principles, technical tools, workflow efficiency
- Hard constraints: technical specifications (resolution, format, export settings)
- Soft guidelines: composition rules, color theory, pacing/rhythm preferences

## Example Interaction Flow

```
User: "I want to create a video editing agent but I don't know anything about video editing."

Agent: [Starts Stage 1]
"Let's define this agent's role. I need to understand:
1. What type of videos will this agent help edit? (e.g., YouTube tutorials, short-form social media, documentary-style)
2. What should the agent do? (e.g., suggest cuts, recommend transitions, optimize pacing)
3. What should it NOT do? (e.g., make final creative decisions, handle audio mixing)
4. Who will use this agent? (you as a beginner, or will you collaborate with others?)"

User: [Answers questions]

Agent: [Presents Role Definition]
"Here's what I understood:
- Agent name: Video Editing Assistant
- Platform: Codex
- Domain: Video editing for YouTube tutorials
- Core responsibilities:
  - Suggest cut points based on pacing best practices
  - Recommend transitions that maintain flow
  - Identify technical issues (lighting, audio sync)
- Out of scope:
  - Final creative direction (user decides)
  - Audio mixing/mastering
  - Motion graphics creation
- Collaboration: Works with you (beginner editor) to learn editing fundamentals

Does this match your needs?"

User: "Yes, that's right."

Agent: [Stage 2 - Knowledge Requirements Analysis]
"For a video editing agent, I'll search for:
- Hard constraints: Technical standards (resolution, frame rate, export formats)
- Hard constraints: Common editing mistakes to avoid
- Soft guidelines: Pacing best practices for tutorials
- Soft guidelines: Transition selection guidance
- Soft guidelines: Storytelling structure for instructional content

Starting research..."

Agent: [Stage 3 - Searches and evaluates sources]
[After 2 ReAct rounds]
"Research complete. Found:
- 8 Tier A/B sources (official editing software docs, professional editor guides)
- 12 Tier C sources (useful for context, but not used for hard rules)
- Information gaps: Color grading standards (couldn't find authoritative source)

Moving to rule extraction..."

Agent: [Stage 4 - Presents extracted rules]
"I've extracted these rules:

Hard Constraints (will enforce):
1. Export settings: 1080p minimum, H.264 codec, 60fps for screen recordings [Source: YouTube Creator Standards]
2. Avoid jump cuts within 0.5s of each other (creates jarring effect) [Source: Film Editing Pro Guide + Video Production Handbook]
3. Use L-cuts and J-cuts for dialogue transitions (audio leads/follows video) [Source: Professional Editing Techniques]

Soft Guidelines (for knowledge base):
- Tutorial pacing: 1.5-2x speed for demonstrations, slow for key explanations
- Transition usage: Limit to 2-3 types per video for consistency
- Opening: Hook viewer in first 10 seconds with problem statement

Information gaps:
- Color grading: Found only generic advice, no authoritative standards for tutorials

Approve these rules?"

User: "Yes, but add a constraint about keeping videos under 15 minutes."

Agent: [Updates rules]
"Added: Maximum video length 15 minutes (tutorial retention best practice)

Generating training files..."

Agent: [Stage 5 - Generates files]
"Created training materials:
- work_root/AGENTS.md (system prompt with hard constraints)
- work_root/knowledge/editing-fundamentals.md
- work_root/knowledge/tutorial-best-practices.md

Your Video Editing Assistant is ready. Suggested test: Ask it to review a rough cut and suggest improvements."
```

## Notes for Implementation

- This skill should be assigned to the **Agents-Hub Assistant** (the system helper agent)
- User triggers it via a "Training" button in the frontend, which sends a message like: "/train-agent <agent_name>"
- The skill automatically detects whether the agent already exists (update mode) or needs to be created
- All file writes go to `local_data/agents/<agent_name>/work_root/`, which is outside any project repository
- Training content is **cross-project**: same agent can be used in multiple projects with consistent behavior
