# Reference Verification Protocol — Deep Methodology

This document provides detailed guidance for Phase 3 reference verification agents.

---

## Common Miscitation Patterns

These are the most frequent ways papers misrepresent their references. Verify agents should actively look for each pattern:

### 1. Oversimplification
**What it looks like:** The reference contains a nuanced finding with caveats, but the citing paper presents it as a simple, definitive result.
**Example:** Ref says "Under conditions X, we observed Y with some exceptions (see Table 3)" → Cited as "Y has been demonstrated [ref]"
**How to detect:** Compare hedging language in the reference vs. the citing paper's characterization.

### 2. Selective Citation
**What it looks like:** The reference contains multiple findings, some supporting and some contradicting the citing paper's narrative. Only the supporting finding is cited.
**Example:** Ref shows method A works for X but fails for Y → Cited only for "method A works for X [ref]" while the citing paper also applies it to Y.
**How to detect:** Read the full findings section of the reference, not just the part that seems to match.

### 3. Context Stripping
**What it looks like:** A finding that was specific to certain conditions is cited as a general result.
**Example:** Ref found effect at 500°C → Cited as "this effect is well-known [ref]" without noting the temperature condition, while the citing paper works at 25°C.
**How to detect:** Check the experimental conditions in the reference vs. the citing paper.

### 4. Claim Escalation
**What it looks like:** The reference suggested or hypothesized something, but the citing paper presents it as established fact.
**Example:** Ref says "we hypothesize that mechanism Z may contribute" → Cited as "mechanism Z has been shown to contribute [ref]"
**How to detect:** Compare verb tenses and hedging language between source and citation.

### 5. Attribution Error
**What it looks like:** The finding is attributed to the wrong reference, or the reference doesn't contain the claimed finding at all.
**Example:** "Smith et al. showed X [ref]" but Smith et al. never studied X — it was in a different paper.
**How to detect:** Search the reference for the specific finding. If absent, it's attribution error.

### 6. Contradicted Citation
**What it looks like:** The reference actually contradicts the citing paper's claim, but is cited as if it supports it.
**Example:** Ref shows treatment had no significant effect → Cited as supporting the treatment's effectiveness.
**How to detect:** Read the reference's conclusion. Does it agree or disagree with how it's being used?

### 7. Outdated Citation
**What it looks like:** An old reference is cited for a finding that has been superseded, updated, or retracted by newer work.
**How to detect:** Check the reference's citation graph for corrections, retractions, or significant follow-up studies.

---

## Verification Workflow (Per Reference)

```
1. IDENTIFY the specific claim being supported by this citation
   └── What EXACTLY does the citing paper say this reference shows?

2. LOCATE the reference
   ├── Paper-retrieval MCP (if configured): search_papers → get_paper_metadata → get_full_text
   ├── DOI resolution: WebFetch("https://doi.org/{doi}")
   └── Web search: WebSearch("{author} {year} {title}")

3. READ the reference
   ├── If full text available: Read abstract + relevant sections
   │   Focus on: Results, Discussion, Conclusion, specific tables/figures cited
   ├── If only abstract: Read abstract carefully
   │   Note: Abstract-only verification has LOWER confidence
   └── If nothing available: Mark as "unverifiable" and move on

4. COMPARE
   ├── What the citing paper claims → What the reference actually says
   ├── Check for each miscitation pattern above
   ├── Note: Some degree of simplification is normal in citations
   │   Flag only when the simplification CHANGES THE MEANING
   └── Consider: Is the citation FAIR even if not perfectly precise?

5. VERDICT
   ├── ACCURATE — Fair representation, even if simplified
   ├── DISTORTED — Meaning changed, but the reference is related to the claim
   ├── UNSUPPORTED — The reference doesn't address this topic at all
   └── CONTRADICTED — The reference says the opposite

6. ASSESS IMPACT
   ├── Which claims in the citing paper depend on this reference?
   ├── Is this the ONLY reference supporting a claim? (high impact)
   ├── Are there other references that DO support the claim? (lower impact)
   └── Does this miscitation indicate a pattern? (systematic issue)
```

---

## Confidence Calibration

**HIGH confidence** — You read the full text and can point to specific passages:
- Verdict is based on direct quotes from the reference
- The relevant section of the reference is unambiguous
- You found exactly what the citing paper claims (or confirmed its absence)

**MEDIUM confidence** — You have the abstract + metadata but not full text:
- Abstract is consistent/inconsistent with the citation
- The topic area matches but you can't verify specific claims
- Note this limitation explicitly in the verdict

**LOW confidence** — You have only metadata:
- Title and year match, but you can't verify content
- Or: full text found but the relevant passage is ambiguous
- Do not issue DISTORTED/UNSUPPORTED/CONTRADICTED at low confidence
- Mark as "insufficient data for verification"

---

## Citation Graph Intelligence

When verifying a reference, also check its citation context. If a paper-retrieval MCP with a citation-graph tool is configured (e.g. `mcp__papers__get_citation_graph(paperId="{id}")`), use it. Otherwise, run a `WebSearch` for the paper title plus terms like "retracted", "correction", "critique", or "follow-up".

Look for:
- **Retractions or corrections** — if the reference was retracted, it should not be cited at all
- **Significant critiques** — papers that challenged the reference's findings
- **Updates** — newer papers by the same group that revised the findings
- **High-citation follow-ups** — if a major paper built on and validated/invalidated the reference

This information goes into the verification report under "Citation Graph Context."

---

## Rate Limiting & Efficiency

- Paper-retrieval MCP calls: no explicit rate limit, but be efficient. Batch search queries.
- Web searches: space queries, avoid repeating failed searches.
- Full text retrieval: this is the expensive operation. Prioritize by triage score.
- If a reference shares authors with another already-verified reference, the full text may already be partially familiar — note connections.

---

## Cache Integration

Before starting verification on any reference:
1. Read `reviews/reference_cache/index.md`
2. Search for the reference's DOI or title
3. If found, read the cache entry
4. If the `cited_as` field in a prior verification matches the current citation context → verdict is reusable
5. If `cited_as` differs → new verification needed, but `key_findings` and `key_passages` from cache provide a head start
6. Always add your new verification to the cache after completing it
