---
name: session-host
description: Deep research on conference talks, speakers, and their groups to prepare a session host with informed questions on a risk spectrum. Uses parallel background subagents for web research and creates structured briefing markdown documents. Use when chairing or hosting a session at a scientific conference.
argument-hint: [path to session description (markdown / text)] [--output dir/]
---

# Conference Session Host Preparation

Orchestrate deep background research on conference talks to prepare a session host with informed questions. Uses parallel subagents, web research, and produces structured markdown briefing documents.

**Key principle:** Agents own their output files. Each research agent writes its own per-talk markdown file after orchestrator confirmation. The orchestrator writes only the overview document.

## When to Use

Invoke when the user needs to:
- Prepare as a session host/chair for a scientific conference
- Research speakers, their groups, and talk topics before a session
- Generate informed questions spanning safe-to-speculative for each talk
- Create structured briefing markdown documents

## Phase 1: Discovery

Read the session description provided by the user. Accepted forms:

- A path to a markdown / text file listing the session and its talks
- Pasted text in the chat with the same content
- A conference program URL (use `WebFetch` to read it)

For each talk, extract:
- **Talk title** (full verbatim title as listed in the program)
- **Presenter** (name + institution)
- **Authors** (names + institutions)

Present a summary table to the user before proceeding:

| # | Title | Presenter | Institution | Authors |
|---|-------|-----------|-------------|---------|

Ask if anything needs correction or if the user has additional context. Confirm the output directory (default: `briefings/<session-slug>/` next to the input).

## Phase 2: Dispatch Planning

Plan **one research agent per talk**.

**Roles:**
- **You (orchestrator):** Plan, dispatch agents, review summaries, write the overview document
- **N research agents** (one per talk): Deep-dive web research + write per-talk markdown file

Track one item per talk (independent, run in parallel) plus a final consolidation item that waits for all of them.

## Phase 3: Agent Dispatch

Spawn all research agents in parallel with the `Agent` tool: one call per talk, all in the same message, each running in the background. Name each agent after its talk (e.g. `talk-01-<presenter-slug>`), or keep the agent ID each call returns. You need the name or ID to reply to that agent later.

Each agent receives the full prompt from the [Research Agent Template](#research-agent-template) below, customized with:
- Specific talk details (title, presenter, authors)
- The output directory and the agent's target filename
- Suggested search queries and group leader hints

**Optional — author cross-reference search:** Include an extra last research step in the prompt: look up prior work from the talk authors. Use whichever of these the user has configured:

- A paper-retrieval MCP (e.g. one that exposes `search_papers(authorName="...")`)
- `WebSearch` with the author's name + likely topic keywords
- A local notes / literature folder via file search (ripgrep, fzf, or any search MCP over your notes)

This step is purely additive. Agents run it only after they have completed their primary research, and skip it entirely if no suitable tool is available.

## Phase 4: Review & Confirm

Each agent follows a two-phase workflow: **research first, then write the markdown file after confirmation.** An agent ends its research phase by returning a short summary as its final message. You reply with `SendMessage` to its name or ID. That resumes the same agent with its full research context, so it can revise or write without starting over. Never spawn a fresh agent for the write step: it would have none of the research.

When an agent's research summary arrives:
1. Review the summary for:
   - **Completeness:** Did they find the group leader, presenter profile, recent publications?
   - **Question quality:** Do questions follow the risk spectrum? Are they genuinely useful?
   - **Accuracy:** Do claims have sources? Any obvious errors?
2. If deficient, `SendMessage` the agent specific corrections and ask it to revise
3. If satisfactory, `SendMessage` the agent: **proceed to write the markdown file**
4. The agent writes its per-talk markdown file
5. The agent's final message reports the relative file path
6. Mark the corresponding task as completed
7. Provide the user with a brief highlight summary per talk as reports arrive

**Why agents write directly:** This avoids transferring the full research report through the orchestrator's context window. The agent already has all the content — let it write directly. The orchestrator only needs the summary for review and the file path for the overview.

## Phase 5: Overview Document

Once all agents have written their per-talk files, write the **overview document** at `<output_dir>/README.md`.

**Overview structure (markdown):**
- Session title, conference name, date
- For each talk: **full verbatim talk title**, presenter, group leader, key insight, core novelty, sharpest question
- Relative markdown links to each talk's detailed file (e.g. `[Talk Title](./talk-01-presenter.md)`)

## Phase 6: Wrap-up

Agents stop on their own once they have reported their file path, so there is nothing to shut down. Present the final summary to the user.

---

## Research Agent Template

Below is the template for each research agent's prompt. Replace `{{placeholders}}` with actual values.

```
You are one of several research agents preparing the host of the {{SESSION_NAME}} at the {{CONFERENCE_NAME}}. Your job is to deeply research ONE specific talk so the host can ask informed, intelligent questions — and then write a polished briefing markdown file.

## Your Talk

**Title:** "{{TALK_TITLE}}"
**Presenter:** {{PRESENTER_NAME}}, {{PRESENTER_INSTITUTION}}
**Authors:** {{AUTHORS_LIST}}

## Output Target

- **Output directory:** {{OUTPUT_DIR}}
- **Filename:** `talk-{{TALK_NUMBER_PADDED}}-{{PRESENTER_SLUG}}.md`

## Your Workflow

You have TWO phases: **research**, then **write the markdown file** (after orchestrator confirmation).

### PHASE 1: Research

Do the following steps sequentially, using web search extensively:

#### Step 1: Identify Group Leader & Group Profile
- Web search the likely group leader (usually a professor among the authors) at their institution
- Find their university group page, research interests, h-index if available
- Identify the group's core research themes and how they connect to this talk

#### Step 2: Map the Co-Authors
- Search each co-author to determine their role (postdoc, PhD student, senior scientist, collaborator from another group?)
- Identify any interdisciplinary collaborations (multiple groups contributing)
- The presenter is often a PhD student — confirm their career stage and specific focus

#### Step 3: Recent Group Publications
- Search for 3-5 recent publications from the group on the talk topic
- Try search queries combining: group leader name + key topic terms
- Try presenter name + institution for their specific publications
- Also search for any foundational papers from the group that this work builds on

#### Step 4: State of the Art Context
- What are the key concepts, methods, and challenges in this research area?
- What makes this specific approach novel or interesting?
- What are competing approaches or alternative methods?
- What are the open questions and current limitations?

#### Step 5: Draft 10 Questions

The host needs questions they can ask if the audience is quiet. Questions are rated by **host risk** — not how hard they are for the speaker, but how likely they are to be relevant given that we haven't seen the talk yet.

Create 10 questions on a spectrum:

**SAFE — Questions 1-3 (will definitely be relevant):**
These are questions about the broader field, general methodology, or basic aspects of the work that ANY talk on this topic would cover. The host can ask these with full confidence they'll land regardless of the exact talk content.
Examples: "What methodology did you use?", "Why did you choose this specific system/model/approach?", "How did you validate your results?"

**MEDIUM — Questions 4-6 (likely relevant, shows engagement):**
More specific questions that reference the group's prior work or known methodological details. These show the host has done homework and will likely connect to the talk content.
Examples: "Your group previously showed X — does that trend hold here?", "How does [known challenge] affect your results?"

**POINTED — Questions 7-8 (good bet, connects to broader field):**
Questions that position the work within the larger research landscape. These push the presenter to reflect on implications, comparisons, or practical relevance. They're likely relevant but probe beyond what the talk explicitly covers.
Examples: "How does your approach compare to [alternative]?", "What are the implications for [application]?"

**HIGH RISK — Questions 9-10 (calculated bets on talk content):**
These are sharp, specific questions based on educated guesses about what the talk will cover. They reference cutting-edge findings, subtle mechanistic details, or forward-looking challenges. If the talk touches on these topics, the questions will seem brilliantly informed. If not, they may fall flat — but the upside is worth the risk.
Examples: "Did you observe [specific phenomenon from recent literature]?", "Have you considered [novel connection to adjacent field]?"

For each question provide:
- The question itself
- Risk level label
- 1-2 sentence rationale: why this question is relevant, what you'd learn, and why it's at this risk level

#### Step 6: Return a Summary to the Orchestrator

After completing your research, end this phase by returning a **concise summary** as your final message. Include:
- Group leader name + institution
- Presenter career stage
- Core novelty of the talk (1-2 sentences)
- Your single sharpest question
- Confirmation that you have 10 questions ready
- Any notable findings (e.g., connection to host's own work, interdisciplinary bridges)

**Do NOT return the full report.** The orchestrator only needs enough to verify quality. Do not write the file yet: the orchestrator will resume you with a message that either confirms or asks for corrections.

### PHASE 2: Write the Markdown File

**Only proceed after the orchestrator confirms your research is satisfactory.**

Write to `{{OUTPUT_DIR}}/talk-{{TALK_NUMBER_PADDED}}-{{PRESENTER_SLUG}}.md` using standard markdown.

**Required document structure:**

```markdown
# {{TALK_TITLE}}

> **Full verbatim talk title as listed in the conference program**

- **Presenter:** Name (career stage) | **Group:** Prof. X, Institution
- **Authors:** Full author list with roles where known

## Group Background

Paragraphs + bullet lists about the group leader, institution, research themes.

## Presenter Profile

Paragraphs about the presenter's career stage, focus, publications.

## Co-Author Context (if applicable)

Paragraphs + bullet lists about collaborations, bridge persons.

## Relevant Recent Research

1. **Author et al.** — "Full Paper Title" — *Journal* Year, Vol, Pages. _Why this paper matters._
2. ...

## Talk Context & State of the Art

Paragraphs + bullet lists explaining:
- What the talk is most likely about
- Key concepts and challenges
- What makes the work novel

## 10 Questions for the Host

### SAFE — Questions 1–3

**Q1.** Question text.
_Rationale: why this is safe and what you'd learn._

(continue Q2, Q3)

### MEDIUM — Questions 4–6

(same format)

### POINTED — Questions 7–8

(same format)

### HIGH RISK — Questions 9–10

(same format; mark the standout question with a leading 🔑 or **(top pick)**)
```

**Critical formatting rules:**
- The **full verbatim talk title** MUST appear in the document body (not just as a filename abbreviation)
- Use bold for names, paper titles, key terms; italics for rationales and supplementary context
- Include author names, journal, year for all cited papers
- Use horizontal rules (`---`) sparingly to break very long sections

#### Step 2c: Report Back

After writing the file, end with a final message to the orchestrator containing:
- The relative path to the file
- Confirmation that writing is complete

Be thorough in your research, cite sources where possible (URLs), and produce a document genuinely useful for a session host at a scientific conference.
```

---

## Orchestrator Checklist

Use this checklist to track progress:

- [ ] Read session description and extracted all talk details (title, presenter, authors) — including full verbatim titles
- [ ] Confirmed talk list and output directory with user
- [ ] Planned one agent per talk
- [ ] Dispatched research agents (one per talk, in parallel, names or IDs noted)
- [ ] (Optional) Included the cross-reference search step for any local literature library
- [ ] Reviewed each agent's summary and confirmed the write via SendMessage
- [ ] Collected file paths from all agents
- [ ] Wrote overview README.md (with relative links + full talk titles)

## Lessons from Prior Runs

**What works well:**
- Giving agents specific search queries to try (not just topics) dramatically improves their research quality
- Suggesting who the group leader likely is (based on author list) saves agents time
- Noting likely career stages ("probably a PhD student") helps agents calibrate their search
- Agents find genuinely useful connections when given enough context (e.g., identifying "bridge persons" between collaborating groups, finding the host's own papers)
- Parallel dispatch saves significant time (~11 min per agent, all running simultaneously)
- Placing the optional cross-reference search last in the prompt lets agents finish their primary research first
- Having agents write the markdown directly (after confirmation) avoids context window bloat on the orchestrator

**Agent behavior patterns observed:**
- Agents execute ~20-30 web searches per talk over ~11 minutes
- They handle HTTP errors gracefully (403s, 404s) and retry with alternative queries
- They naturally follow the systematic workflow: group leader → co-authors → publications → state of art → compile
- They respond well to targeted follow-up messages after their summary

**Question risk calibration:**
- The risk spectrum is from the HOST's perspective: "How confident am I that this question will be relevant to the actual talk?"
- SAFE = guaranteed relevant regardless of exact talk content
- HIGH RISK = educated guess about specific talk content; brilliant if it hits, awkward if it misses
- This naturally correlates with question depth (general → specific), but the framing matters

**Context management:**
- Do NOT accumulate full agent reports in the orchestrator's context — review summaries only
- Each agent writes its own markdown file, transferring only the relative path back
- Write the overview document last, once all paths are collected
- If an agent's summary is deficient, send targeted corrections rather than requesting the full report
