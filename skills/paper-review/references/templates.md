# Paper Review — Output Templates

Templates for each artifact produced during a paper review. Agents should follow these formats.

---

## Dimension Report Template (Phase 2)

All dimension reports follow this structure:

```markdown
# {Dimension Name} — {Paper Title (short)}

**Reviewer:** {agent role}
**Date:** {YYYY-MM-DD}
**Scope:** {what was analyzed}

---

## Summary

{2-3 sentence executive summary of findings for this dimension}

**Severity breakdown:** {N} CRITICAL, {N} CONCERN, {N} NOTE

---

## Detailed Findings

### Finding {N}: {Short title}

**Severity:** [CRITICAL] | [CONCERN] | [NOTE] | [USER] | [POSITIVE]
**Location:** {Section/Figure/Table/Claim reference}
**Evidence:** {What specifically was found}
**Impact:** {How this affects the paper's overall quality or claims}
**Recommendation:** {Specific action for authors — if applicable}

---

## {Dimension-Specific Sections}

{Each dimension has its own analysis sections — see SKILL.md for what each agent produces}

---

## Flags Summary

{Consolidated list of all flags from this dimension}

- [CRITICAL] {description} — Location: {ref}
- [CONCERN] {description} — Location: {ref}
- [USER] {description} — Question: {what input is needed}
- [NOTE] {description}
```

---

## Claim Map Template (Phase 1)

```markdown
# Claim Map — {Paper Title}

**Extracted:** {date}
**Total claims:** {N} (novel: {K}, background: {M}, methodological: {J}, interpretive: {L})
**Figures analyzed:** {N}
**References cataloged:** {N}

---

## Novel Claims

### CLAIM-001: {one-sentence claim}

- **Type:** novel
- **Location:** Section {X}, paragraph {Y}
- **Verbatim:** "{exact quote}"
- **Strength language:** {demonstrates | shows | suggests | ...}
- **Strength score:** {1-5, where 5 = definitive}
- **Evidence pointers:**
  - Figure {N}: {what figure supposedly shows}
  - Table {N}: {what data point is cited}
  - Data: {inline numbers or statistics}
  - Reference: [{ref_number}] — {what ref supposedly supports}
- **Vision check:** {if applicable}
  - Independent reading: {what the figure actually shows}
  - Alignment: match | partial_mismatch | mismatch
  - Details: {specifics}
- **Flags:** {any immediate flags}

### CLAIM-002: ...

---

## Background Claims

{Same format, typically less detail needed}

---

## Methodological Claims

{Claims about methods — "we used X because Y", "our approach differs from Z"}

---

## Interpretive Claims

{Claims in the Discussion that interpret results — "this suggests mechanism X"}

---

## Vision Analysis Summary

| Figure/Table | Independent Reading | Text Claims | Alignment | Flags |
|---|---|---|---|---|
| Fig 1a | {description} | {what text says} | match | — |
| Fig 2b | {description} | {what text says} | mismatch | [CRITICAL] axis scale |
| Table 1 | {description} | {what text says} | partial | [CONCERN] rounding |
```

---

## Reference Catalog Template (Phase 1)

```markdown
# Reference Catalog — {Paper Title}

**Total references:** {N}
**Key claim support:** {K}
**Method basis:** {M}
**Background:** {J}

---

### REF-001: [{1}] {Author}, {Year} — {Title}

- **Bibliographic details:** {full reference as stated in paper}
- **DOI (if stated):** {doi}
- **Importance:** key_claim_support | method_basis | background | peripheral
- **Citation contexts:**
  1. Section {X}: "{sentence}" — Usage: claim_support → CLAIM-{NNN}
  2. Section {Y}: "{sentence}" — Usage: background
- **Total citations in paper:** {N} times
- **Notes:** {any observations about how this ref is used}

### REF-002: ...
```

---

## Metadata Scan Template (Phase 3A)

```markdown
# Reference Metadata Scan — {Paper Title}

**Date:** {YYYY-MM-DD}
**Total references:** {N}
**Verified:** {K} | **Not found:** {M} | **Cached:** {J}

---

### REF-001: {Author}, {Year}

- **Status:** verified | not_found | metadata_only | cached
- **DOI match:** yes | no | not_stated | mismatch
- **Paper-retrieval MCP ID:** {id or "not used"}
- **Title match:** exact | close | different
- **Year match:** yes | off_by_one | different
- **Abstract available:** yes | no
- **Abstract-level citation check:**
  - Context 1: "{citing sentence}" → match | suspicious | mismatch
    - Reason: {if suspicious/mismatch, explain why}
- **Deep verification priority:** high | medium | low | skip
- **Priority reason:** {justification}
- **Cache status:** hit (review: {slug}, verdict: {verdict}) | miss
```

---

## Deep Verification Template (Phase 3B)

```markdown
---
ref_number: {N}
ref_id: "REF-{NNN}"
title: "{full title}"
authors: "{authors}"
year: {year}
doi: "{doi}"
journal: "{journal}"
verdict: accurate | distorted | unsupported | contradicted
confidence: high | medium | low
full_text_source: papers_mcp | web | pdf | abstract_only
---

# Reference Verification: [{ref_number}] {Author}, {Year}

## Citation Context in Reviewing Paper

{The exact sentence(s) where this reference is cited, with the claim it supports}

**Claim supported:** CLAIM-{NNN} — {short description}
**Citation usage:** {claim_support | method_justification | comparison | background}

## What the Citing Paper Claims This Reference Shows

{Extracted and paraphrased: what does the citing paper say this reference demonstrates/found/showed?}

## What the Reference Actually Says

{Direct quotes from the referenced paper, with section/page indicators}

> "{Quote 1}" — Section {X}

> "{Quote 2}" — Section {Y}

## Comparison & Verdict

**Verdict: {ACCURATE | DISTORTED | UNSUPPORTED | CONTRADICTED}**

{Detailed analysis:}
- What matches: {specifics}
- What diverges: {specifics}
- Severity of divergence: {minor nuance vs. fundamental misrepresentation}

## Impact on Review

- **Affected claims:** CLAIM-{NNN}, CLAIM-{MMM}
- **Severity:** {How badly does this affect the paper? Does it invalidate a core claim or just weaken a background statement?}
- **Flag:** [{CRITICAL | CONCERN}] {one-line summary for flags.md}
```

---

## Cross-Findings Template (Phase 4)

```markdown
# Cross-Dimensional Findings — {Paper Title}

**Date:** {YYYY-MM-DD}

---

## Compound Patterns Detected

### Pattern 1: {Pattern Name}

**Components:**
- {Dimension 1}: {finding}
- {Dimension 2}: {finding}
- {Dimension 3}: {finding}

**Combined assessment:** {What these findings mean together — worse than any individual finding}
**Severity:** CRITICAL | CONCERN
**Affected claims:** CLAIM-{NNN}, CLAIM-{MMM}

### Pattern 2: ...

---

## Strength Patterns

{Compound positive findings — things the paper does well across multiple dimensions}

---

## Claim Status Summary

| Claim ID | Claim (short) | Evidence | Logic | Refs | Domain | Net Status |
|---|---|---|---|---|---|---|
| CLAIM-001 | {desc} | strong | sound | verified | novel | SOLID |
| CLAIM-003 | {desc} | weak | gap | miscited | prior art | CRITICAL |
| ... |
```

---

## Final Review Report Template

See SKILL.md Section 4.2 for the full REVIEW_REPORT.md structure.
