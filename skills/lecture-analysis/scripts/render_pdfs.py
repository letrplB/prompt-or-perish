#!/usr/bin/env python3
"""
render_pdfs.py — bulk-render lecture-analysis artifacts to PDF.

Default behaviour: render the didactic review + every question bank in a
lecture's _analysis/ sidecar directory to <sidecar>/pdf/, using the styled
CSS templates bundled with this skill.

Usage:
    render_pdfs.py <sidecar-dir>
    render_pdfs.py <sidecar-dir> --include-topics      # also render mirror docs
    render_pdfs.py <sidecar-dir> --review-only
    render_pdfs.py <sidecar-dir> --questions-only
    render_pdfs.py <sidecar-dir> --prefix "CHEM301"    # override file-name prefix
    render_pdfs.py <sidecar-dir> --chrome /path/to/chromium

The sidecar directory is the `_analysis/` folder produced by the
lecture-analysis skill. The script auto-discovers:
  - <sidecar>/03_didactic-review.md
  - <sidecar>/04_questions/*.questions.md
  - (optional) <sidecar>/02_topics/*.md
and reads <sidecar>/manifest.json (if present) for clean PDF titles.

Output PDFs land in <sidecar>/pdf/. HTML build artefacts are kept in
<sidecar>/.pdf-build/ for inspection / re-rendering.

Requires:
  - pandoc on PATH
  - Google Chrome / Chromium / MS Edge (any Chromium-based browser will do).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
REVIEW_CSS = TEMPLATES / "pdf-review.css"
QUESTIONS_CSS = TEMPLATES / "pdf-questions.css"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome",
    "chromium",
    "chromium-browser",
]


def find_chrome(override: str | None) -> str:
    if override:
        if Path(override).exists() or shutil.which(override):
            return override
        sys.exit(f"--chrome path not found: {override}")
    for c in CHROME_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit(
        "Could not find a Chromium-based browser. Pass --chrome /path/to/chrome.\n"
        "Tried: " + ", ".join(CHROME_CANDIDATES)
    )


def slug_to_label(slug: str, manifest_topics: list[dict]) -> str:
    """Map a slug from a filename back to a readable label.

    First try to match against the manifest's topic list (best). Fall back to
    title-casing the slug.
    """
    for t in manifest_topics:
        if t.get("slug") == slug:
            return t.get("title", slug)
    # Fallback: title-case the slug
    return slug.replace("-", " ").title()


def derive_prefix(sidecar: Path, manifest: dict) -> str:
    """Derive a short prefix for output filenames.

    Order of preference:
    1. --prefix CLI override (handled by caller)
    2. manifest.title (cleaned)
    3. parent directory name of sidecar (e.g. lectures/CHEM301/_analysis -> CHEM301)
    """
    title = manifest.get("title", "")
    if title:
        # Take the first space-separated chunk that looks short and acronym-y
        first = title.split(":")[0].strip().split()
        if first and 2 <= len(first[0]) <= 6 and first[0].isupper():
            return first[0]
    # Fallback to directory name
    return sidecar.parent.name


def parse_question_filename(stem: str) -> tuple[int, str] | None:
    """Parse 'topic-NN-[XX-]slug-words.questions' -> (NN, slug)."""
    m = re.match(r"^topic-(\d+)-((?:\d+-)?.+)\.questions$", stem)
    if not m:
        return None
    return int(m.group(1)), m.group(2)


def parse_topic_filename(stem: str) -> tuple[int, str] | None:
    """Parse 'topic-NN-[XX-]slug-words' -> (NN, slug)."""
    m = re.match(r"^topic-(\d+)-((?:\d+-)?.+)$", stem)
    if not m:
        return None
    return int(m.group(1)), m.group(2)


def slug_to_filename_part(slug: str) -> str:
    """Convert a slug like '08-gr15-pnicogene' to a filename-friendly token.

    Strips the leading numeric ordering prefix (08-) since we use the topic id
    as the primary order key. Handles a few common patterns:
      gr15 / gr01    -> G15 / G1   (strip leading zeros from group numbers)
      d / f          -> d / f      (single-letter block names stay lowercase)
      pse / hg / nmr -> PSE / HG / NMR  (2-3 letter all-lowercase = acronym)
      kohlenstoff    -> Kohlenstoff  (default: capitalise first letter)
    """
    parts = slug.split("-", 1)
    if parts and parts[0].isdigit() and len(parts) > 1:
        slug = parts[1]
    out_parts = []
    for p in slug.split("-"):
        m = re.match(r"^gr(\d+)$", p)
        if m:
            out_parts.append("G" + str(int(m.group(1))))
            continue
        if len(p) == 1 and p.isalpha() and p.islower():
            out_parts.append(p)  # 'd', 'f' for d-Block / f-Block
            continue
        if 2 <= len(p) <= 3 and p.isalpha() and p.islower():
            out_parts.append(p.upper())  # 'pse' -> 'PSE', 'hg' -> 'HG'
            continue
        out_parts.append(p[:1].upper() + p[1:])
    return "-".join(out_parts)


def render(
    md: Path, css: Path, html: Path, pdf: Path, pagetitle: str,
    pandoc: str, chrome: str
) -> None:
    pdf.parent.mkdir(parents=True, exist_ok=True)
    html.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        pandoc, str(md),
        "--standalone", "--embed-resources",
        "--css", str(css),
        "--mathml",
        "--metadata", f"pagetitle={pagetitle}",
        "-f", "markdown", "-t", "html5",
        "-o", str(html),
    ], check=True)
    subprocess.run([
        chrome,
        "--headless", "--disable-gpu",
        "--no-pdf-header-footer", "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf}",
        f"file://{html}",
    ], check=True, stderr=subprocess.DEVNULL)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("sidecar", help="Path to _analysis/ directory")
    ap.add_argument("--prefix", help="Override prefix for output PDF names")
    ap.add_argument("--review-only", action="store_true",
                    help="Only render the didactic review")
    ap.add_argument("--questions-only", action="store_true",
                    help="Only render question banks (skip review)")
    ap.add_argument("--include-topics", action="store_true",
                    help="Also render per-topic mirror docs (rare; usually agent-context only)")
    ap.add_argument("--chrome", help="Path to Chrome / Chromium / Edge / Brave")
    args = ap.parse_args()

    sidecar = Path(args.sidecar).resolve()
    if not sidecar.is_dir():
        sys.exit(f"Sidecar dir not found: {sidecar}")
    if not REVIEW_CSS.exists() or not QUESTIONS_CSS.exists():
        sys.exit(f"CSS templates missing under {TEMPLATES}")

    pandoc = shutil.which("pandoc") or sys.exit("pandoc not on PATH")
    chrome = find_chrome(args.chrome)

    # Load manifest if present
    manifest_path = sidecar / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception as e:
            print(f"Warning: could not read manifest.json: {e}", file=sys.stderr)

    topics = manifest.get("topics", [])
    prefix = args.prefix or derive_prefix(sidecar, manifest)
    out_dir = sidecar / "pdf"
    build_dir = sidecar / ".pdf-build"

    # 1. Didactic review
    if not args.questions_only:
        review_md = sidecar / "03_didactic-review.md"
        if review_md.exists():
            print(f"Review: {review_md.name}")
            render(
                review_md, REVIEW_CSS,
                build_dir / "didactic-review.html",
                out_dir / f"{prefix}-Didactic-Review.pdf",
                f"{prefix} — Didactic Review",
                pandoc, chrome,
            )
        else:
            print(f"  (skipped) no review at {review_md}")

    # 2. Question banks
    if not args.review_only:
        qdir = sidecar / "04_questions"
        if qdir.is_dir():
            qfiles = sorted(qdir.glob("*.questions.md"))
            print(f"Questions: {len(qfiles)} bank(s)")
            for q_path in qfiles:
                parsed = parse_question_filename(q_path.stem)
                if not parsed:
                    print(f"  (skipped) cannot parse filename: {q_path.name}")
                    continue
                topic_id, slug = parsed
                label_token = slug_to_filename_part(slug)
                pretty_title = slug_to_label(slug, topics)
                pdf_name = f"{prefix}-Questions-{topic_id:02d}-{label_token}.pdf"
                print(f"  → {pdf_name}")
                render(
                    q_path, QUESTIONS_CSS,
                    build_dir / f"q-{topic_id:02d}-{slug}.html",
                    out_dir / pdf_name,
                    f"{prefix} — Questions {pretty_title}",
                    pandoc, chrome,
                )

    # 3. Topic mirror docs (optional)
    if args.include_topics:
        tdir = sidecar / "02_topics"
        if tdir.is_dir():
            tfiles = sorted(tdir.glob("topic-*.md"))
            print(f"Topic mirrors: {len(tfiles)} doc(s)")
            for tmd in tfiles:
                parsed = parse_topic_filename(tmd.stem)
                if not parsed:
                    continue
                topic_id, slug = parsed
                label_token = slug_to_filename_part(slug)
                pretty_title = slug_to_label(slug, topics)
                pdf_name = f"{prefix}-Topic-{topic_id:02d}-{label_token}.pdf"
                print(f"  → {pdf_name}")
                # Topic mirror docs use the questions stylesheet (similar
                # structure: per-slide H2/H3 sections); could swap to a
                # dedicated style later.
                render(
                    tmd, QUESTIONS_CSS,
                    build_dir / f"topic-{topic_id:02d}-{slug}.html",
                    out_dir / pdf_name,
                    f"{prefix} — Topic {topic_id}: {pretty_title}",
                    pandoc, chrome,
                )

    print(f"\nDone. Output: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
