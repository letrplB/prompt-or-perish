---
name: exam-solutions
description: Generate correction templates for exams from .docx files. Extracts questions, researches solutions, and produces structured markdown documents with model answers, point distribution, and grading rubrics. Uses parallel agent teams (one per question). Auto-detects the exam language and writes output in that language.
argument-hint: [path to exam .docx file] [--output dir/]
---

# Exam Correction Template Generator

Generate structured correction templates for exams. Extracts the exam from a .docx file, parses questions and point allocations, researches and solves each question via a parallel agent team, and produces rich markdown documents with model answers and grading rubrics.

**Key principle:** Agents propose solutions first; the orchestrator reviews with the user before agents commit them to disk. Each agent writes its own per-question markdown file after approval.

**Language handling:** The skill auto-detects the exam language and agents write all output (section headings, labels, body text) in that language. The templates below show the English variant; agents translate the labels at runtime.

## When to Use

Invoke when the user:
- Provides an exam .docx file and wants a correction template
- Asks to generate model solutions for an exam
- Needs grading rubrics or point distribution templates for exam questions

## Inputs

**Required:**
- Path to a `.docx` file containing the exam

**Optional:**
- `--output <dir>` — destination directory for the solution markdown files. Default: `solutions/<exam-slug>/` next to the input.

**Determined during workflow (ask if needed):**
- Which questions to solve (all or a selection)
- Point distribution strategy (clarified before team dispatch)

## Phase 1: Extract & Parse the Exam

1. Install `python-docx` if not available (`pip3 install --break-system-packages python-docx`)
2. Extract full text from the .docx using Python + `python-docx`
3. Parse and identify:
   - **Exam metadata:** title, course name, date, location, time/duration, institute, instructor, allowed materials, total points
   - **Questions:** number, full text, sub-questions (a, b, c...), point values per (sub-)question
   - **Language:** detect from exam text
4. Build a structured representation of the exam

### Parsing Strategy

Exams typically follow patterns like:
- "Question 1 (15 points)" or its localised equivalent
- Sub-questions: "a)", "b)", "i.", "ii." with individual point values
- Point values in parentheses, brackets, or after keywords meaning "points" / "pts" in the exam's language

If the structure is ambiguous (unclear point distribution, nested sub-questions, unclear question boundaries), flag these specifically for user clarification in Phase 2.

## Phase 2: Clarify with User

Present the extracted exam structure to the user in a clear table:

```
**Exam:** [Title]
**Course:** [Course Name]
**Date:** [Date] | **Duration:** [Time]
**Total Points:** [X]
**Language:** [Detected language]

| Question | Sub-Q | Points | Topic/Summary |
|----------|-------|--------|---------------|
| 1        |       | 15     | [Brief topic] |
|          | a)    | 5      | [Brief desc]  |
|          | b)    | 10     | [Brief desc]  |
| 2        |       | 20     | [Brief topic] |
| ...      |       |        |               |
```

### Clarify the following:

1. **Correctness check:** "Does this match the exam structure? Any questions I parsed incorrectly?"
2. **Scope:** "Which questions should I solve? (All / selection)"
3. **Point distribution strategy:** This is critical for the grading rubric.
   - For questions with many points (e.g., 15+): coarser rubric is acceptable (e.g., "5 points for concept X, 5 for derivation, 5 for result")
   - For questions with few points (e.g., 2-5): granularity must be higher (e.g., "1 point for naming the compound, 1 point for correct structure")
   - Ask: "How granular should the point rubrics be? Should I distribute points down to individual concepts, or is a coarser breakdown sufficient for the larger questions?"
4. **Special instructions:** "Any specific methods, conventions, or textbook references I should use for particular questions?"
5. **Output location:** Confirm or override the default output directory.
6. **Language confirmation** (only if detection is uncertain)

**Do NOT proceed to team dispatch until the user has confirmed the structure and point distribution strategy.**

## Phase 3: Team Planning

**CRITICAL: Use a real agent team (TeamCreate + SendMessage), NOT standalone subagents (Agent tool).**

Why: Each solution agent needs persistent context across two phases — (1) solve and propose, then (2) receive feedback and finalize. With standalone subagents, context is lost between invocations and "resume" is a lossy workaround. A real team keeps each agent's full research context alive throughout the review → feedback → revision → write cycle. This is especially important when the user requests corrections — the agent needs its complete solution context to revise efficiently.

Create an agent team with **one solution agent per question** (or per question group if the user specified).

```
TeamCreate: exam-solutions-{exam-name}
```

**Team structure:**
- **You (orchestrator):** Parse exam, clarify with user, dispatch agents, review solutions, write the overview document
- **N solution agents** (one per question): Research, solve, propose solution, then write the per-question markdown file after approval

## Phase 4: Agent Dispatch

Spawn all solution agents in parallel using `SendMessage` with the team name and `run_in_background: true`.

Each agent receives the full prompt from the [Solution Agent Template](#solution-agent-template) below, customized with:
- The specific question text (full, verbatim)
- Sub-questions and their individual point values
- The user's point distribution strategy
- The exam language
- The exam topic/course context
- The output directory and the agent's target filename
- Any special instructions from the user for this question

**Dispatch all agents simultaneously** — they work in parallel and send their summaries back via SendMessage when done with Phase 1.

## Phase 5: Review & Approve

Each agent follows a two-phase workflow: **solve first, then write the markdown file after orchestrator + user approval.**

When an agent sends its proposed solution summary via SendMessage:

1. **Present to the user** with a concise summary:
   - Question number and topic
   - Proposed model answer (key points)
   - Point distribution rubric
   - Any alternative acceptable answers noted
   - Confidence assessment (is the agent sure about the solution?)

2. **User review:**
   - If the user approves: send confirmation to the agent via SendMessage to proceed to writing the markdown file
   - If corrections needed: send specific feedback via SendMessage — the agent revises using its full research context (this is why real teams matter)
   - Batch multiple question reviews when agents finish close together

3. **After approval:** The agent writes its per-question markdown file and sends back the relative path via SendMessage

4. **Collect file paths** for the overview document

**Why agents write directly:** Avoids transferring full solution content through orchestrator context. The agent has the complete solution — let it write directly after approval.

**Why real teams, not subagents:** The review → feedback → write cycle requires agents to maintain their full research and solution context. With SendMessage, the orchestrator can send corrections and the agent revises in-place with everything still in memory. With standalone subagents, resuming loses context momentum and makes iterative feedback clunky.

## Phase 6: Overview Document

Once all agents have written their per-question files, write the **overview document** at `<output_dir>/README.md`.

**Overview structure (markdown).** Labels translate to the exam's language at write time:

```markdown
# Solution Key — [Exam Title]

- **Course:** [Course name]
- **Date:** [Date]
- **Location:** [Room/Location]
- **Time:** [Start–End time]
- **Duration:** [Duration]
- **Institute:** [Institute name]
- **Instructor:** [If known]
- **Allowed materials:** [If specified]
- **Total points:** [X]

---

## Overview

- **Question 1** (Y points) — [Topic](./question-01.md) — _Brief topic summary_
- **Question 2** (Y points) — [Topic](./question-02.md) — _Brief topic summary_
- ...

---

_Generated by the exam-solutions skill._
```

## Phase 7: Cleanup

1. Shut down all agents
2. Clean up team resources
3. Present final summary to the user:
   - Path to the overview document
   - List of all question files
   - Any questions that need follow-up attention

---

## Solution Agent Template

Below is the template for each solution agent's prompt. Replace `{{placeholders}}` with actual values.

```
You are an exam solution specialist on a team creating a correction template for a university exam. Your job is to solve ONE specific exam question thoroughly and accurately, then write a polished solution markdown file.

## Your Question

**Exam:** {{EXAM_TITLE}}
**Course:** {{COURSE_NAME}}
**Language:** {{LANGUAGE}} — Write your entire solution in this language.

**Question {{QUESTION_NUMBER}}:** ({{TOTAL_POINTS}} points)
{{FULL_QUESTION_TEXT}}

**Sub-questions and points:**
{{SUB_QUESTIONS_WITH_POINTS}}

**Point distribution strategy:** {{POINT_DISTRIBUTION_STRATEGY}}

**Special instructions:** {{SPECIAL_INSTRUCTIONS_OR_NONE}}

## Output Target

- **Output directory:** {{OUTPUT_DIR}}
- **Filename:** `question-{{QUESTION_NUMBER_PADDED}}.md`

## Your Workflow

You have TWO phases: **solve**, then **write the markdown file** (after orchestrator approval).

### PHASE 1: Research & Solve

#### Step 1: Understand the Question
- Parse the question carefully — what exactly is being asked?
- Identify the topic area, required concepts, and expected depth
- Note the point values — they signal expected answer length and detail

#### Step 2: Research (if needed)
- For standard textbook concepts: your training knowledge is likely sufficient (~90% of exam questions)
- For specific formulas, constants, reaction mechanisms: verify via web search
- For cutting-edge or highly specialized topics: search for papers or authoritative sources
- For chemistry: verify IUPAC names, reaction mechanisms, thermodynamic values
- For math: verify formulas, derivations, boundary conditions
- Always verify numerical answers and units

#### Step 3: Solve Each Sub-Question
For each sub-question, produce:

**a) Model Answer**
The ideal student answer that earns full points. Write it as a student would — clear, structured, showing the work/reasoning expected at this level.

**b) Grading Rubric**
Point-by-point breakdown of how to award marks:
- List each concept/step that earns points
- Specify partial credit rules (e.g., "correct approach but wrong result: -1 point")
- Point granularity must match the strategy: fewer total points = more granular rubric per point
- Example for a 3-point question: "1P: correct formula | 1P: correct substitution | 1P: correct result with units"
- Example for a 15-point question: "5P: derivation of equation | 5P: application to given system | 5P: interpretation of results"

**c) Acceptable Alternatives**
Concise notes on which alternative approaches or formulations also earn full credit. Do NOT write verbose alternative solutions — just note which key concepts must be present.
- Example: "Also accept: Henderson–Hasselbalch instead of full derivation, as long as pH is correct"
- Example: "Either SN1 or SN2 mechanism accepted, provided the justification is consistent"

#### Step 4: Self-Check
- Verify calculations and numerical results
- Check that point rubric sums to the correct total
- Ensure the solution matches the expected depth for the course level
- Confirm language matches the exam language throughout

#### Step 5: Send Summary to Orchestrator

Send a concise summary including:
- Question number and topic
- Key points of the model answer (not the full solution)
- Point distribution rubric overview
- Any uncertainties or questions about the expected answer
- Confirmation that the full solution is ready

**Do NOT send the complete solution text.** The orchestrator needs enough to verify correctness and present to the user. Wait for confirmation before Phase 2.

### PHASE 2: Write the Markdown File

**Only proceed after the orchestrator confirms your solution is approved.**

Write to `{{OUTPUT_DIR}}/question-{{QUESTION_NUMBER_PADDED}}.md` using the structure below. Use standard markdown — no platform-specific syntax.

**Required document structure** (English labels shown — translate ALL labels and headings to {{LANGUAGE}} when writing):

```markdown
# Question {{QUESTION_NUMBER}} ({{TOTAL_POINTS}} points)

> Full verbatim question text (or key excerpt if very long).

---

## a) [Sub-question topic] (X points)

### Model Answer

[Solution content — paragraphs, bullet lists, numbered steps as appropriate]
[For chemistry: render structures inline as SMILES in fenced code blocks or as image references]
[For math: show derivation steps clearly using LaTeX in `$...$` or `$$...$$`]

### Grading Rubric

- **X P:** [Concept/step that earns these points]
- **X P:** [Next concept/step]
- _Partial credit:_ [rules]

### Acceptable Alternatives

_[Brief notes on acceptable alternative answers]_

---

(repeat per sub-question)

---

**Total: {{TOTAL_POINTS}} points**
```

**Critical formatting rules:**
- Write EVERYTHING in the exam language ({{LANGUAGE}}), including the section headings and labels shown above (`Question`, `Model Answer`, `Grading Rubric`, `Acceptable Alternatives`, `Partial credit`, `Total`, `points`).
- Use **bold** for point values in rubric items
- Use horizontal rules (`---`) between sub-questions
- Use blockquotes for the verbatim question text
- For chemistry structures, use SMILES in fenced code blocks (e.g. `` ```smiles\nCCO\n``` ``) or paths to image files
- For equations, use LaTeX delimiters: `$inline$` or `$$display$$`

#### Step 2c: Report Back

After writing the file, send the orchestrator:
- The relative path to the file (e.g. `question-03.md`)
- Confirmation that writing is complete

Be thorough and accurate. A correction template must be reliable — instructors use it to grade dozens of exams consistently.
```

---

## Orchestrator Checklist

- [ ] Extracted exam from .docx (Phase 1)
- [ ] Parsed all questions, sub-questions, and point values
- [ ] Detected exam language
- [ ] Presented structure to user and clarified ambiguities (Phase 2)
- [ ] Confirmed point distribution strategy with user
- [ ] Confirmed scope (which questions to solve)
- [ ] Confirmed output directory
- [ ] Created team and dispatched agents (Phases 3-4)
- [ ] Reviewed each agent's proposed solution (Phase 5)
- [ ] Presented solutions to user for approval
- [ ] Agents wrote approved solution markdown files
- [ ] Collected all file paths
- [ ] Wrote overview README.md with exam metadata and per-question links (Phase 6)
- [ ] Cleaned up team (Phase 7)
- [ ] Presented final summary to user

## Design Principles

**Solution depth:** Each solution serves dual purpose — both an ideal student answer (what earns full points) AND an instructor reference (with rubric and acceptable alternatives). Alternatives are noted concisely (which concepts must be present), not as verbose rewrites.

**Point-proportional detail:** The rubric granularity scales inversely with points per question. A 2-point question needs per-point concept mapping. A 20-point question can have coarser groupings (5P blocks). The exact strategy is confirmed with the user before dispatch.

**Research calibration:** ~90% of exam questions should be answerable from model knowledge. Web search for verification of formulas, constants, nomenclature. For cutting-edge or highly specialized topics, agents should search for papers and authoritative sources. Research depth is proportional to question specificity.

**Language:** Auto-detected from exam text. Everything — model answers, rubrics, alternatives, section headers — is written in the exam language. If detection is uncertain, ask the user.

**Exam metadata in overview:** The overview document preserves all header information from the exam (course, date, location, time, institute, instructor, allowed materials, total points) as a complete reference.
