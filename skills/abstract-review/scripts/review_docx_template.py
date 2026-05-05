"""
Template script for conference abstract review.

This script is a TEMPLATE — not meant to be run directly. The abstract-review
skill uses this as a starting point, then customizes the comments, tracked
changes, and revised text for each specific abstract.

Usage pattern:
  1. Copy this template
  2. Replace the CUSTOMIZE sections with actual review content
  3. Run the script to produce the reviewed .docx

Requirements: python-docx, lxml (installed with python-docx)
"""

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from lxml import etree
from copy import deepcopy
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION — Customize per review
# ═══════════════════════════════════════════════════════════════════════

INPUT_FILE = "Abstract.docx"                    # CUSTOMIZE: input file path
OUTPUT_FILE = "Abstract_REVIEWED.docx"          # CUSTOMIZE: output file path
REVIEWER_NAME = "Reviewer Name"                 # CUSTOMIZE: reviewer attribution
REVIEWER_INITIALS = "RN"                        # CUSTOMIZE: derived from name

# ═══════════════════════════════════════════════════════════════════════
# XML INFRASTRUCTURE — Do not modify
# ═══════════════════════════════════════════════════════════════════════

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DATE = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

COMMENTS_URI = "/word/comments.xml"
COMMENTS_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
COMMENTS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"

doc = Document(INPUT_FILE)
comments_xml = etree.Element(f"{{{W}}}comments", nsmap={"w": W, "r": R})
comment_id_counter = [0]


def make_comment_id():
    """Generate a unique comment ID."""
    cid = comment_id_counter[0]
    comment_id_counter[0] += 1
    return str(cid)


def add_comment_to_xml(comment_id, text):
    """Add a comment entry to the comments.xml structure."""
    c = etree.SubElement(comments_xml, f"{{{W}}}comment")
    c.set(f"{{{W}}}id", comment_id)
    c.set(f"{{{W}}}author", REVIEWER_NAME)
    c.set(f"{{{W}}}date", DATE)
    c.set(f"{{{W}}}initials", REVIEWER_INITIALS)
    p = etree.SubElement(c, f"{{{W}}}p")
    r_el = etree.SubElement(p, f"{{{W}}}r")
    t = etree.SubElement(r_el, f"{{{W}}}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text


def wrap_runs_with_comment(paragraph_element, anchor_text, comment_text):
    """
    Anchor a comment to a specific text range within a paragraph.

    Args:
        paragraph_element: The lxml element of the paragraph (use para._element)
        anchor_text: The text string to anchor the comment to
        comment_text: The review comment text

    Returns:
        True if comment was successfully anchored, False if anchor text not found.
    """
    comment_id = make_comment_id()
    add_comment_to_xml(comment_id, comment_text)

    runs = paragraph_element.findall(f".//{{{W}}}r")
    full_text = ""
    run_map = []
    for run in runs:
        t_el = run.find(f"{{{W}}}t")
        if t_el is not None and t_el.text:
            start_idx = len(full_text)
            full_text += t_el.text
            run_map.append((run, start_idx, len(full_text)))

    pos = full_text.find(anchor_text)
    if pos == -1:
        print(f"  WARNING: Could not find '{anchor_text[:50]}...' in paragraph")
        return False

    end_pos = pos + len(anchor_text)

    first_run = None
    last_run = None
    for run, s, e in run_map:
        if s < end_pos and e > pos:
            if first_run is None:
                first_run = run
            last_run = run

    if first_run is None:
        return False

    # Insert commentRangeStart before first matching run
    range_start = etree.Element(f"{{{W}}}commentRangeStart")
    range_start.set(f"{{{W}}}id", comment_id)
    first_run.addprevious(range_start)

    # Insert commentRangeEnd after last matching run
    range_end = etree.Element(f"{{{W}}}commentRangeEnd")
    range_end.set(f"{{{W}}}id", comment_id)
    last_run.addnext(range_end)

    # Insert comment reference run after the range end
    ref_run = etree.Element(f"{{{W}}}r")
    rpr = etree.SubElement(ref_run, f"{{{W}}}rPr")
    rstyle = etree.SubElement(rpr, f"{{{W}}}rStyle")
    rstyle.set(f"{{{W}}}val", "CommentReference")
    cr = etree.SubElement(ref_run, f"{{{W}}}commentReference")
    cr.set(f"{{{W}}}id", comment_id)
    range_end.addnext(ref_run)

    print(f"  Comment #{comment_id}: {comment_text[:70]}...")
    return True


def tracked_replace(paragraph, old_text, new_text, rev_id_start):
    """
    Replace text using tracked changes (w:del + w:ins) attributed to the reviewer.

    Args:
        paragraph: The python-docx paragraph object (or lxml element)
        old_text: Text to delete (shown as strikethrough)
        new_text: Text to insert (shown as colored insertion)
        rev_id_start: Starting revision ID (increments by 2: one for del, one for ins)

    Returns:
        Next available revision ID.
    """
    p_el = paragraph._element if hasattr(paragraph, '_element') else paragraph

    runs = p_el.findall(f".//{{{W}}}r")
    full_text = ""
    run_map = []
    for run in runs:
        t_el = run.find(f"{{{W}}}t")
        if t_el is not None and t_el.text:
            start_idx = len(full_text)
            full_text += t_el.text
            run_map.append((run, start_idx, len(full_text), t_el))

    pos = full_text.find(old_text)
    if pos == -1:
        print(f"  WARNING: Could not find '{old_text}' for tracked replace")
        return rev_id_start

    end_pos = pos + len(old_text)

    affected = []
    for run, s, e, t_el in run_map:
        if s < end_pos and e > pos:
            affected.append((run, s, e, t_el))

    if not affected:
        return rev_id_start

    first_run, first_s, first_e, first_t = affected[0]
    last_run, last_s, last_e, last_t = affected[-1]

    # Preserve run formatting
    rpr_source = first_run.find(f"{{{W}}}rPr")
    rpr_copy = deepcopy(rpr_source) if rpr_source is not None else None

    prefix = full_text[first_s:pos]
    suffix = full_text[end_pos:last_e]

    insert_point = first_run

    # Prefix text (unchanged portion before the match)
    if prefix:
        pre_run = etree.Element(f"{{{W}}}r")
        if rpr_copy is not None:
            pre_run.append(deepcopy(rpr_copy))
        pre_t = etree.SubElement(pre_run, f"{{{W}}}t")
        pre_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        pre_t.text = prefix
        insert_point.addprevious(pre_run)

    # Deletion markup
    del_el = etree.Element(f"{{{W}}}del")
    del_el.set(f"{{{W}}}id", str(rev_id_start))
    del_el.set(f"{{{W}}}author", REVIEWER_NAME)
    del_el.set(f"{{{W}}}date", DATE)
    del_run = etree.SubElement(del_el, f"{{{W}}}r")
    if rpr_copy is not None:
        del_run.append(deepcopy(rpr_copy))
    del_text = etree.SubElement(del_run, f"{{{W}}}delText")
    del_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    del_text.text = old_text
    insert_point.addprevious(del_el)

    # Insertion markup
    ins_el = etree.Element(f"{{{W}}}ins")
    ins_el.set(f"{{{W}}}id", str(rev_id_start + 1))
    ins_el.set(f"{{{W}}}author", REVIEWER_NAME)
    ins_el.set(f"{{{W}}}date", DATE)
    ins_run = etree.SubElement(ins_el, f"{{{W}}}r")
    if rpr_copy is not None:
        ins_run.append(deepcopy(rpr_copy))
    ins_t = etree.SubElement(ins_run, f"{{{W}}}t")
    ins_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    ins_t.text = new_text
    insert_point.addprevious(ins_el)

    # Suffix text (unchanged portion after the match)
    if suffix:
        suf_run = etree.Element(f"{{{W}}}r")
        if rpr_copy is not None:
            suf_run.append(deepcopy(rpr_copy))
        suf_t = etree.SubElement(suf_run, f"{{{W}}}t")
        suf_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        suf_t.text = suffix
        insert_point.addprevious(suf_run)

    # Remove original affected runs
    for run, s, e, t_el in affected:
        run.getparent().remove(run)

    print(f"  Tracked: '{old_text}' → '{new_text}'")
    return rev_id_start + 2


# ═══════════════════════════════════════════════════════════════════════
# REVIEW CONTENT — CUSTOMIZE everything below
# ═══════════════════════════════════════════════════════════════════════

paras = doc.paragraphs
rev_id = 100  # Start high to avoid ID collisions

# ── Comments ──────────────────────────────────────────────────────────
# Template: wrap_runs_with_comment(paras[N]._element, "anchor text", "Comment text")
#
# Example:
# wrap_runs_with_comment(
#     paras[0]._element,
#     "some text in the title",
#     "Title is too long. Consider shortening."
# )

# CUSTOMIZE: Add your comments here
# ...

# ── Tracked Changes ──────────────────────────────────────────────────
# Template: rev_id = tracked_replace(paras[N], "old text", "new text", rev_id)
#
# Example:
# rev_id = tracked_replace(paras[3], "consuming", "concerning", rev_id)

# CUSTOMIZE: Add your tracked changes here
# ...


# ═══════════════════════════════════════════════════════════════════════
# SAVE WITH COMMENTS — Do not modify
# ═══════════════════════════════════════════════════════════════════════

# Serialize and attach comments.xml
comments_bytes = etree.tostring(
    comments_xml, xml_declaration=True, encoding="UTF-8", standalone=True
)
doc_part = doc.part
comments_part = Part(
    PackURI(COMMENTS_URI),
    COMMENTS_CT,
    comments_bytes,
    doc_part.package,
)
doc_part.relate_to(comments_part, COMMENTS_REL)

# Enable track changes in document settings
settings_el = doc.settings.element
etree.SubElement(settings_el, f"{{{W}}}trackChanges")


# ═══════════════════════════════════════════════════════════════════════
# APPEND REVISED VERSION — CUSTOMIZE the revised text below
# ═══════════════════════════════════════════════════════════════════════

def add_run(paragraph, text, bold=False, italic=False, size=Pt(12),
            font_name="Arial", color=None):
    """Helper to add a formatted run to a paragraph."""
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = size
    run.font.name = font_name
    if color:
        run.font.color.rgb = color
    return run


# ── Divider ──
doc.add_paragraph()
divider = doc.add_paragraph()
divider.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = divider.add_run("— " * 30)
r.font.size = Pt(12)
r.font.name = "Arial"
r.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

# ── Header ──
header = doc.add_paragraph()
header.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_run(header, "REVISED VERSION", bold=True, size=Pt(14),
        color=RGBColor(0x00, 0x66, 0xCC))

note = doc.add_paragraph()
note.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_run(note, f"(Suggested redraft — review by {REVIEWER_NAME})",
        italic=True, size=Pt(10), color=RGBColor(0x66, 0x66, 0x66))

doc.add_paragraph()

# ── Revised Title ──
# CUSTOMIZE: Rewrite the title
title_p = doc.add_paragraph()
add_run(title_p, "Revised Title Here", bold=True, size=Pt(14))

# ── Authors (usually unchanged) ──
auth_p = doc.add_paragraph()
add_run(auth_p, "Author List Here", italic=True, size=Pt(12))

# ── Affiliations ──
aff_p = doc.add_paragraph()
add_run(aff_p, "Affiliations Here", size=Pt(12))

doc.add_paragraph()

# ── Revised abstract body ──
# CUSTOMIZE: Write the revised abstract in logical paragraphs
# Match the original font (typically Arial 12pt for body, 14pt bold for title)
#
# Example:
# p1 = doc.add_paragraph()
# add_run(p1, "First paragraph of the revised abstract...", size=Pt(12))
#
# p2 = doc.add_paragraph()
# add_run(p2, "Second paragraph...", size=Pt(12))

# ── Revised figure caption (if applicable) ──
# fig_p = doc.add_paragraph()
# add_run(fig_p, "Figure 1: ...", italic=True, size=Pt(11))

# ── References (keep original, same numbering) ──
# doc.add_paragraph()
# ref_header = doc.add_paragraph()
# add_run(ref_header, "References:", size=Pt(12))
# for ref_text in ["[1] ...", "[2] ...", ...]:
#     rp = doc.add_paragraph(style="List Paragraph")
#     add_run(rp, ref_text, size=Pt(12))


# ═══════════════════════════════════════════════════════════════════════
# SAVE FINAL — Do not modify
# ═══════════════════════════════════════════════════════════════════════

doc.save(OUTPUT_FILE)
print(f"\nSaved reviewed document to: {OUTPUT_FILE}")
