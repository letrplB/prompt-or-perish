# prompt-or-perish

A small library of [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) skills for the parts of academic life that survive in 2026: writing papers, reviewing them, building decks, prepping lectures, hosting sessions, and quietly checking whether the document on your desk was actually written by a human.

These skills were built and used in real research and teaching workflows, then scrubbed of any platform-specific assumptions so they work as plain Claude Code skills against the local filesystem.

## What's inside

| Skill | What it does |
|---|---|
| **`paper-review`** | Multi-agent paper review — claim extraction, vision analysis of every figure, independent literature survey, datapoint-level claim/evidence alignment, deep reference verification with cache. |
| **`abstract-review`** | Reviews a `.docx` conference abstract like a senior co-author. Adds Word-compatible comments + tracked changes attributed to a named reviewer, then appends a corrected version below the original. |
| **`presentation-review`** | 4-pass deck refinement (diagnose → manifest → execute → integrate). Grounded in Doumont's three laws with additions from Duarte and Reynolds. Focuses on content and structure, not visual style. |
| **`lecture-analysis`** | End-to-end lecture-PDF analysis through 5 stackable phases: overview → ingestion (text + page renders) → parallel topical detail extraction with vision → didactic review → per-topic question banks. Optional Phase 6 renders artifacts to PDFs. |
| **`session-host`** | Deep background research on every talk in a conference session. Finds the group leader, recent publications, and drafts 10 questions on a SAFE → HIGH-RISK spectrum the host can use if the audience goes quiet. |
| **`exam-solutions`** | Generates correction templates / solution keys for `.docx` exams. Parses questions and points, dispatches a parallel agent team (one per question), and produces per-question markdown with model answers and grading rubrics. Auto-detects exam language. |
| **`docx-forensics`** | Forensic inspection of `.docx` files to detect AI-generated content. Checks ZIP timestamps, revision-save IDs, sub/superscript rendering, citation integrity, image metadata, and prompt-leftover patterns. Produces a structured markdown report. |

Each skill is self-contained under `skills/<name>/` with a `SKILL.md` and any scripts/templates it needs.

## Install

Skills live under `~/.claude/skills/` (user-level) or `.claude/skills/` (project-level). To install all of them at user level:

```bash
git clone https://github.com/<you>/prompt-or-perish.git
mkdir -p ~/.claude/skills
cp -R prompt-or-perish/skills/* ~/.claude/skills/
```

Or to install just one:

```bash
cp -R prompt-or-perish/skills/paper-review ~/.claude/skills/
```

To install at project scope (so the skill ships with a specific repo), use `.claude/skills/` inside that project instead.

After installation, restart Claude Code so it picks up the new skills.

## Use

Most skills can be invoked by:

- A slash command — `/paper-review path/to/paper.pdf`
- Or just by description — "review this abstract", "analyze this lecture PDF", "is this docx AI-generated?"

Each `SKILL.md` documents its arguments, phases, and output structure.

## Requirements

- **Claude Code** — these are Claude Code skills.
- **Python 3.10+** with a project-local `.venv` for skills that ship Python scripts (`paper-review`, `lecture-analysis`, `abstract-review`, `docx-forensics`). Per-skill dependencies are listed in their `SKILL.md` or `scripts/requirements.txt`.
- **Pandoc + a Chromium-based browser** for `lecture-analysis` Phase 6 (PDF export only).

### Optional: paper-retrieval MCP

`paper-review` and `session-host` work out of the box using Claude Code's built-in `WebSearch` and `WebFetch`. They get sharper if you also configure a paper-retrieval MCP — one that exposes tools like `search_papers`, `get_paper_metadata`, `get_full_text`, and (ideally) `get_citation_graph`. Any MCP that follows that surface area drops in.

Example `.mcp.json` entry, using the `@sura_ai/papers` npm package (GitHub repo to follow):

```json
{
  "mcpServers": {
    "papers": {
      "command": "bunx",
      "args": ["@sura_ai/papers@latest"],
      "env": {
        "CORE_API_KEY": "<your CORE API key>"
      }
    }
  }
}
```

If you don't have one configured, the skills detect that and fall back to web search — verification confidence is noted as reduced in the report.

### Optional: chemistry MCP

For chemistry-heavy use of `paper-review`, `exam-solutions`, or `lecture-analysis`, a chemistry MCP that resolves compounds, CAS numbers, and InChI keys helps the agents verify nomenclature and structures.

Example `.mcp.json` entry, using the `@sura_ai/chemistry` npm package (GitHub repo to follow):

```json
{
  "mcpServers": {
    "chemistry": {
      "command": "bunx",
      "args": ["@sura_ai/chemistry@latest"],
      "env": {
        "CHEMISTRY_USER_AGENT": "<your-app-name>/0.1"
      }
    }
  }
}
```

### Optional: local literature index

If you keep a local notes / literature folder, the skills will use it for cross-referencing when an appropriate search MCP (e.g. anything exposing a `query` tool over your notes) is configured. Otherwise that step is skipped silently.

## Design notes

- **Markdown-first output.** Every skill writes plain markdown to a per-task workspace. No platform lock-in; export elsewhere later if you want.
- **Parallel agent teams where it pays.** `paper-review`, `exam-solutions`, `session-host`, and `lecture-analysis` use parallel subagents or `TeamCreate` for the embarrassingly-parallel parts (per-figure, per-question, per-talk, per-topic). The orchestrator stays in the main thread for synthesis.
- **Pause points by design.** Heavy skills pause for user confirmation between phases (after extraction, after dispatch plan, before applying edits). You stay in the loop.
- **Resumable.** Skills with persistent state (`paper-review`, `lecture-analysis`, `presentation-review`) write a manifest or review document next to the source so a partial run can pick up where it left off.

## Contributing

Issues and PRs welcome. Each skill is independently usable, so a fix or extension to one shouldn't ripple across the others.

If you want to add a new skill, drop a directory under `skills/` with a `SKILL.md` (frontmatter: `name`, `description`, optional `argument-hint`) and a brief usage section. Keep it filesystem-native — no platform-specific output assumptions.

## License

MIT. See [LICENSE](./LICENSE).
