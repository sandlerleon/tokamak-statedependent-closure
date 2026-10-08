# -*- coding: utf-8 -*-
"""Shared python-docx helpers: native Word (OMML) equations, rich text with sub/superscripts,
captions, tables, figures and a PAGE-numbered footer. Used by the manuscript, the
Supplementary Information and the cover letter builders.

Springer asked for nothing unusual here, but equations built as native Word objects stay
editable and survive production, which is why they are used rather than images or styled text.
"""
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

FONT = "Times New Roman"
M_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"')


# ------------------------------------------------------------------ document set-up
def new_document(font=FONT, size=11, line=1.5, margins=1.0):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = font
    st.element.rPr.rFonts.set(qn("w:eastAsia"), font)
    st.font.size = Pt(size)
    st.paragraph_format.line_spacing = line
    st.paragraph_format.space_after = Pt(6)
    for s in doc.sections:
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(margins)
    for lvl, sz in ((1, 13), (2, 11.5), (3, 11)):
        h = doc.styles["Heading %d" % lvl]
        h.font.name = font
        h.element.rPr.rFonts.set(qn("w:eastAsia"), font)
        h.element.rPr.rFonts.set(qn("w:ascii"), font)
        h.element.rPr.rFonts.set(qn("w:hAnsi"), font)
        h.font.size = Pt(sz)
        h.font.bold = True
        h.font.italic = lvl == 3
        h.font.color.rgb = None
        h.paragraph_format.space_before = Pt(12 if lvl == 1 else 8)
        h.paragraph_format.space_after = Pt(4)
        h.paragraph_format.keep_with_next = True
    return doc


def page_numbers_and_line_numbers(doc, line_numbers=True):
    """Centred PAGE field in the footer; continuous line numbers (Springer asks for them)."""
    sec = doc.sections[0]
    sec.footer.is_linked_to_previous = False
    fp = sec.footer.paragraphs[0]
    for r in list(fp.runs):
        r._element.getparent().remove(r._element)
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    for tag, attr, val in (("w:fldChar", "w:fldCharType", "begin"), ("w:instrText", "xml:space", "preserve"),
                           ("w:fldChar", "w:fldCharType", "end")):
        el = OxmlElement(tag)
        el.set(qn(attr), val)
        if tag == "w:instrText":
            el.text = "PAGE"
        run._element.append(el)
    if line_numbers:
        pg = sec._sectPr
        ln = OxmlElement("w:lnNumType")
        ln.set(qn("w:countBy"), "1")
        ln.set(qn("w:restart"), "continuous")
        pg.append(ln)


# ------------------------------------------------------------------ rich text
# markup: *italic*  **bold**  _{sub}  ^{sup}  (also _x ^x for a single character)
TOK = re.compile(r"(\*\*.+?\*\*|\*.+?\*|_\{.+?\}|\^\{.+?\})")   # braced sub/superscripts only: file names like run_analysis.py stay intact


def add_rich(par, text, size=None, bold=None, italic=None, color=None):
    for piece in TOK.split(text):
        if not piece:
            continue
        r = None
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            r = par.add_run(piece[2:-2]); r.bold = True
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            r = par.add_run(piece[1:-1]); r.italic = True
        elif piece.startswith("_{") and piece.endswith("}"):
            r = par.add_run(piece[2:-1]); r.font.subscript = True
        elif piece.startswith("^{") and piece.endswith("}"):
            r = par.add_run(piece[2:-1]); r.font.superscript = True
        elif piece.startswith("_") and len(piece) == 2:
            r = par.add_run(piece[1]); r.font.subscript = True
        elif piece.startswith("^") and len(piece) == 2:
            r = par.add_run(piece[1]); r.font.superscript = True
        else:
            r = par.add_run(piece)
        if size:
            r.font.size = Pt(size)
        if bold is not None and not r.bold:
            r.bold = bold
        if italic is not None and not r.italic:
            r.italic = italic
        if color is not None:
            r.font.color.rgb = color
    return par


def para(doc, text, style=None, align=None, size=None, bold=None, italic=None, indent=None,
         space_after=None, keep_next=False):
    p = doc.add_paragraph(style=style)
    add_rich(p, text, size=size, bold=bold, italic=italic)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent is not None:
        p.paragraph_format.first_line_indent = Inches(indent)
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.keep_with_next = keep_next
    return p


def heading(doc, text, level=1):
    h = doc.add_heading(level=level)
    add_rich(h, text)
    for r in h.runs:
        r.font.name = FONT
        r.font.color.rgb = None
    return h


def bullet(doc, text, size=None):
    p = doc.add_paragraph(style="List Bullet")
    add_rich(p, text, size=size)
    p.paragraph_format.space_after = Pt(3)
    return p


# ------------------------------------------------------------------ captions, figures, tables
def caption(doc, text, size=9.5, keep_next=False):
    p = doc.add_paragraph()
    add_rich(p, text, size=size)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.keep_with_next = keep_next
    return p


def figure(doc, path, width_in=6.4, cap=None, alt=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    run.add_picture(path, width=Inches(width_in))
    if alt:
        for dp in run._r.xpath(".//wp:docPr"):
            dp.set("descr", alt)
    if cap:
        caption(doc, cap)


def set_cell_shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def table(doc, rows, widths=None, header=True, size=8.5, align_first_left=True):
    """rows: list of lists of str (rich markup allowed). First row is the header."""
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    if widths:
        # LibreOffice and Word both honour the grid, not just per-cell widths
        t.autofit = False
        for j, wd in enumerate(widths):
            t.columns[j].width = Inches(wd)
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(1)
            add_rich(p, txt, size=size, bold=True if (header and i == 0) else None)
            if header and i == 0:
                set_cell_shade(c, "E7ECF1")
            if widths:
                c.width = Inches(widths[j])
    if header:
        trPr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        th.set(qn("w:val"), "true")
        trPr.append(th)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# ------------------------------------------------------------------ native equations (OMML)
def _x(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CTRL = ('<m:ctrlPr><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:i/></w:rPr></m:ctrlPr>')


def T(text):                       # upright literal
    return [("t", text, "p")]


def V(text):                       # italic variable
    return [("t", text, "i")]


def SUB(b, s):
    return [("sub", b, s)]


def SUBSUP(b, s, p):
    return [("subsup", b, s, p)]


def SUP(b, s):
    return [("sup", b, s)]


def FRAC(n, d):
    return [("frac", n, d)]


def DELIM(inner, beg="(", end=")"):
    return [("d", inner, (beg, end))]


def SQRT(inner):
    return [("rad", inner)]


def Vs(name, sub):                 # italic variable with an upright descriptive subscript
    return SUB(V(name), T(sub))


def NARY(sym, sub, body):
    """n-ary operator (sum) with a subscript limit, e.g. a lattice sum."""
    return [("nary", sym, sub, body)]


def ABS(inner):
    return DELIM(inner, "|", "|")


def render(nodes):
    out = []
    for n in nodes:
        k = n[0]
        if k == "t":
            if n[2] == "i":
                mpr, wi = '<m:rPr><m:sty m:val="i"/></m:rPr>', "<w:i/>"
            else:
                mpr, wi = "<m:rPr><m:nor/></m:rPr>", '<w:i w:val="0"/>'
            out.append('<m:r>%s<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>%s</w:rPr>'
                       '<m:t xml:space="preserve">%s</m:t></m:r>' % (mpr, wi, _x(n[1])))
        elif k == "sub":
            out.append("<m:sSub><m:sSubPr>%s</m:sSubPr><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>" % (CTRL, render(n[1]), render(n[2])))
        elif k == "sup":
            out.append("<m:sSup><m:sSupPr>%s</m:sSupPr><m:e>%s</m:e><m:sup>%s</m:sup></m:sSup>" % (CTRL, render(n[1]), render(n[2])))
        elif k == "subsup":
            out.append("<m:sSubSup><m:sSubSupPr>%s</m:sSubSupPr><m:e>%s</m:e><m:sub>%s</m:sub><m:sup>%s</m:sup></m:sSubSup>" % (CTRL, render(n[1]), render(n[2]), render(n[3])))
        elif k == "frac":
            out.append("<m:f><m:fPr>%s</m:fPr><m:num>%s</m:num><m:den>%s</m:den></m:f>" % (CTRL, render(n[1]), render(n[2])))
        elif k == "d":
            beg, end = n[2]
            out.append('<m:d><m:dPr><m:begChr m:val="%s"/><m:endChr m:val="%s"/>%s</m:dPr><m:e>%s</m:e></m:d>'
                       % (_x(beg), _x(end), CTRL, render(n[1])))
        elif k == "nary":
            out.append('<m:nary><m:naryPr><m:chr m:val="%s"/><m:limLoc m:val="undOvr"/><m:supHide m:val="1"/>%s</m:naryPr><m:sub>%s</m:sub><m:sup/><m:e>%s</m:e></m:nary>'
                       % (_x(n[1]), CTRL, render(n[2]), render(n[3])))
        elif k == "rad":
            out.append("<m:rad><m:radPr><m:degHide m:val=\"1\"/>%s</m:radPr><m:deg/><m:e>%s</m:e></m:rad>" % (CTRL, render(n[1])))
    return "".join(out)


def _tab(text=""):
    return parse_xml('<w:r %s><w:tab/>%s</w:r>' % (M_NS, ('<w:t xml:space="preserve">%s</w:t>' % _x(text)) if text else ""))


def equation(doc, nodes, number):
    """Displayed OMML equation, centred, with the number aligned to the right margin."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.tab_stops.add_tab_stop(Inches(3.25), WD_TAB_ALIGNMENT.CENTER)
    pf.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT)
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    pf.keep_together = True
    p._element.append(_tab())
    p._element.append(parse_xml("<m:oMath %s>%s</m:oMath>" % (M_NS, render(nodes))))
    if number is not None:
        p._element.append(_tab("(%s)" % number))
    return p


# frequently used symbols
PI, PHI, BETA, ETA, KAPPA, XI, PSI, TAU, LAM, EPS, DELTA = (
    "π", "φ", "β", "η", "κ", "ξ", "ψ", "τ", "λ", "ε", "Δ")
EQ, PLUS, MINUS, TIMES = " = ", " + ", " − ", " × "
GE, LE = " ≥ ", " ≤ "
