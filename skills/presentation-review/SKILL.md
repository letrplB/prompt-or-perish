---
name: presentation-review
description: Evaluate and refine a presentation deck through an orchestrated 4-pass workflow — diagnose the red line, manifest a concrete plan in a side-by-side MD file, dispatch topical subagents to draft per-section patch manifests, then serially apply and validate. Grounded in Doumont's three laws with additions from Duarte and Reynolds. Focuses on content and structure, not visual style. Use when the user says "/presentation-review", "review this deck", "critique these slides", "refine this presentation", or provides an HTML deck and asks for feedback.
argument-hint: [path to deck.html] [--audience "..."] [--thesis "..."] [--focus pass1|pass2|pass3|pass4|all]
---

# Presentation Review

Diagnose, plan, and refine a slide deck through a 4-pass workflow. Output a persistent review document next to the deck; dispatch subagents to deep-dive topical sections in parallel; apply changes serially from structured patch manifests.

**This skill is about content and structure.** It does not critique visual style, color palette, typography, or layout — assume those are intentional. If a style choice is breaking communication (type illegibly small, visual-speech competition), flag it; otherwise, don't.

## When to Use

Invoke when the user:
- Says `/presentation-review` with a path
- Provides an HTML slide deck and asks for review, critique, or refinement
- Says "tighten this deck", "sharpen the story", "is the red line clear?"
- Wants Doumont-style feedback with concrete rewrites

## Inputs

**Required:**
- Path to an HTML deck: a single file, or a deck folder whose lecture/talk file loads separate scene or style modules. The slide markup, notes and numbering conventions are detected in Pass 1 (§1.0), not assumed.

**Strongly recommended — ASK before proceeding if missing:**
- **Audience** — specific. "A 20-person chemistry group at Uni X" beats "scientists".
- **Thesis** — if the audience remembers one thing, what?
- **Duration** — affects slide count discipline.

If audience or thesis is missing, ask once:
> *"Before I review: (1) who exactly is this for, and (2) if they remember one thing, what should it be?"*

Do not accept "general audience"; push back and ask for specifics.

---

# The 4-Pass Workflow

```
  Pass 1 · Diagnose       (main thread, solo)
  Pass 2 · Manifest       (main thread, solo)      → writes REVIEW.md
  Pass 3 · Execute        (parallel subagents)     → each writes manifest into REVIEW.md
  Pass 4 · Integrate      (main thread, serial)    → applies manifests, validates
```

The persistent artifact is **`{deckname}.REVIEW.md`** — created next to the HTML. It survives across sessions; a partial review can resume from any pass.

---

## Pass 1 — Diagnose

Solo, main thread. No subagents yet. Goal: understand the deck whole.

### 1.0 · Detect the deck's conventions
Before parsing, read the deck's head, the first few slides and any linked deck config or engine docs (`deck.json`, README, an authoring guide). Record the answers at the top of §1 as **Deck conventions**. Every later pass, every subagent prompt and every manifest follows them:

- **Slide element**: the selector that marks one slide (e.g. `section.slide`, a web component's children)
- **Title**: where a slide's title lives (a heading element, a `data-title` attribute, …)
- **Speaker notes**: a positional array (e.g. `<script id="speaker-notes">` JSON, index = slide order) **or** per-slide (e.g. a `data-notes` attribute, an `<aside class="notes">`). Positional notes need re-indexing after inserts/cuts; per-slide notes move with their slide.
- **Stable slide IDs**: present? (e.g. `data-id`). If the deck has a tool that mints them, new slides get theirs from that tool, never hand-written.
- **Section labels and numbering**: hard-coded (`§` spans, folios) or computed by the engine at runtime
- **Builds and scenes**: click steps (e.g. `data-step`) and any JS scene modules that draw slide content. Changing a scene's steps means editing that module, not just the HTML.
- **Files**: single file, or the slide file plus which modules it loads

See [Known deck conventions](#known-deck-conventions) for two common patterns. If a convention is unclear, ask the user once rather than guessing.

### 1.1 · Parse and inventory
Extract all slides. Build a table:

```
#  | §   | Group         | Title                              | Type          | Words  | SN
---|-----|---------------|------------------------------------|---------------|--------|----
01 | —   | —             | Cover                              | title         |   18   | ✓
02 | 01  | Primer        | A very expensive autocomplete      | text+diagram  |   65   | ✓
...
```

Columns: slide index, section label, group tag (usually top-right of header), slide title, primary content type (text / chart / table / diagram / quote / 2-col compare / list), approximate word count, speaker-note present.

### 1.2 · Red line extraction
List each slide's **distilled message** (one sentence each) in order. Read them as a paragraph. Answer:
- Does this read as a story or a ToC?
- What is the **implicit thesis** (the one sentence tying them all together)?
- Compare to the stated thesis from inputs. Mismatch = critical finding.

### 1.3 · Broad structural flags
Quick sweeps, not deep dives:
- **D8 · Section coherence** — do topical groups hold together?
- **D9 · Transition audit** — which adjacent-slide handoffs feel weak?
- **D14 · Closing audit** — does the close earn its weight or peter out?
- **Rhythm** — runs of >3 same-layout slides; absence of breathers.

### 1.4 · Write §1 of REVIEW.md

```markdown
# Review: {deck title}

_Reviewed by presentation-review skill. Audience: {audience}. Thesis target: {thesis}._

## §1 · Diagnosis

### Summary
One paragraph. Biggest strengths, biggest weaknesses, red line clarity.

### Red line — current
Implicit thesis: "..."
Per-slide message list (numbered, one line each):
```

Hand off to Pass 2 without asking for approval — Pass 2 builds on this, still no edits.

---

## Pass 2 — Manifest

Solo, main thread. Build the concrete plan from the diagnosis.

### 2.1 · Target structure
Decide the final shape. For each current slide, assign one of:
- **KEEP** — no change or only minor polish (handled by subagent)
- **REFINE** — significant rewrite needed
- **REORDER** — move to position X
- **MERGE with** slide Y
- **SPLIT into** N new slides
- **CUT** — remove entirely
- **NEW** — add a new slide in position X (with brief)

### 2.2 · Topical scoping
Divide the refined deck into **4–8 topical scopes**. Reuse the deck's existing group tags if they exist (e.g., Primer · Steering · Failure modes · Autonomy · Practice · Outlook · Close). Rules:
- Each scope is **contiguous** slides (to minimise renumbering conflicts)
- Each scope has **3–6 slides** (manageable for one agent; more = split)
- Each scope has a clear **theme** (a subagent needs to hold one idea, not a salad)

### 2.3 · Write §2 and §3 of REVIEW.md

```markdown
## §2 · Target Structure

(Before → After table or list. Show every slide's assigned action. New slides shown in their target position.)

## §3 · Agent Assignments

### Agent A — Foundations  [slides 02–03, § 01–02]
**Theme**: the mental model of what an LLM is and how reasoning sits on top.
**Goal after refinement**: two slides that make the audience able to name the base mechanism and the scratchpad extension without reading anything.
**Slides in scope**: 02, 03
**Known issues (from Pass 1)**:
- Slide 02 title is a topic, not a message.
- Slide 03 scratchpad example is niche (SN2/E2) for mixed audience.
**Brief**:
- Rewrite titles as messages.
- Verify the System-1/System-2 analogy lands for the stated audience.
- Tighten body copy; cut anything not serving the message.
- Deliver a patch manifest at the end of §4 under "Agent A".

### Agent B — Steering  [slides 04–08, § 03–07]
...

### Agent C — Failure modes  [slides 09–12, § 08–11]
...
```

### 2.4 · Present the plan and PAUSE
Show the user §1–§3 of the REVIEW.md. Ask:
> *"Here's the plan. Proceed to Pass 3 (dispatch subagents to draft the changes)? Or adjust scopes first?"*

Do not launch subagents until confirmed.

---

## Pass 3 — Execute

Parallel subagents. One per topical scope. All invoked in a **single message with multiple Agent tool calls** so they run concurrently.

### 3.1 · Subagent prompt template

Each subagent receives a self-contained prompt (it has no conversation context):

```
You are refining a topical section of an HTML slide deck.

DECK: {absolute path to HTML}
REVIEW PLAN: {absolute path to REVIEW.md}
YOUR SCOPE: slides {list} — {theme}
AUDIENCE: {audience}
DECK THESIS: {thesis}
DECK CONVENTIONS: {the Deck conventions block from §1: slide element, title,
  notes, stable IDs, numbering, builds/scenes, files}

Your task:
1. Read the deck file. Locate your assigned slides.
2. Read §3 of the REVIEW.md for your agent's brief.
3. Run these per-slide diagnostics on every slide in your scope:
   - D1 one-sentence message test
   - D2 title-as-message check
   - D3 3-second glance test
   - D4 signal/noise audit
   - D5 text density
   - D6 imprecision audit
   - D7 visual-speech competition
4. For any new slides in your scope, draft full HTML using the same markup
   and class conventions as the surrounding deck (DECK CONVENTIONS): notes
   where the deck keeps them, no hand-written stable IDs. Match the existing
   editorial style.
5. Produce a PATCH MANIFEST (see format below). DO NOT EDIT THE HTML.

Write your manifest into REVIEW.md under the heading "### Agent X manifest"
in §4. Follow the YAML block format exactly.

Style guardrails:
- Do not redesign the visual style. Keep class names, typography choices,
  color usage consistent with the deck's existing aesthetic.
- Match the tone register of the rest of the deck (check a few slides
  outside your scope to calibrate).
- Every proposed rewrite must be concrete — no "make clearer".
- When splitting or merging, spell out the final slide messages.

Do not modify the HTML. Manifests only.
```

Subagent type: `general-purpose` (needs Read, Write — to REVIEW.md only — and maybe WebSearch for fact-checks).

### 3.2 · Patch manifest format (enforced)

Each subagent writes one block to §4 of REVIEW.md:

````markdown
### Agent B manifest — Steering (slides 04–08)

```yaml
agent: "B — Steering"
scope_slides: [04, 05, 06, 07, 08]

# Existing-slide edits. Each edit must be applyable by a single Edit tool call.
edits:
  - slide: 07
    type: title
    selector: 'slide 07, <div class="title"> first child'
    before: |
      Most chemistry problems<br/>are <span class="accent">prompt + RAG</span> problems.
    after: |
      Prompt and retrieve first. <span class="accent">Fine-tune last</span>.
    reason: "Title-as-message; tighter phrasing; verdict now in title."

  - slide: 04
    type: body
    selector: 'slide 04, .body[max-width:560px] paragraph 1'
    before: "A rule of thumb, not a law. Resist fine-tuning until..."
    after: "..."
    reason: "Soft opener dilutes; lead with the operational rule."

# Net-new slides (full HTML). Position relative to existing slides.
new_slides:
  - position: after_slide_05
    label: "Context Accumulation"
    group: "Steering"
    section_number: "§ 04"   # if known; orchestrator may reassign
    message: "The model has no memory — only a growing transcript."
    brief: "Introduce what goes into the context across turns, setting up context rot later."
    draft_html: |   # in the deck's own slide markup (see Deck conventions)
      <section class="slide light" data-label="Context Accumulation">
        ...
      </section>
    speaker_note: "..."

# Restructuring flags for the orchestrator
restructure:
  - action: reorder
    from_slide: 09
    to_position: before_slide_07
    reason: "Sycophancy fits Steering arc; Context Rot needs agent concept first."
  - action: merge
    slides: [11, 12]
    into_title: "..."
    reason: "..."

# Cross-cutting concerns the orchestrator must resolve
conflicts_expected:
  - "This scope inserts 1 new slide; downstream § labels shift by +1."
  - "Positional notes only: speaker notes array index shifts by +1 for all later entries."
```
````

### 3.3 · Running the agents
Launch all topical agents in parallel:

```
Agent(description="Foundations review", subagent_type="general-purpose", prompt=<template-for-A>)
Agent(description="Steering review",    subagent_type="general-purpose", prompt=<template-for-B>)
Agent(description="Failure modes review",subagent_type="general-purpose", prompt=<template-for-C>)
...
```

Send in one message so they execute concurrently. Wait for all to finish before Pass 4.

---

## Pass 4 — Integrate

Main thread, serial. No new subagents.

### 4.1 · Read back
Re-read REVIEW.md §4 to collect every agent's manifest.

### 4.2 · Conflict detection
Walk every manifest and flag:
- **Same slide** edited by two agents (shouldn't happen if scopes are disjoint; if it does, ask user)
- **Adjacent inserts** that collide on position (e.g., "after_slide_05" from both A and B)
- **Speaker-note indices** (positional notes only) — any new slide insertion shifts all downstream indices; multiple insertions compound
- **Global renumber** (hard-coded numbering only) — sum inserts and cuts to compute final `§` labels and folio counts
- **Scene modules** — two agents changing slides that share one scene module, or a step change that the module must follow

### 4.3 · Resolve, plan the sequence
For a conflict-free plan, compute an **application order**:

1. Deletions (cuts) first — reduces index math.
2. In-place edits (titles, body copy, speaker notes) — each an independent Edit.
3. Reorders — treat as cut + insert.
4. Merges / splits — edit in place, then adjust siblings.
5. New slide insertions — bottom-up (highest-numbered position first) to avoid cascading renumber. If the deck uses stable slide IDs, mint them for new slides with the deck's own tool.
6. Global renumber pass — only if numbering is hard-coded: `§` labels and folios across the whole deck in one Python/Bash script.
7. Positional speaker notes only — rebuild the array to match the final slide count. Per-slide notes need no step.

Each step is a single Edit (or one Bash command for the renumber script or ID tool). Nothing parallel.

### 4.4 · Apply
Execute the sequence. After each meaningful group of edits, re-grep for the slide element (and § labels, if hard-coded) to confirm state.

### 4.5 · Validation pass
After all edits, run:
- **Structural sanity**: slide count matches the plan; where applicable, `§` label and folio sequences are continuous, the positional notes count equals the slide count, and stable IDs are unique.
- **Render check**: if the deck has a QA or preview tool, run it; otherwise open the deck in a browser and step through every touched slide, including its builds.
- **Quick D1–D2 sweep**: for every touched slide, confirm the new title is a message (or intentionally not) and the slide has one distillable message.
- **Red line regression**: re-list new messages; does the arc still read as a story?

### 4.6 · Write §5 of REVIEW.md

```markdown
## §5 · Applied Changes

{N} slides edited. {M} new slides. {K} reorders.
Section count: before {X} → after {Y}.

### Change log
- Slide 07 title: rewritten.
- Slides 09–10: swapped.
- Slide 11: new (Context Accumulation).
- ...

### Validation
- Section labels: sequential ✓ (if hard-coded)
- Folios: sequential ✓ (if hard-coded)
- Speaker notes: {count} aligned with {count} slides ✓ (if positional)
- Stable IDs: unique, new ones minted by the deck's tool ✓ (if used)
- Render check: {tool or browser} ✓
- D1 sweep: {N/N} slides have clear single messages.

### Red line after refinement
"..." (new implicit thesis, per-slide message list)
```

Tell the user what changed, offer a targeted next pass if anything is weak.

---

# Diagnostic Reference (D1–D18)

Shared across Pass 1 (broad) and Pass 3 (per-agent deep dive).

## Per-slide — Message (D1–D7)

**D1 · One-sentence test.** State the slide's message in one complete sentence. If you can't, the slide doesn't have one yet.

**D2 · Title-as-message.** ✓ full-sentence claim · ⚠ topic-phrase pointing at a claim · ✗ bare topic. ⚠ acceptable only if paired with a visible claim (eyebrow / lede); ✗ is a failure.

**D3 · 3-second glance.** What does a reader get in 3 seconds? If the answer is "text", too dense. (Duarte: glance media.)

**D4 · Signal/noise audit.** Every element serves the message or it's noise. Enumerate each element; mark signal / noise.

**D5 · Text density.** Soft limits: title ≤ 15 words; body ≤ 40 words/column; single blocks ≤ 60 words unless quoted; tables ≤ 4 × 3 before compounding.

**D6 · Imprecision audit.** Flag: soft openers ("It's worth noting..."), vague quantifiers ("many", "often"), unearned intensifiers ("dramatically" with no number), abstract nouns instead of verbs, passive where active is sharper. Propose sharper rewrites.

**D7 · Visual-speech integration.** If projected while the speaker talks, does the slide compete (audience reads + listens → neither lands) or complement (image + speech)?

## Cross-slide — Structure (D8–D14)

**D8 · Section coherence.** Do slides within a group share a real theme, or is it a grab-bag? Could a slide move between groups equally well?

**D9 · Transition audit.** For each adjacent pair: what question does slide N raise that N+1 answers? If none, weak transition.

**D10 · Forward-reference audit.** Concepts referenced before introduction. Explicit forward-ref ("more on agents later") is good; silent is bad.

**D11 · Gap audit.** Concepts used without introduction.

**D12 · Redundancy audit.** Same ground twice. Deliberate reinforcement = good; accidental repetition = merge candidate.

**D13 · Opening audit (slides 1–3).** Promise what the deck delivers? Friction in first 30s? Cover informative without clutter?

**D14 · Closing audit.** Earns weight or peters out? Single memorable take-home? Call-to-action matches goal?

## Whole-deck — Story (D15–D18)

**D15 · Red line.** Message list reads as story or ToC? State implicit thesis. Compare to stated thesis.

**D16 · Rhythm.** Same-layout runs > 3 = monotony. Any breathers (pullquote, full-bleed visual, single-line slide)? Tonal variety (surprise, softness, punch)?

**D17 · Audience fit.** Against stated audience: undefined jargon; over-explained basics; inconsistent rhetorical register.

**D18 · Takeaway test.** Close the file. Write what they'll remember in a week. ≤ 3 items (Doumont's rule of three). Zero = no take-home; >3 = demote some.

---

# Principles — condensed reference

## Doumont — three laws
1. **Adapt to audience.** Same message, different forms for different people. Mismatch = wasted slide.
2. **Maximize signal-to-noise.** Every element helps. Noise dilutes signal even when it's pretty.
3. **Effective redundancy.** Repeat key ideas in different modes (visual + verbal; section headers + running heads; preview + payoff). Not the same words — different angles on the same point.

## Doumont — slide-specific
- One message per slide. One slide per message.
- Title = the message, as a full sentence.
- Text + speech compete in the audience's head. Prefer image + speech.
- Rule of three: ≤ 3 memorable items.
- Legibility: print 6 per letter page; if you can't read it, type is too small.

## MIT CommLab
- Titles are takeaways, not topics. *"M Dwarfs are the Most Common Type of Star"*, not *"Distribution of Stars"*.
- Prime with context before data — schematic before the chart.
- Phased reveal (animations) to prevent cognitive overload.
- Limit palette: base + one accent. Color codes (red=hot), not decoration.
- Strategic repetition: a figure in outline, body, conclusion.

## Duarte / Reynolds
- Slides are **glance media**. 3-second test.
- Story structure: empathy → contrast → variety. Introduce, complicate, resolve.
- Simplicity = clarity, directness, essentialness. Beauty is elimination.
- Spoken word carries argument and emotion; slide supports.

## When these rules conflict with the deck's existing style
Respect the style. Critique content and structure, not chosen aesthetic. The skill's job is to sharpen the message through the given style, not replace the style.

---

# Operational notes

## Parallel vs serial (deliberate design)
- **Parallel** is used in Pass 3 (analysis and drafting). Subagents work on disjoint scopes; they write to different headings in REVIEW.md. No file collision.
- **Serial** is used in Pass 4 (application). All writes to the HTML deck go through the orchestrator, one Edit at a time.

Subagents **never** edit the HTML. They only write manifests into REVIEW.md. This is the invariant that makes the workflow safe.

## The REVIEW.md artifact
- Persists next to the deck as `{deckname}.REVIEW.md`.
- Survives sessions. A user can say "continue the review from Pass 3" and the skill can resume.
- Sections: §1 Diagnosis · §2 Target Structure · §3 Agent Assignments · §4 Patch Manifests · §5 Applied Changes.
- Each section is appended; nothing is overwritten. The file tells the story of the review itself.

## Pause points (where the user steers)
- Between Pass 2 and Pass 3: show the plan, confirm scopes.
- Between Pass 3 and Pass 4: show the aggregated manifests, let user cherry-pick which changes to apply (or apply all).
- After Pass 4: show the change log and validation, offer targeted follow-up.

## Known deck conventions
Two patterns this skill has been used on. Treat them as examples; §1.0 decides what the deck in front of you does.

| | Single-file deck | Scene-engine deck |
|---|---|---|
| Slide | one `<section>` per slide, often inside a `<deck-stage>` web component that auto-counts children | `section.slide` in a lecture/talk HTML file |
| Title / label | heading in the slide; `data-label` gives a short semantic label | `data-title` (also shown in the footer), optional `data-section` |
| Notes | `<script type="application/json" id="speaker-notes">`: JSON array, index aligned with slide order | per-slide `data-notes`; optional `data-bridge` line to the next slide |
| Stable IDs | none | `data-id`, minted by the engine's ID tool, never hand-edited |
| Numbering | `§` labels in `<span class="sect">`, folios in `.foot` spans | computed at runtime |
| Builds | usually none or CSS-only | `data-step` / `data-until` on elements; scene functions in separate JS modules draw per step |
| Render check | open in a browser | the engine's QA tool (screenshots every slide and step) |
