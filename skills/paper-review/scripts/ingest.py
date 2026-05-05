#!/usr/bin/env python3
"""
Paper ingestion pipeline for paper-review skill.
Handles PDF and DOCX → normalized markdown + extracted figures + page renders.

Usage:
    python ingest.py --pdf paper.pdf --output ./00_source/
    python ingest.py --docx paper.docx --output ./00_source/
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# PDF ingestion (PyMuPDF / fitz)
# ---------------------------------------------------------------------------

def ingest_pdf(pdf_path: Path, output_dir: Path) -> dict:
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf_path))

    figures_dir = output_dir / "figures"
    pages_dir = output_dir / "pages"
    figures_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    # ---- metadata ----
    meta = doc.metadata or {}
    metadata = {
        "title": meta.get("title", "").strip() or _guess_title_pdf(doc),
        "authors": meta.get("author", "").strip(),
        "source_type": "pdf",
        "source_path": str(pdf_path.resolve()),
        "pages": len(doc),
        "figures_extracted": 0,
        "tables_detected": 0,
    }

    # ---- extract text with structure ----
    sections: list[dict] = []
    current_section = {"heading": None, "level": 0, "paragraphs": []}
    heading_pattern = re.compile(
        r"^(Abstract|Introduction|Methods?|Materials?\s+and\s+Methods?|"
        r"Experimental\s+Section|Results?|Discussion|Conclusions?|"
        r"Acknowledge?ments?|References|Supporting\s+Information|"
        r"Supplementary|Author\s+Contributions?|Data\s+Availability|"
        r"Conflicts?\s+of\s+Interest|Funding|Appendix)",
        re.IGNORECASE,
    )
    numbered_heading = re.compile(r"^(\d+\.?\d*\.?\d*)\s+(.+)$")

    for page_idx, page in enumerate(doc):
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            block_text_parts = []
            max_font_size = 0
            is_bold = False
            for line in block["lines"]:
                line_text = ""
                for span in line["spans"]:
                    line_text += span["text"]
                    if span["size"] > max_font_size:
                        max_font_size = span["size"]
                    if span["flags"] & 2 ** 4:  # bold flag
                        is_bold = True
                block_text_parts.append(line_text.strip())

            block_text = " ".join(block_text_parts).strip()
            if not block_text:
                continue

            # Detect headings: large font, bold, or matching known patterns
            is_heading = False
            heading_level = 2
            clean = block_text.strip()

            if heading_pattern.match(clean):
                is_heading = True
                heading_level = 2
            elif numbered_heading.match(clean):
                m = numbered_heading.match(clean)
                num = m.group(1)
                depth = num.count(".")
                heading_level = min(2 + depth, 4)
                is_heading = True
            elif max_font_size > 12 and is_bold and len(clean) < 120:
                is_heading = True
                heading_level = 2 if max_font_size > 14 else 3

            if is_heading:
                if current_section["paragraphs"] or current_section["heading"]:
                    sections.append(current_section)
                current_section = {
                    "heading": clean,
                    "level": heading_level,
                    "paragraphs": [],
                }
            else:
                current_section["paragraphs"].append(block_text)

    if current_section["paragraphs"] or current_section["heading"]:
        sections.append(current_section)

    # ---- extract embedded images ----
    fig_count = 0
    seen_xrefs = set()
    for page_idx, page in enumerate(doc):
        images = page.get_images(full=True)
        for img in images:
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                base_image = doc.extract_image(xref)
                if base_image and base_image["image"]:
                    w = base_image.get("width", 0)
                    h = base_image.get("height", 0)
                    # Skip tiny images (icons, decorations)
                    if w < 50 or h < 50:
                        continue
                    fig_count += 1
                    ext = base_image.get("ext", "png")
                    fig_path = figures_dir / f"figure_{fig_count:03d}.{ext}"
                    fig_path.write_bytes(base_image["image"])
            except Exception:
                continue

    metadata["figures_extracted"] = fig_count

    # ---- render pages as images (200 DPI) for vision analysis ----
    for page_idx, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        page_path = pages_dir / f"page_{page_idx + 1:03d}.png"
        pix.save(str(page_path))

    # ---- detect tables (heuristic: lines with multiple tab/space-aligned columns) ----
    table_count = 0
    for page_idx, page in enumerate(doc):
        text = page.get_text("text")
        lines = text.split("\n")
        consecutive_tabular = 0
        for line in lines:
            # Rough heuristic: lines with 3+ groups of whitespace-separated tokens
            parts = re.split(r"\s{2,}", line.strip())
            if len(parts) >= 3 and len(line.strip()) > 10:
                consecutive_tabular += 1
            else:
                if consecutive_tabular >= 3:
                    table_count += 1
                consecutive_tabular = 0
        if consecutive_tabular >= 3:
            table_count += 1

    metadata["tables_detected"] = table_count

    # ---- extract reference list ----
    references = _extract_references_pdf(sections)

    # ---- write outputs ----
    _write_parsed_text(sections, references, metadata, output_dir)
    _write_metadata(metadata, output_dir)

    doc.close()
    return metadata


# ---------------------------------------------------------------------------
# DOCX ingestion (python-docx)
# ---------------------------------------------------------------------------

def ingest_docx(docx_path: Path, output_dir: Path) -> dict:
    from docx import Document
    from docx.opc.constants import RELATIONSHIP_TYPE as RT

    doc = Document(str(docx_path))

    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # ---- metadata ----
    props = doc.core_properties
    metadata = {
        "title": (props.title or "").strip() or _guess_title_docx(doc),
        "authors": (props.author or "").strip(),
        "source_type": "docx",
        "source_path": str(docx_path.resolve()),
        "pages": 0,  # DOCX doesn't have reliable page count
        "figures_extracted": 0,
        "tables_detected": len(doc.tables),
    }

    # ---- extract text with structure ----
    sections: list[dict] = []
    current_section = {"heading": None, "level": 0, "paragraphs": []}

    for para in doc.paragraphs:
        style_name = (para.style.name or "").lower()
        text = para.text.strip()
        if not text:
            continue

        if "heading" in style_name:
            if current_section["paragraphs"] or current_section["heading"]:
                sections.append(current_section)
            # Extract heading level from style name (e.g., "Heading 2" → 2)
            level_match = re.search(r"\d+", style_name)
            level = int(level_match.group()) if level_match else 2
            current_section = {
                "heading": text,
                "level": min(level, 4),
                "paragraphs": [],
            }
        elif "title" in style_name:
            if current_section["paragraphs"] or current_section["heading"]:
                sections.append(current_section)
            current_section = {"heading": text, "level": 1, "paragraphs": []}
        else:
            current_section["paragraphs"].append(text)

    if current_section["paragraphs"] or current_section["heading"]:
        sections.append(current_section)

    # ---- extract images ----
    fig_count = 0
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            try:
                image_data = rel.target_part.blob
                # Determine extension from content type
                ct = rel.target_part.content_type or ""
                ext = "png"
                if "jpeg" in ct or "jpg" in ct:
                    ext = "jpg"
                elif "gif" in ct:
                    ext = "gif"
                elif "tiff" in ct:
                    ext = "tiff"
                fig_count += 1
                fig_path = figures_dir / f"figure_{fig_count:03d}.{ext}"
                fig_path.write_bytes(image_data)
            except Exception:
                continue

    metadata["figures_extracted"] = fig_count

    # ---- extract tables as markdown ----
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    for t_idx, table in enumerate(doc.tables):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        if rows:
            md_table = _rows_to_markdown_table(rows)
            table_path = tables_dir / f"table_{t_idx + 1:03d}.md"
            table_path.write_text(md_table, encoding="utf-8")

    # ---- extract references ----
    references = _extract_references_docx(sections)

    # ---- write outputs ----
    _write_parsed_text(sections, references, metadata, output_dir)
    _write_metadata(metadata, output_dir)

    return metadata


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _guess_title_pdf(doc) -> str:
    """Guess title from first page: largest font text."""
    import fitz
    page = doc[0]
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    candidates = []
    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip():
                    candidates.append((span["size"], span["text"].strip()))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        # Title is usually the largest text on page 1
        return candidates[0][1][:200]
    return "Unknown Title"


def _guess_title_docx(doc) -> str:
    """Guess title from first heading or Title style."""
    for para in doc.paragraphs:
        style = (para.style.name or "").lower()
        text = para.text.strip()
        if text and ("title" in style or "heading 1" in style):
            return text[:200]
    # Fallback: first non-empty paragraph
    for para in doc.paragraphs:
        if para.text.strip():
            return para.text.strip()[:200]
    return "Unknown Title"


def _extract_references_pdf(sections: list[dict]) -> list[str]:
    """Extract reference entries from the References section or by pattern matching."""
    refs = []

    # Strategy 1: Look for a section with a References-like heading
    in_refs = False
    for section in sections:
        heading = (section.get("heading") or "").strip().lower()
        if heading in ("references", "bibliography", "literature cited", "works cited"):
            in_refs = True
            for para in section["paragraphs"]:
                refs.extend(_split_numbered_refs(para))
        elif in_refs:
            break

    if refs:
        return refs

    # Strategy 2: Scan the last 30% of sections for paragraphs containing
    # sequential [N] citation patterns — the actual reference list.
    # Once we find the start (block with [1]), keep collecting continuation blocks.
    total_sections = len(sections)
    start_idx = max(0, total_sections - max(total_sections // 3, 5))
    found_ref_start = False
    max_ref_seen = 0

    for section in sections[start_idx:]:
        for para in section["paragraphs"]:
            extracted = _split_numbered_refs(para)
            if not extracted:
                continue

            # Get the reference numbers in this block
            block_nums = []
            for entry in extracted:
                m = re.match(r"\[(\d+)\]", entry)
                if m:
                    block_nums.append(int(m.group(1)))

            if not block_nums:
                continue

            if not found_ref_start:
                # Look for the start: low numbers, enough entries
                if min(block_nums) <= 5 and len(extracted) >= 3:
                    found_ref_start = True
                    max_ref_seen = max(block_nums)
                    refs.extend(extracted)
            else:
                # Continuation block: numbers should pick up where we left off
                # Accept if the lowest number in this block is near our max
                if min(block_nums) <= max_ref_seen + 5:
                    max_ref_seen = max(max(block_nums), max_ref_seen)
                    refs.extend(extracted)

    return refs


def _split_numbered_refs(text: str) -> list[str]:
    """Split a text block into individual numbered references."""
    entries = re.split(r"(?=\[\d+\])", text)
    results = []
    for entry in entries:
        entry = entry.strip()
        # Must start with [N] and be long enough to be a real reference
        if re.match(r"\[\d+\]", entry) and len(entry) > 20:
            results.append(entry)
    return results


def _extract_references_docx(sections: list[dict]) -> list[str]:
    """Same logic for DOCX."""
    return _extract_references_pdf(sections)  # Same heuristic works


def _rows_to_markdown_table(rows: list[list[str]]) -> str:
    """Convert table rows to markdown table format."""
    if not rows:
        return ""
    # Header row
    header = "| " + " | ".join(rows[0]) + " |"
    separator = "| " + " | ".join(["---"] * len(rows[0])) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])
    return f"{header}\n{separator}\n{body}"


def _write_parsed_text(
    sections: list[dict],
    references: list[str],
    metadata: dict,
    output_dir: Path,
) -> None:
    """Write normalized parsed_text.md."""
    lines = []
    lines.append("---")
    lines.append(f'title: "{metadata["title"]}"')
    lines.append(f'authors: "{metadata["authors"]}"')
    lines.append(f'source: "{metadata["source_path"]}"')
    lines.append(f'source_type: "{metadata["source_type"]}"')
    lines.append(f'pages: {metadata["pages"]}')
    lines.append(f'figures_extracted: {metadata["figures_extracted"]}')
    lines.append(f'tables_detected: {metadata["tables_detected"]}')
    lines.append("---")
    lines.append("")

    # Title
    lines.append(f"# {metadata['title']}")
    lines.append("")

    # Sections
    for section in sections:
        if section["heading"]:
            prefix = "#" * max(section["level"], 1)
            lines.append(f"{prefix} {section['heading']}")
            lines.append("")
        for para in section["paragraphs"]:
            lines.append(para)
            lines.append("")

    # Reference list
    if references:
        lines.append("## Extracted References")
        lines.append("")
        for i, ref in enumerate(references, 1):
            lines.append(f"{i}. {ref}")
        lines.append("")

    # Figure inventory
    figures_dir = output_dir / "figures"
    if figures_dir.exists():
        figs = sorted(figures_dir.glob("figure_*"))
        if figs:
            lines.append("## Figure Inventory")
            lines.append("")
            for fig in figs:
                lines.append(f"- `{fig.name}` — [extracted embedded image]")
            lines.append("")

    # Page renders inventory
    pages_dir = output_dir / "pages"
    if pages_dir.exists():
        pages = sorted(pages_dir.glob("page_*"))
        if pages:
            lines.append("## Page Renders (200 DPI)")
            lines.append("")
            for pg in pages:
                lines.append(f"- `{pg.name}`")
            lines.append("")

    parsed_path = output_dir / "parsed_text.md"
    parsed_path.write_text("\n".join(lines), encoding="utf-8")


def _write_metadata(metadata: dict, output_dir: Path) -> None:
    """Write metadata.json."""
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Paper ingestion for paper-review skill")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pdf", type=Path, help="Path to PDF file")
    group.add_argument("--docx", type=Path, help="Path to DOCX file")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    if args.pdf:
        if not args.pdf.exists():
            print(f"ERROR: PDF not found: {args.pdf}", file=sys.stderr)
            sys.exit(1)
        meta = ingest_pdf(args.pdf, args.output)
        print(f"PDF ingestion complete: {meta['title']}")
        print(f"  Pages: {meta['pages']}")
        print(f"  Figures extracted: {meta['figures_extracted']}")
        print(f"  Tables detected: {meta['tables_detected']}")
    elif args.docx:
        if not args.docx.exists():
            print(f"ERROR: DOCX not found: {args.docx}", file=sys.stderr)
            sys.exit(1)
        meta = ingest_docx(args.docx, args.output)
        print(f"DOCX ingestion complete: {meta['title']}")
        print(f"  Figures extracted: {meta['figures_extracted']}")
        print(f"  Tables detected: {meta['tables_detected']}")

    print(f"  Output: {args.output}")


if __name__ == "__main__":
    main()
