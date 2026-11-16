---
name: abstract-review
description: Review a conference abstract (.docx) like a senior researcher — analyse quality, add Word-style comments and tracked changes, and append a corrected version. Use when the user provides a .docx abstract for review, asks to review a conference submission, or says "review abstract".
argument-hint: [path to .docx file] [--reviewer "Name"]
---

# Conference Abstract Review

Review a scientific conference abstract in .docx format with the rigour of an experienced co-author. Produce a reviewed copy with Word-compatible comments, tracked changes attributed to a named reviewer, and a fully corrected version appended below the original.

## When to Use

Invoke when the user:
- Provides a .docx conference abstract for review
- Asks to review, proof-read, or improve a conference submission
- Wants tracked changes and comments added to an abstract

## Inputs

**Required:**
- Path to a `.docx` file containing the abstract

**Optional (ask if not provided):**
- `--reviewer "Name"` — the name to attribute tracked changes to. If not provided, **ask the user** before proceeding: *"Who should appear as the reviewer in tracked changes? (e.g., your name as it should show in Word)"*

## Phase 1: Extract and Understand

1. Use a project-local `.venv` rather than installing Python packages globally. If `python-docx` is missing, install it with `.venv/bin/pip install python-docx` (create the venv first with `python3 -m venv .venv` if needed)
2. Extract text from the .docx using Python + `zipfile` + `xml.etree.ElementTree` (handles binary docx reliably)
3. Inspect paragraph structure, styles, and font formatting using `python-docx` to understand the document layout
4. Identify the abstract's components:
   - **Title**
   - **Author list and affiliations**
   - **Abstract body** (one or more paragraphs)
   - **Figure captions** (if present)
   - **References**

## Phase 2: Scientific Evaluation

Evaluate the abstract across these dimensions and prepare internal notes (do NOT output the full evaluation yet — it goes into comments):

### Language & Grammar
- Grammatical errors, typos, awkward phrasing
- Colloquialisms inappropriate for scientific writing (e.g., "good to use" → "ready for use")
- Sentence length and readability — flag run-on sentences (>50 words)
- Correct scientific terminology

### Factual Accuracy
- Verify key scientific claims where possible using web search
- Flag any misclassifications (e.g., calling a peptide an antibody, confusing agonist/antagonist)
- Check that method names, receptor names, chemical nomenclature are correct
- **This is critical** — factual errors in conference abstracts damage credibility

### Structure & Length
- Is the abstract appropriate length for a conference submission? (typically 200-350 words for body text)
- Is there a clear structure: motivation → approach → key results → conclusion?
- Does it try to tell too many stories at once?
- Is the title concise and informative?

### Scientific Content
- Is the motivation clear and specific (not generic)?
- Are quantitative results presented? (An abstract about "quantification" should contain numbers)
- Is the conclusion focused on one clear take-home message?
- Are references appropriate and correctly cited?
- Is the figure caption (if present) self-explanatory?

### Design & Framing
- Does the opening grab attention with the specific problem, not a generic field overview?
- Is the methods detail appropriate for an abstract (high-level, not synthesis recipes)?
- Does the ending resolve or does it open new unresolved questions?

## Phase 3: Generate the Reviewed .docx

Write a Python script (based on the template in `scripts/review_docx_template.py`) that:

### 3a. Add Comments
Use XML manipulation to add Word-compatible comments (`w:comment` elements in `comments.xml`). Each comment:
- Is attributed to the reviewer name (with initials derived from the name)
- Has a timestamp
- Is anchored to a specific text range using `commentRangeStart`/`commentRangeEnd`
- Contains the review observation

**Comment categories to include:**
- Structural observations (too long, wrong focus, missing data)
- Factual errors (with explanation of why it's wrong)
- Language issues that need the author's judgement (not just typos — those get tracked changes)
- Suggestions for improvement that require rewriting (not simple word swaps)
- Positive reinforcement where the writing is genuinely strong ("Good point — this is the core motivation")

### 3b. Add Tracked Changes
Use XML manipulation to insert `w:del` + `w:ins` revision markup for safe, unambiguous corrections:
- Grammar fixes (subject-verb agreement, articles, prepositions)
- Spelling corrections
- Terminology fixes (colloquial → formal)
- Factual corrections (e.g., wrong classification of a compound)
- Hyphenation fixes
- Small phrasing improvements that preserve meaning

**Do NOT tracked-change anything that would alter scientific meaning or requires the author's domain expertise to judge.** Those go in comments instead.

### 3c. Enable Track Changes Mode
Add `w:trackChanges` to the document settings so future edits are also tracked.

### 3d. Save Intermediate
Save as `{original_name}_REVIEWED.docx`.

## Phase 4: Append Corrected Version

Extend the same script to append below the original:

1. **Visual divider** — a centered line of em-dashes in gray
2. **"REVISED VERSION" header** — centered, blue, bold, larger font
3. **"(Suggested redraft — review by {reviewer_name})" subtitle** — centered, gray, italic, smaller
4. **The fully rewritten abstract:**
   - Same formatting style as the original (match font family, sizes for title/body/authors)
   - All tracked-change corrections applied
   - Structural improvements implemented
   - Language polished throughout
   - But: **preserve the authors' voice and tone** — do not over-formalize or alienate the writer
   - **Keep what's genuinely good** — if a sentence or argument works well, keep it recognizably similar
   - Conserve the original experimental logic and narrative arc
   - Use the same references (keep numbering consistent)
   - Fix the figure caption if needed
   - Fix affiliations if there are obvious issues (e.g., language of country names — "Schweden" → "Sweden")

### Tone Principles for the Redraft
- This is a **co-author's revision**, not a hostile review
- The goal is to help the writer, not rewrite from scratch
- Changes should feel like a natural improvement the writer would agree with
- Preserve domain-specific phrasing the writer clearly chose intentionally
- Only restructure when the original structure genuinely hampers readability

## Phase 5: Present Results

After generating the file:

1. **Summarise the review** to the user in chat:
   - Number of comments added
   - Number of tracked changes
   - List of the most critical issues (factual errors first, then structural, then language)
   - Key improvements in the revised version
2. **Note the output file path**
3. **Offer** to explain any specific comment or change in more detail
4. **Offer** to verify any factual claims the user is unsure about (using web search)

## Technical Notes

### python-docx Limitations
- `python-docx` does NOT natively support comments or tracked changes
- Both require direct XML (`lxml`) manipulation of the document's XML parts
- Comments need: creating `comments.xml`, adding it as a part with the correct content type and relationship, inserting `commentRangeStart`/`commentRangeEnd`/`commentReference` elements in the document body
- Tracked changes need: `w:del` with `w:delText` and `w:ins` with `w:t` elements, wrapped with author/date attributes

### Key XML Namespaces
```
W  = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R  = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
```

### Script Template
The full template script is at `scripts/review_docx_template.py`. It provides:
- `add_comment_to_xml()` — creates a comment entry in comments.xml
- `wrap_runs_with_comment()` — anchors a comment to a text range in a paragraph
- `tracked_replace()` — performs a tracked deletion + insertion on a text fragment
- Comments part creation and relationship wiring
- Track changes mode activation in document settings

Adapt the template for each review by populating the specific comments and tracked changes based on the evaluation.
