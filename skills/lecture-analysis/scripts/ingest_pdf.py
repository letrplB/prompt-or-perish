#!/usr/bin/env python3
"""
ingest_pdf.py — deterministic first pass over a lecture PDF.

Outputs into <out>/00_ingest/:
  - pages/page-{NNN}.txt    per-page extracted text
  - pages/page-{NNN}.png    full-page render (omit with --light)
  - outline.json            PDF bookmarks / TOC
  - manifest.json           page count, image counts, render dpi, lengths

Idempotent: skips pages whose .txt and .png already exist unless --force.

Usage:
  ingest_pdf.py <pdf> <out_dir> [--dpi 144] [--light] [--force] [--max-pages N]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import pypdf
import fitz  # pymupdf


def extract_outline(reader: pypdf.PdfReader) -> list[dict]:
    out: list[dict] = []
    try:
        outl = reader.outline
    except Exception:
        return out

    def walk(items, depth=0):
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                try:
                    page = reader.get_destination_page_number(item)
                except Exception:
                    page = None
                out.append({
                    "depth": depth,
                    "title": getattr(item, "title", str(item)),
                    "page": page,
                })

    walk(outl)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out_dir")
    ap.add_argument("--dpi", type=int, default=144)
    ap.add_argument("--light", action="store_true",
                    help="text + outline only; skip page renders")
    ap.add_argument("--force", action="store_true",
                    help="re-render even if outputs exist")
    ap.add_argument("--max-pages", type=int, default=None)
    args = ap.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    base = Path(args.out_dir).resolve() / "00_ingest"
    pages_dir = base / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    reader = pypdf.PdfReader(str(pdf_path))
    md = reader.metadata or {}
    n_pages = len(reader.pages)
    if args.max_pages:
        n_pages = min(n_pages, args.max_pages)

    # Outline
    outline = extract_outline(reader)
    (base / "outline.json").write_text(json.dumps(outline, indent=2, ensure_ascii=False))

    # Per-page text via pypdf, page renders + image counts via pymupdf
    doc = fitz.open(str(pdf_path))
    page_records: list[dict] = []

    zoom = args.dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for i in range(n_pages):
        idx = i + 1
        txt_path = pages_dir / f"page-{idx:03d}.txt"
        png_path = pages_dir / f"page-{idx:03d}.png"

        # Text — prefer pymupdf (better layout preservation than pypdf for slides)
        if args.force or not txt_path.exists():
            text = doc[i].get_text("text") or ""
            txt_path.write_text(text)
        else:
            text = txt_path.read_text()

        # Page render
        if not args.light:
            if args.force or not png_path.exists():
                pix = doc[i].get_pixmap(matrix=matrix, alpha=False)
                pix.save(str(png_path))

        page_records.append({
            "page": idx,
            "text_len": len(text),
            "n_images": len(doc[i].get_images()),
            "rendered": not args.light,
        })

        if idx % 25 == 0 or idx == n_pages:
            print(f"  ingested {idx}/{n_pages}")

    manifest = {
        "pdf": str(pdf_path),
        "title": md.get("/Title", ""),
        "author": md.get("/Author", ""),
        "producer": md.get("/Producer", ""),
        "n_pages": n_pages,
        "render_dpi": None if args.light else args.dpi,
        "outline_entries": len(outline),
        "total_image_objects": sum(p["n_images"] for p in page_records),
        "pages": page_records,
    }
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"ingest complete · {n_pages} pages · outline {len(outline)} entries · "
          f"images {manifest['total_image_objects']} · "
          f"renders {'skipped' if args.light else 'on'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
