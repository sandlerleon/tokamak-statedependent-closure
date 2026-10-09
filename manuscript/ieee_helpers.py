# -*- coding: utf-8 -*-
"""python-docx helpers that produce an IEEE-Transactions-style two-column manuscript: US Letter, 10 pt Times New Roman, title and authors across both columns,
roman-numeral section headings in small capitals, 'Fig.' and 'TABLE' captions, numbered equations, and full-width figure/table blocks."""
import re

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

import docx_helpers as H

FONT = "Times New Roman"
COL_W = 3.5          # column width, inches
GAP = 0.25
M_NS = H.M_NS


def _set_cols(section, num):
    sectPr = section._sectPr
    for c in sectPr.xpath("./w:cols"):
        sectPr.remove(c)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), str(num))
    if num > 1:
        cols.set(qn("w:space"), str(int(GAP * 1440)))
    sectPr.append(cols)


def new_document():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    st.font.size = Pt(10)
    pf = st.paragraph_format
    pf.line_spacing = 1.0
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin = sec.right_margin = Inches(0.625)
    sec.top_margin, sec.bottom_margin = Inches(0.75), Inches(1.0)
    _set_cols(sec, 1)
    return doc


def begin_two_columns(doc):
    sec = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_cols(sec, 2)
    return sec


def _one_col_block(doc):
    s = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_cols(s, 1)


def _resume_two(doc):
    s = doc.add_section(WD_SECTION.CONTINUOUS)
    _set_cols(s, 2)


class Wide:
    """Context manager: everything added inside spans both columns."""

    def __init__(self, doc):
        self.doc = doc

    def __enter__(self):
        _one_col_block(self.doc)

    def __exit__(self, *a):
        _resume_two(self.doc)


def title_block(doc, title, authors, affil_lines):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    H.add_rich(p, title, size=22)
    for r in p.runs:
        r.font.name = FONT
    q = doc.add_paragraph()
    q.alignment = WD_ALIGN_PARAGRAPH.CENTER
    H.add_rich(q, authors, size=11)
    q.paragraph_format.space_after = Pt(2)
    for line in affil_lines:
        a = doc.add_paragraph()
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        H.add_rich(a, line, size=9, italic=True)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)


def abstract(doc, text, index_terms):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run("Abstract—")
    r.bold = True
    r.italic = True
    r.font.size = Pt(9)
    H.add_rich(p, text, size=9, bold=True)
    p.paragraph_format.space_after = Pt(4)
    q = doc.add_paragraph()
    q.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = q.add_run("Index Terms—")
    r.bold = True
    r.italic = True
    r.font.size = Pt(9)
    rr = q.add_run(index_terms)
    rr.font.size = Pt(9)
    rr.bold = True
    q.paragraph_format.space_after = Pt(8)


def h1(doc, num, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run("%s. %s" % (num, text.upper()))
    r.font.size = Pt(10)
    return p


def back_heading(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text.upper())
    r.font.size = Pt(10)
    return p


def h2(doc, letter, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run("%s. " % letter)
    r.italic = True
    r2 = p.add_run(text)
    r2.italic = True
    return p


def body(doc, text, indent=True, size=10, align="justify"):
    p = doc.add_paragraph()
    H.add_rich(p, text, size=size)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if align == "justify" else WD_ALIGN_PARAGRAPH.LEFT
    if indent:
        p.paragraph_format.first_line_indent = Inches(0.17)
    p.paragraph_format.space_after = Pt(2)
    return p


def bullet_item(doc, text):
    p = doc.add_paragraph()
    H.add_rich(p, text, size=10)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.first_line_indent = Inches(-0.17)
    p.paragraph_format.space_after = Pt(1)
    return p


def fig_caption(doc, num, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run("Fig. %d. " % num)
    r.font.size = Pt(8)
    H.add_rich(p, text, size=8)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    return p


def figure(doc, path, width_in, alt=None, wide=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    run.add_picture(path, width=Inches(width_in))
    if alt:
        for dp in run._r.xpath(".//wp:docPr"):
            dp.set("descr", alt)
    return p


def table_caption(doc, roman, title):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.keep_with_next = True
    r = p.add_run("TABLE %s" % roman)
    r.font.size = Pt(8)
    q = doc.add_paragraph()
    q.alignment = WD_ALIGN_PARAGRAPH.CENTER
    q.paragraph_format.keep_with_next = True
    q.paragraph_format.space_after = Pt(3)
    H.add_rich(q, title, size=8)
    for rr in q.runs:
        rr.font.small_caps = True


def table(doc, rows, widths, size=8):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, wd in enumerate(widths):
        t.columns[j].width = Inches(wd)
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(0)
            H.add_rich(p, txt, size=size, bold=True if i == 0 else None)
            if i == 0:
                H.set_cell_shade(c, "E7ECF1")
            c.width = Inches(widths[j])
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)
    return t


def equation(doc, nodes, number):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.tab_stops.add_tab_stop(Inches(COL_W / 2), WD_TAB_ALIGNMENT.CENTER)
    pf.tab_stops.add_tab_stop(Inches(COL_W), WD_TAB_ALIGNMENT.RIGHT)
    pf.space_before = Pt(3)
    pf.space_after = Pt(3)
    pf.keep_together = True
    p._element.append(H._tab())
    p._element.append(parse_xml("<m:oMath %s>%s</m:oMath>" % (M_NS, H.render(nodes))))
    if number is not None:
        p._element.append(H._tab("(%d)" % number))
    return p


def reference(doc, num, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.first_line_indent = Inches(-0.3)
    p.paragraph_format.space_after = Pt(1)
    r = p.add_run("[%d]\t" % num)
    r.font.size = Pt(8)
    H.add_rich(p, text, size=8)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.3))
    return p


def footer_page_numbers(doc):
    sec = doc.sections[0]
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    for tag, attr, val in (("w:fldChar", "w:fldCharType", "begin"), ("w:instrText", "xml:space", "preserve"), ("w:fldChar", "w:fldCharType", "end")):
        el = OxmlElement(tag)
        el.set(qn(attr), val)
        if tag == "w:instrText":
            el.text = "PAGE"
        run._element.append(el)
    for r in fp.runs:
        r.font.size = Pt(9)
