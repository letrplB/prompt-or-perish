---
name: lecture-analysis
description: Analyze a lecture PDF end-to-end through 5 stackable phases — overview, full ingestion (text + page renders), parallel topical detail extraction with vision, didactic review, and per-topic question banks. Produces a sidecar `_analysis/` directory next to the PDF that mirrors slide content in agent-accessible markdown. Use when the user provides a lecture PDF and asks to analyze, summarize, critique didactically, or generate study questions.
argument-hint: [path to lecture.pdf] [--phase 1|2|3|4|5|all] [--language auto|de|en] [--topics N]
user-invocable: true
---

# Lecture Analysis

Five-phase pipeline for taking a lecture slide PDF apart and putting it back together as durable, agent-readable artifacts:

1. **Overview** — light skim, persisted summary + topic plan
2. **Ingestion** — render every page, dump per-page text (the deterministic substrate for everything after)
3. **Detail** — parallel topic agents do a two-pass (text + vision) extraction into slide-faithful mirror docs
4. **Didactic review** — feedback on topical order, image use, gaps, pedagogy
5. **Questions** — parallel topic agents generate a question bank (10 per topic, mixed difficulty)

Optional **Phase 6 — PDF export** (deterministic, no LLM): render the didactic review and question banks to clean modern PDFs for circulation. See "Phase 6" below.

Each phase writes to a sidecar directory next to the PDF and updates a `manifest.json`. Phases are resumable: re-invoking the skill picks up the next pending phase. The user can also target a single phase with `--phase N`.

## When to Use

Invoke when the user:
- Provides a lecture PDF and asks for an overview, deep analysis, didactic critique, or study questions
- Says `/lecture-analysis <path>` or `lecture-analysis <path>`
- Wants to make a slide deck queryable by other agents (e.g., a downstream teaching-assistant agent)

## Inputs

**Required:**
- Path to a lecture PDF (PowerPoint exports work well; embedded fonts and high image count are fine)

**Optional:**
- `--phase 1|2|3|4|5|all` — only run a specific phase. Default `all`, with confirmation pauses.
- `--language auto|de|en` — output language for overview/review/questions (auto-detects from slide text)
- `--topics N` — target number of topics for the topic plan. Default: derived from lecture length and TOC slide.
- `--dpi 144` — page render DPI for Phase 2. Default 144 (1920×1080 for a 16:9 PowerPoint slide). **Hard cap: do not exceed 150 DPI.** Anthropic's vision API rejects any image > 2000 px on a side in a many-image request, and a 16:9 slide at >150 DPI exceeds that on the long edge. 144 DPI gives a comfortable safety margin and still resolves graph axis labels, phase-diagram regions, and structure overlays clearly. If you genuinely need higher detail for a specific subset, run a one-off rerender of those pages at higher DPI and feed them to a single-image request.

## Sidecar Layout

```
<lecture-folder>/_analysis/
├── manifest.json                   phase status, topic plan, paths
├── 00_ingest/
│   ├── pages/
│   │   ├── page-001.txt            per-page text (via pymupdf)
│   │   ├── page-001.png            full-page render (Phase 2 only)
│   │   └── …
│   ├── outline.json                PDF bookmarks/TOC
│   └── manifest.json               ingestion stats
├── 01_overview.md                  Phase 1 output (overview + topic plan table)
├── 02_topics/
│   ├── topic-01-<slug>.md          slide-mirror doc for topic 1
│   └── …
├── 03_didactic-review.md           Phase 4 output
└── 04_questions/
    ├── topic-01-<slug>.questions.md
    └── …
```

Why a sidecar of local markdown files: it's fast, diff-friendly, and plugs straight into any agent context. Exporting to a knowledge platform later is straightforward — the artifacts are plain markdown.

## Top-Level Manifest

`<sidecar>/manifest.json` is the source of truth for resume. Schema:

```json
{
  "pdf": "<absolute path>",
  "language": "de",
  "phases": {
    "1_overview":   {"status": "done|pending|failed", "artifact": "01_overview.md"},
    "2_ingestion":  {"status": "done|pending|failed", "render_dpi": 144},
    "3_detail":     {"status": "done|pending|failed", "agents": {...}},
    "4_review":     {"status": "done|pending|failed", "artifact": "03_didactic-review.md"},
    "5_questions":  {"status": "done|pending|failed", "agents": {...}}
  },
  "topics": [
    {"id": 1, "slug": "atombau-pse", "title": "Atombau & PSE",
     "pages": [1, 35], "n_slides": 35, "brief": "...",
     "detail_path": "02_topics/topic-01-atombau-pse.md",
     "questions_path": "04_questions/topic-01-atombau-pse.questions.md"}
  ]
}
```

On every invocation, read the manifest first. If absent, initialize it from the PDF metadata.

---

# Phase 1 — Overview

Solo, main thread. No subagents. Goal: produce a persistent overview and a topic plan the user signs off on.

## 1.1 — Light ingest

Run the ingest script in `--light` mode (text + outline only, no page renders — fast):

```bash
.venv/bin/python .claude/skills/lecture-analysis/scripts/ingest_pdf.py \
  "<pdf>" "<sidecar>" --light
```

This populates `00_ingest/pages/page-NNN.txt`, `00_ingest/outline.json`, and `00_ingest/manifest.json`. Idempotent — re-running is cheap.

**Use a project-local `.venv`** rather than installing Python packages globally. If `pypdf` or `pymupdf` are missing, install via `.venv/bin/pip install pypdf pymupdf`.

## 1.2 — Read the lecture as a whole

- Read the first ~5 pages of text (cover, TOC slide, intro outline) — these typically declare the lecture's structure.
- Read the outline — for PowerPoint exports it's often per-slide (one entry per page in the export's language) and useless for chapter detection. If it has real headings, use them.
- **Skim every slide's full text** (not just titles) by reading every `page-NNN.txt`. The cost is small (a few hundred KB total) and you need this signal to find the topic boundaries — section divider slides are sparse-text, big-title pages and only show up if you scan them all.

Detect language from the cover and TOC text. Default `de` if German is dominant; otherwise match the dominant language. If `--language` was specified, use that.

## 1.3 — Derive a topic plan

Group contiguous slide ranges into topics. Rules:

- **Contiguous only** — a topic is `[start_page, end_page]`. No skipping.
- **Match the lecture's own granularity.** For an inorganic-chemistry semester lecture covering the elements (typical title: "Chemistry of the Elements" or "Inorganic Chemistry I"), the natural unit is **one topic per main group of the periodic table** (groups 1, 2, 13, 14, 15, 16, 17, 18) plus distinct topics for atomic structure / periodic trends, hydrogen, transition metals (likely sub-split into d-block groups or a few thematic chunks), and coordination chemistry. Expect **12–20 topics** for a 400-page elements lecture, not 8–10.
- **Find topic boundaries by detecting section dividers.** Pages with very sparse text (≤ 20 words) and a single large title line are almost certainly section dividers. List them; each one is a strong topic-boundary candidate.
- **Each topic has a single theme** that an agent can hold in one head. "Gruppe 14: Kohlenstoffgruppe" is right; "elements" is too broad; "carbon allotropes" is too narrow as its own top-level topic — that's a slide-level subsection inside the Group-14 mirror doc.
- **Subsections within a topic** (e.g. element-by-element treatments inside one main group) live as `### Slide N` sections in the mirror doc — they don't need to be separate topics. Topic granularity = "agent reads it in one go"; subsection granularity = "section heading inside that doc".
- **Slug** = lowercase ASCII, hyphenated, ≤ 30 chars. e.g. `atombau-pse`, `gruppe-1-alkalimetalle`, `gruppe-17-halogene`.

If the user passed `--topics N`, target that count instead.

## 1.4 — Write `01_overview.md`

```markdown
# Lecture Overview — <Title>

**Source**: <relative path>
**Author**: <from PDF metadata>
**Pages**: <N>   ·   **Embedded image objects**: <total>
**Language**: <detected>
**Generated**: <ISO date>

## Course thesis (implicit)
One sentence — what is this lecture trying to teach overall?

## Structure as declared
Quote the TOC slide verbatim if present; otherwise note "no explicit TOC slide".

## Topic plan

| # | Topic | Slug | Pages | Slides | Brief |
|---|-------|------|-------|--------|-------|
| 1 | Atombau & PSE | atombau-pse | 1–35 | 35 | Atomic structure, periodic trends, electron configuration |
| 2 | … | … | … | … | … |

## Notes for downstream phases
- Anything Phase 3/4 should pay attention to (e.g., section divider slide style, language switches, heavy use of specific representation).
- Any pages that look anomalous (broken layout, missing content).
```

Update `manifest.json`: set `phases.1_overview.status = "done"` and write `topics`.

## 1.5 — Pause and confirm

Show the topic plan to the user:

> "Here's the topic plan. Adjust any boundaries / merges / splits before I run the heavy ingestion and detail extraction? Reply 'go' to proceed."

Do **not** start Phase 2 until confirmed (or `--phase` was specified to skip Phase 1).

---

# Phase 2 — Ingestion

Solo, main thread. Deterministic, no LLM. Renders every page so vision agents can read them in Phase 3.

## 2.1 — Full render

```bash
.venv/bin/python .claude/skills/lecture-analysis/scripts/ingest_pdf.py \
  "<pdf>" "<sidecar>" --dpi <dpi>
```

For a ~400-page slide deck at 144 DPI, expect ~50–150 MB of PNGs and a couple of minutes wall time. Run it and let it finish.

## 2.2 — Verify

After the script exits, check:
- Every `topics[i].pages` range has matching renders (`page-NNN.png` exists for every page in range)
- `00_ingest/manifest.json` `total_image_objects` is non-zero (sanity: this is a slide deck with visuals)

If any pages failed to render, re-run with `--force` on the affected range or report to the user.

Update `manifest.json`: `phases.2_ingestion.status = "done"`, store `render_dpi`.

No pause. Phase 3 starts immediately.

---

# Phase 3 — Detail (parallel topical agents, two-pass extraction)

Parallel subagents — one per topic. Each agent reads the per-page text **and** the per-page renders for its assigned range, then produces a slide-faithful mirror document.

This is the heart of the skill. The output is what other agents will read instead of the PDF.

## 3.1 — Dispatch

For every topic in `manifest.topics`, spawn one `general-purpose` subagent in parallel (single message, multiple Agent tool calls):

```
Agent(
  description="Detail: <topic title>",
  subagent_type="general-purpose",
  prompt=<TOPIC_DETAIL_TEMPLATE filled in for this topic>
)
```

For lectures with > 8 topics, batch in groups of 8 (or whatever the harness allows comfortably) — but still in parallel within each batch.

## 3.2 — Topic Detail Agent prompt template

```
You are a lecture-analysis detail agent. Your job: read every slide in your assigned
page range and produce a slide-faithful mirror document.

LECTURE: <title>
LANGUAGE: <detected language>  — write your output in this language
YOUR TOPIC: <topic title> (#<id>)
YOUR PAGE RANGE: <start>–<end>  (<n> slides)
THEME: <brief>

INPUTS available on disk:
- Per-page text:    <sidecar>/00_ingest/pages/page-NNN.txt
- Per-page render:  <sidecar>/00_ingest/pages/page-NNN.png

OUTPUT FILE: <sidecar>/02_topics/topic-<id>-<slug>.md

# Two-pass extraction

PASS 1 — TEXT.  Read every page-NNN.txt in your range. For each slide build a draft
section using only the text:
- Slide number and PDF page
- Title (largest header line on the slide)
- Body bullets / paragraphs (preserve order; preserve scientific notation, units,
  formulas, IUPAC names verbatim)
- Tables, if present, transcribed as markdown tables
- Equations transcribed as LaTeX-in-backticks (e.g. `\\Delta H_f`) when math is present

PASS 2 — VISION.  Now READ the page-NNN.png for every slide in your range using the
Read tool (it accepts PNGs). For each slide augment Pass 1 with:
- A description of every meaningful visual element: figure / diagram / structure /
  graph / photo / table-as-image / arrow-flow.
- For each visual: WHAT it shows AND WHAT MESSAGE it conveys for the slide's argument.
  ("Periodic table coloured by electronegativity" — what; "trend increases →↑ across
  periods, ↓ down groups" — message.)
- Chemistry structures: capture the molecule, ions, or formula unit. If a SMILES is
  obvious, give it; otherwise describe in IUPAC-friendly prose.
- Reaction schemes: capture reactants → products and any conditions/labels.
- Numerical/graph axes and the take-home from any chart.

If a slide is purely a section divider, mark it as such and move on — single line.
If a slide is identical to a prior one (re-shown for emphasis), note "= slide N".

# Output format

Write exactly this structure to <output file>:

    # Topic <id>: <title> (p.<start>–<end>)

    > <brief>  ·  <n> slides  ·  source: <pdf basename>

    ---

    ## Slide <n> · p.<page> — <slide title or "(no title)">

    **Type**: <text | text+image | figure | diagram | reaction | table | divider | mixed>

    **Body**:
    <bulleted body content from the slide, verbatim where possible>

    **Visuals**:
    - <element 1 — what it is + message>
    - <element 2 — …>
    (omit this section if pure text)

    **Annotations**:
    - <anything on the slide a student would need but isn't in body or visuals
       — captions, formula labels, callouts, footnotes>

    **Distilled message** (one sentence):
    <what a student should leave this slide with>

    ---

    (next slide)

# Quality bar

- Every slide gets a section. No gaps.
- Body content is verbatim where reasonable; do not paraphrase technical terms.
- Visual descriptions are concrete and message-forward, not "an image is shown".
- "Distilled message" is one declarative sentence — it's what makes this doc useful
  to other agents. Get it right.
- Match the lecture's language throughout.

When done, send a one-paragraph summary back via your normal output:
- N slides processed
- Any pages that were unreadable / corrupted
- Any topics-boundary issues you noticed (slides that don't fit the assigned theme)
- Confidence: high / medium / low
```

## 3.3 — Aggregate

When all agents finish, update `manifest.json`:
- `phases.3_detail.status = "done"`
- `topics[i].detail_path` for each
- Surface any boundary issues from agent reports (e.g. "slides 92–94 belong with topic 5, not topic 4") — store as `phases.3_detail.flags`

Pause and show the user:
- One-line per topic with detail-doc path
- Any flags worth reviewing

> "Detail extraction complete. Proceed to didactic review and question generation? Reply 'go'."

---

# Phase 4 — Didactic Review

Solo, main thread. Reads the mirror docs (NOT the page renders again) and produces a structured critique.

The mirror docs are the right input here: they distill the slides' messages into one sentence each, which is exactly what a story-arc analysis needs.

## 4.1 — Cross-topic skim

Read every `02_topics/topic-NN-<slug>.md`. Build the **distilled-message list** — one line per slide, in order. Read it as a paragraph:

- Does this read as a coherent story or a topic dump?
- What is the implicit thesis of the lecture?
- Where do transitions feel weak (slide N raises no question that slide N+1 answers)?
- Any concept used before introduction (forward reference without acknowledgement)?
- Any concept introduced and never used again?

## 4.2 — Image use audit

For each topic, count and categorize visuals: figure / diagram / structure / graph / photo / table-as-image. Flag:
- Topics with very high visual density vs. very low (mismatch with topic difficulty?)
- Visuals where the "message" the agent extracted is weak — that's a slide where the figure may not be carrying its weight.
- Repeated visuals — deliberate reinforcement (good) vs. accidental repetition (cut).

## 4.3 — Gap audit

- Concepts referenced (in body or visuals) but never introduced in earlier slides.
- Concepts that appear only in body bullets and never get reinforced visually — these are weakly anchored.
- Standard topics for this lecture-type that are *missing* (use your domain knowledge of the field — for an inorganic-chemistry semester lecture, examples: Born-Haber cycles, MO diagrams, crystal field, ionic vs covalent radii, Frost diagrams). Suggest, don't insist.

## 4.4 — Topical-order critique

- Are topics ordered in a way that builds dependencies forward?
- Would a student have the concepts they need by the time each topic starts?
- Specific reorder suggestions only if the gain is clear.

## 4.5 — Write `03_didactic-review.md`

```markdown
# Didactic Review — <Title>

**Reviewer**: lecture-analysis skill (Phase 4)
**Generated**: <date>

## Implicit thesis (from slide messages)
"…"

## Red line — does it read as a story?
One paragraph verdict.

## Strengths
- Bullet list of what works.

## Weaknesses (ranked by impact)
1. **<Issue>** — <description, with slide / topic refs>. <Suggested fix.>
2. …

## Image-use audit
| Topic | Slides | Visuals | Strong | Weak | Notes |
|-------|--------|---------|--------|------|-------|
| 1     | 35     | 22      | 18     | 4    | Slides 14, 17, 22, 28 carry weak images |
| …     |        |         |        |      |       |

## Gap audit
- **Concepts referenced before introduction**: …
- **Weakly anchored concepts** (text-only, no visual): …
- **Likely-missing topics**: … (with rationale)

## Topical order
Verdict + specific reorder suggestions if any.

## Slide-level flags
List of specific slides worth a second look (≤ 20 entries; rank by impact).
```

Update manifest: `phases.4_review.status = "done"`.

---

# Phase 5 — Questions

Parallel topical agents — one per topic. Each generates a 10-question bank for its topic at mixed difficulty.

## 5.1 — Difficulty mix

Default per topic (10 questions):
- **4 easy** — Bloom: remember, understand. Definitions, identification, recall.
- **4 medium** — Bloom: apply, analyze. Predict, calculate, compare.
- **2 hard** — Bloom: evaluate, create. Justify, design, integrate across slides.

If the user wants a different mix, accept and pass through to agents.

## 5.2 — Question Agent prompt template

```
You are a lecture-analysis question agent. Generate a 10-question bank for ONE topic
of a lecture, at mixed difficulty, grounded in the topic's mirror document.

LECTURE: <title>
LANGUAGE: <language> — write everything in this language
YOUR TOPIC: <title> (#<id>) p.<start>–<end>
INPUT: <sidecar>/02_topics/topic-<id>-<slug>.md
OUTPUT: <sidecar>/04_questions/topic-<id>-<slug>.questions.md

Difficulty mix: 4 easy, 4 medium, 2 hard (Bloom: rem/und · app/ana · eval/cre).

Rules:
- Every question must be answerable from this topic's mirror document. No external
  knowledge required for the answer (you may invoke it for distractors).
- For each question give: stem, optional choices (only when MC fits), MODEL ANSWER,
  the SLIDE(S) it tests, and the BLOOM LEVEL.
- Vary question form: short answer, MC, true/false-with-justify, calculation,
  draw/describe-a-structure, predict-the-product, interpret-a-figure.
- For chemistry: prefer questions that exercise reasoning, not just trivia. ("Why is
  Cs the most reactive alkali metal?" beats "Name the alkali metals.")
- Hard questions should integrate across multiple slides in the topic.

Output format (markdown). All labels (`Questions`, `Easy`, `Medium`, `Hard`, `Q`, `A`) translate to the lecture's language at write time.

    # Questions — Topic <id>: <title>

    > Source: <topic mirror doc>  ·  <n> slides covered

    ## Easy

    ### Q1 — <one-line stem topic> (Slide <n>, Bloom: remember)
    **Q**: <stem>
    **A**: <model answer>

    ### Q2 …

    ## Medium

    ### Q5 — … (Slides <n,m>, Bloom: apply)
    **Q**: …
    **A**: …

    ## Hard

    ### Q9 — … (Slides <n,m,k>, Bloom: evaluate)
    **Q**: …
    **A**: …

When done, return a one-line summary: question count, any topics where you struggled
to find 10 distinct questions (signals thin content).
```

## 5.3 — Aggregate

When all agents finish:
- Update manifest `phases.5_questions.status = "done"`
- `topics[i].questions_path` for each
- Surface "thin" topic flags from agent reports

Final summary to user:

```
Lecture analysis complete · <Title>

  Phase 1 · Overview        → 01_overview.md
  Phase 2 · Ingestion       → 00_ingest/  (<n> pages, <dpi> dpi)
  Phase 3 · Detail          → 02_topics/  (<k> mirror docs)
  Phase 4 · Didactic review → 03_didactic-review.md
  Phase 5 · Questions       → 04_questions/  (<k> banks, <10·k> questions)

Open <sidecar>/manifest.json for the index.
Flags worth reviewing: <list, if any>
```

---

# Phase 6 — PDF export (optional)

Deterministic, no LLM. Renders the didactic review and every question bank to clean modern PDFs for circulation, into `<sidecar>/pdf/`.

## 6.1 — Run the renderer

```bash
.venv/bin/python .claude/skills/lecture-analysis/scripts/render_pdfs.py \
  "<sidecar>"
```

Auto-discovers everything from the sidecar:
- `03_didactic-review.md` → `<prefix>-Didactic-Review.pdf`
- `04_questions/topic-NN-XX-...questions.md` → `<prefix>-Questions-NN-<readable>.pdf` for each topic

The prefix is derived (in order of preference) from `--prefix` CLI override, the manifest title's leading acronym, or the parent directory name (e.g. `lectures/CHEM301/_analysis` → prefix `CHEM301`).

Filename casing is normalised: `gr15` → `G15`, single-letter blocks (`d`, `f`) stay lowercase, 2-3 letter all-lowercase tokens like `pse` / `hg` are uppercased as acronyms.

## 6.2 — Options

```
render_pdfs.py <sidecar> --review-only       # just the review
render_pdfs.py <sidecar> --questions-only    # just the question banks
render_pdfs.py <sidecar> --include-topics    # also render mirror docs (rare)
render_pdfs.py <sidecar> --prefix "Custom"
render_pdfs.py <sidecar> --chrome /path/to/browser
```

The `--include-topics` flag also renders `02_topics/topic-NN-XX-*.md` to `<prefix>-Topic-NN-<readable>.pdf`. Topic mirror docs are usually agent-context only (they're large and slide-by-slide), so this is off by default.

## 6.3 — Templates

Two CSS templates ship with the skill:

- `templates/pdf-review.css` — accent-blue headings + striped tables, used for the didactic review.
- `templates/pdf-questions.css` — same baseline + green/amber/red difficulty bands for `## Easy` / `## Medium` / `## Hard` headings.

Both target an A4 page with 22mm/20mm margins. Edit them in place to retune the look — changes apply on the next run.

## 6.4 — Requirements

- `pandoc` on PATH (Homebrew: `brew install pandoc`).
- A Chromium-based browser. Auto-discovered: Google Chrome, Chromium, MS Edge, Brave (and `google-chrome` / `chromium` / `chromium-browser` on PATH). Override with `--chrome`.
- TeX math (e.g. `^{238}_{92}\text{U}`) renders via MathML — Chrome 109+ supports this natively, no JS or external fonts needed.

## 6.5 — Build artefacts

HTML intermediates are written to `<sidecar>/.pdf-build/` for inspection or manual re-render with a different stylesheet. They're idempotently regenerated; safe to delete.

---

# Resume Logic

On every invocation:

1. Read `manifest.json`. If missing, treat as fresh run.
2. If `--phase N` specified, run only that phase. Verify upstream phases are `done`; if not, refuse and tell the user what to run first.
3. Otherwise, walk phases 1→5; skip any with `status = "done"`; run the next pending one; pause as designed; continue.
4. Failures: set `status = "failed"` and surface error. The next invocation retries that phase only.

---

# Operational Notes

## Parallelism boundaries (deliberate)

- **Phase 1** is solo because it builds the topic plan that Phases 3 and 5 fan out on.
- **Phase 2** is solo because it's deterministic file IO.
- **Phase 3** is parallel because each topic's detail extraction is independent (disjoint page ranges, disjoint output files). One agent per topic.
- **Phase 4** is solo because it needs the whole-lecture view.
- **Phase 5** is parallel for the same reason as Phase 3.

Subagents in Phases 3 and 5 only ever write to their own output file — no contention.

## Why a local sidecar

The mirror docs are agent-context fodder. Local markdown files are zero-overhead to load and diff, plug into any tool that reads files, and are easy to export later if a downstream agent wants them in a knowledge-management UI.

## Vision strategy: render whole pages, not extract images

The PDF has hundreds of embedded image objects. Cropping individual images and feeding them to vision loses spatial relationships (caption vs. figure, arrow flows, panel labels). Rendering the whole page at 144 DPI preserves layout and is what a vision-capable LLM is good at reading. The cost is bigger PNGs; for a typical lecture this is tens to a few hundred MB on disk — fine.

## Language

Outputs in the lecture's dominant language (auto-detected from cover + TOC), or whatever `--language` overrides to. Section headers, question/answer labels, and difficulty band names are translated at write time.

## Pauses (where the user steers)

- After Phase 1 — confirm the topic plan before heavy work starts.
- After Phase 3 — confirm before review and question generation.
- After Phase 5 — final summary, no pause.

## Notes for downstream consumers

- Slide numbering is authoritative across all artifacts so a downstream agent can cite "slide 47" reliably (in whatever language).
- Use a project-local `.venv` rather than installing Python packages globally.
