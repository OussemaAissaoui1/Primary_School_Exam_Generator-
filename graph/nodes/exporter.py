"""Node 6: Export exam + correction PDFs matching the official Tunisian format."""

import os
import re
import urllib.request
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.platypus.flowables import Flowable

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"
FONT_DIR   = BASE_DIR / "fonts"
FONT_PATH  = FONT_DIR / "Amiri-Regular.ttf"
FONT_BOLD  = FONT_DIR / "Amiri-Bold.ttf"

PAGE_W, PAGE_H = A4
MARGIN_T = 2.0 * cm
MARGIN_B = 2.0 * cm
MARGIN_L = 2.5 * cm
MARGIN_R = 2.5 * cm
BODY_W   = PAGE_W - MARGIN_L - MARGIN_R   # usable width


# ── font setup ────────────────────────────────────────────────────────────────

def _ensure_font():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    if not FONT_PATH.exists():
        urllib.request.urlretrieve(
            "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf",
            str(FONT_PATH))
    if not FONT_BOLD.exists():
        try:
            urllib.request.urlretrieve(
                "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf",
                str(FONT_BOLD))
        except Exception:
            import shutil
            shutil.copy(str(FONT_PATH), str(FONT_BOLD))
    pdfmetrics.registerFont(TTFont("Amiri",     str(FONT_PATH)))
    pdfmetrics.registerFont(TTFont("Amiri-Bold", str(FONT_BOLD)))


# ── Arabic helper ─────────────────────────────────────────────────────────────

def _sanitize_html(text: str) -> str:
    """Remove or fix malformed HTML tags that ReportLab can't handle."""
    if not text:
        return ""
    # Remove bullet markers and HTML tags that cause issues
    text = re.sub(r'<br\s*/?>', ' ', text)  # Replace <br> with space
    text = re.sub(r'<[^>]+>', '', text)  # Remove all other HTML tags
    text = re.sub(r'[•|]', '', text)  # Remove bullet points and pipes
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()

def ar(text: str) -> str:
    if not text:
        return ""
    # Sanitize before reshaping
    text = _sanitize_html(str(text))
    return get_display(arabic_reshaper.reshape(text))


# ── Dotted answer line flowable ───────────────────────────────────────────────

class DottedLine(Flowable):
    """A row of dots across the page width — mimics student answer lines."""
    def __init__(self, width=BODY_W, dot_r=0.6, spacing=5):
        super().__init__()
        self.width  = width
        self.height = 8
        self.dot_r  = dot_r
        self.spacing = spacing

    def draw(self):
        self.canv.setFillColor(colors.black)
        x = 0
        while x < self.width:
            self.canv.circle(x, 3, self.dot_r, fill=1, stroke=0)
            x += self.spacing


# ── Style factory ─────────────────────────────────────────────────────────────

def _styles():
    base = dict(fontName="Amiri", wordWrap="RTL")
    def s(name, size, bold=False, align=TA_RIGHT, lead=None, sb=0, sa=0):
        fn = "Amiri-Bold" if bold else "Amiri"
        return ParagraphStyle(name, fontName=fn, fontSize=size,
                              alignment=align, leading=lead or size*1.6,
                              spaceBefore=sb, spaceAfter=sa, wordWrap="RTL")
    return {
        "center_bold": s("CB", 13, bold=True, align=TA_CENTER, lead=20),
        "center":      s("C",  11, align=TA_CENTER, lead=18),
        "right_bold":  s("RB", 11, bold=True),
        "right":       s("R",  11),
        "right_small": s("RS",  9),
        "left_small":  s("LS",  9, align=TA_LEFT),
        "exercise":    s("EX", 11, bold=True, sb=8, sa=2),
        "body_ans":    s("BA", 10, sb=2, sa=2),
        "solution":    s("SO", 10, sb=2, sa=2),
        "answer_bold": s("AB", 10, bold=True, sb=1),
        "table_cell":  s("TC", 9,  align=TA_CENTER, lead=13),
        "table_hdr":   s("TH", 9,  bold=True, align=TA_CENTER, lead=13),
    }


# ── Criteria score box (top right) ───────────────────────────────────────────

def _criteria_box(st: dict) -> Table:
    """Small bordered box: | معـ1 | معـ2 | معـ3 | معـ4 | معـ5 |"""
    criteria = ["معـ1", "معـ2", "معـ3", "معـ4", "معـ5"]
    header = [Paragraph(ar(c), st["table_hdr"]) for c in reversed(criteria)]
    empty  = [Paragraph("", st["table_cell"]) for _ in criteria]
    col_w  = 1.5 * cm
    t = Table([header, empty], colWidths=[col_w]*5,
              rowHeights=[0.55*cm, 0.7*cm])
    t.setStyle(TableStyle([
        ("GRID",       (0,0),(-1,-1), 0.5, colors.black),
        ("FONTNAME",   (0,0),(-1,-1), "Amiri"),
        ("FONTSIZE",   (0,0),(-1,-1), 8),
        ("ALIGN",      (0,0),(-1,-1), "CENTER"),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0),(-1,0),  colors.Color(0.92,0.92,0.95)),
    ]))
    return t


# ── Grading table (جدول إسناد الأعداد) ──────────────────────────────────────

def _grading_table(grading_schema: dict, st: dict) -> Table:
    """Build the full criteria grading table for the bottom of the PDF."""
    criteria = grading_schema.get("criteria", {})

    # Row labels (RTL: last column is first read)
    level_labels = [
        "انعدام التملك",
        "دون التملك الأدنى",
        "التملك الأدنى +-",
        "التملك الأقصى +++",
    ]
    level_keys = ["انعدام التملك", "دون التملك الأدنى", "التملك الأدنى", "التملك الأقصى"]

    crit_keys = ["معـ1", "معـ2", "معـ3", "معـ4", "معـ5"]

    # Header row 1: merged label + criterion names
    hdr1 = ([Paragraph(ar("المعايير"), st["table_hdr"])] +
            [Paragraph(ar(c), st["table_hdr"]) for c in reversed(crit_keys)])

    # Header row 2: مستوى التملك label + blanks
    hdr2 = ([Paragraph(ar("مستوى التملك"), st["table_hdr"])] +
            [Paragraph("", st["table_cell"]) for _ in crit_keys])

    rows = [hdr1, hdr2]

    for lvl_label, lvl_key in zip(level_labels, level_keys):
        row = [Paragraph(ar(lvl_label), st["table_cell"])]
        for ck in reversed(crit_keys):
            score = criteria.get(ck, {}).get("scores", {}).get(lvl_key, 0)
            row.append(Paragraph(ar(str(score)), st["table_cell"]))
        rows.append(row)

    col_widths = [5.5*cm] + [2.0*cm]*5
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("GRID",        (0,0),(-1,-1), 0.5,  colors.black),
        ("FONTNAME",    (0,0),(-1,-1), "Amiri"),
        ("FONTSIZE",    (0,0),(-1,-1), 9),
        ("ALIGN",       (0,0),(-1,-1), "CENTER"),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("BACKGROUND",  (0,0),(-1,1),  colors.Color(0.88,0.88,0.93)),
        ("BACKGROUND",  (0,0),(0,-1),  colors.Color(0.88,0.88,0.93)),
        ("ROWBACKGROUNDS", (0,2),(-1,-1),
         [colors.white, colors.Color(0.97,0.97,0.97)]),
    ]))
    return t


# ── Exam PDF builder ──────────────────────────────────────────────────────────

def _parse_exam_body(exam_text: str, instr_to_criterion: dict) -> list:
    """Return (type, text, criterion) tuples from raw exam text."""
    items = []
    for line in exam_text.split("\n"):
        s = line.strip()
        if not s:
            items.append(("blank", "", ""))
            continue
        if re.match(r'^تمرين\s*\d+', s):
            items.append(("exercise", s, ""))
        elif re.match(r'^(السند|سند)\s*', s):
            items.append(("support", s, ""))
        elif re.match(r'^(التعليمة|تعليمة)\s*\d+', s):
            # find criterion for this instruction
            m = re.match(r'^(التعليمة\s*\d+(?:-\d+)?)', s)
            label = m.group(1).strip() if m else ""
            criterion = instr_to_criterion.get(label, "")
            items.append(("instruction", s, criterion))
        else:
            items.append(("text", s, ""))
    return items


def _build_exam_elements(trimester: int, exam_text: str,
                          exam_structured: dict, grading_schema: dict,
                          st: dict) -> list:
    E = []
    instr_to_criterion = grading_schema.get("instr_to_criterion", {})

    # ── Header ────────────────────────────────────────────────────────────────
    E.append(Paragraph(ar("المدرسة الابتدائية"), st["center_bold"]))
    E.append(Paragraph(
        ar(f"السنة السادسة   —   تقييم مكتسبات التلاميذ في نهاية الثلاثي {trimester}"),
        st["center"]))
    E.append(Spacer(1, 3*mm))

    # Subject + score line (2-column)
    subj_table = Table(
        [[Paragraph(ar("العدد: 20"), st["right"]),
          Paragraph(ar("المادّة: رياضيات"), st["right"])]],
        colWidths=[BODY_W/2, BODY_W/2])
    subj_table.setStyle(TableStyle([
        ("ALIGN",  (0,0),(0,0), "LEFT"),
        ("ALIGN",  (1,0),(1,0), "RIGHT"),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
    ]))
    E.append(subj_table)
    E.append(HRFlowable(width="100%", thickness=0.8, color=colors.black))
    E.append(Spacer(1, 3*mm))

    # Student name line + criteria box (side by side)
    name_cell = Table(
        [[Paragraph(ar("الاسم و اللّقب: ..............................................................."), st["right"])]],
        colWidths=[BODY_W - 8.5*cm])
    crit_cell = _criteria_box(st)
    combo = Table([[crit_cell, name_cell]], colWidths=[8.5*cm, BODY_W - 8.5*cm])
    combo.setStyle(TableStyle([
        ("ALIGN",  (0,0),(0,0), "LEFT"),
        ("ALIGN",  (1,0),(1,0), "RIGHT"),
        ("VALIGN", (0,0),(-1,-1), "TOP"),
    ]))
    E.append(combo)
    E.append(Spacer(1, 2*mm))
    E.append(HRFlowable(width="100%", thickness=0.8, color=colors.black))
    E.append(Spacer(1, 5*mm))

    # ── Body ──────────────────────────────────────────────────────────────────
    items = _parse_exam_body(exam_text, instr_to_criterion)

    for item_type, text, criterion in items:
        if item_type == "blank":
            E.append(Spacer(1, 3*mm))
        elif item_type == "exercise":
            E.append(Spacer(1, 4*mm))
            E.append(Paragraph(ar(text), st["exercise"]))
            E.append(HRFlowable(width="100%", thickness=0.4,
                                color=colors.Color(0.6,0.6,0.6)))
        elif item_type == "support":
            E.append(Paragraph(ar(text), st["right_bold"]))
            E.append(Spacer(1, 2*mm))
        elif item_type == "instruction":
            # Instruction line: instruction text (right) + معيار label (left)
            crit_label = ar(criterion) if criterion else ""
            instr_row = Table(
                [[Paragraph(crit_label, st["left_small"]),
                  Paragraph(ar(text),   st["right"])]],
                colWidths=[2.0*cm, BODY_W - 2.0*cm])
            instr_row.setStyle(TableStyle([
                ("ALIGN",  (0,0),(0,0), "LEFT"),
                ("ALIGN",  (1,0),(1,0), "RIGHT"),
                ("VALIGN", (0,0),(-1,-1), "TOP"),
                ("TOPPADDING",    (0,0),(-1,-1), 2),
                ("BOTTOMPADDING", (0,0),(-1,-1), 2),
            ]))
            E.append(instr_row)
            # 2 dotted answer lines
            E.append(Spacer(1, 2*mm))
            E.append(DottedLine(width=BODY_W))
            E.append(Spacer(1, 5*mm))
            E.append(DottedLine(width=BODY_W))
            E.append(Spacer(1, 4*mm))
        else:
            E.append(Paragraph(ar(text), st["right"]))

    # ── Grading table at bottom ───────────────────────────────────────────────
    E.append(Spacer(1, 8*mm))
    E.append(HRFlowable(width="100%", thickness=0.8, color=colors.black))
    E.append(Spacer(1, 3*mm))
    E.append(Paragraph(ar("جدول إسناد الأعداد"), st["right_bold"]))
    E.append(Spacer(1, 3*mm))
    if grading_schema.get("criteria"):
        E.append(_grading_table(grading_schema, st))

    return E


# ── Correction PDF builder ────────────────────────────────────────────────────

def _build_correction_elements(trimester: int, correction: dict,
                                exam_structured: dict, grading_schema: dict,
                                st: dict) -> list:
    E = []

    # Header
    E.append(Paragraph(ar("عناصر الإجابة والتنقيط"), st["center_bold"]))
    E.append(Paragraph(
        ar(f"فرض مراقبة في الرياضيات — السنة السادسة — الثلاثي {trimester}"),
        st["center"]))
    E.append(HRFlowable(width="100%", thickness=0.8, color=colors.black))
    E.append(Spacer(1, 5*mm))

    correction_text = correction.get("text", "") if isinstance(correction, dict) else str(correction)

    current_exercise = None
    solution_lines: list[str] = []

    def _flush_solution():
        nonlocal solution_lines
        if solution_lines:
            block_lines = []
            for sl in solution_lines:
                sl = sl.strip()
                if not sl:
                    continue
                if sl.startswith("الجواب"):
                    block_lines.append(Paragraph(ar(sl), st["answer_bold"]))
                elif re.search(r'ن\s+(للعملية|للنتيجة|للجواب|لل)', sl):
                    block_lines.append(Paragraph(ar(sl), st["right_small"]))
                else:
                    block_lines.append(Paragraph(ar(sl), st["solution"]))
            if block_lines:
                # Light-gray shaded solution box
                inner_table = Table(
                    [[b] for b in block_lines],
                    colWidths=[BODY_W - 1.2*cm])
                inner_table.setStyle(TableStyle([
                    ("BACKGROUND", (0,0),(-1,-1), colors.Color(0.95,0.97,0.95)),
                    ("BOX",        (0,0),(-1,-1), 0.5, colors.Color(0.7,0.7,0.7)),
                    ("LEFTPADDING",  (0,0),(-1,-1), 6),
                    ("RIGHTPADDING", (0,0),(-1,-1), 6),
                    ("TOPPADDING",   (0,0),(-1,-1), 3),
                    ("BOTTOMPADDING",(0,0),(-1,-1), 3),
                ]))
                E.append(inner_table)
                E.append(Spacer(1, 3*mm))
            solution_lines = []

    for line in correction_text.split("\n"):
        s = line.strip()
        if re.match(r'^تمرين\s*\d+', s):
            _flush_solution()
            E.append(Spacer(1, 4*mm))
            E.append(Paragraph(ar(s), st["exercise"]))
            E.append(HRFlowable(width="100%", thickness=0.4,
                                color=colors.Color(0.6,0.6,0.6)))
            current_exercise = s
        elif re.match(r'^(التعليمة|تعليمة)\s*\d+', s):
            _flush_solution()
            E.append(Paragraph(ar(s), st["right_bold"]))
            E.append(Spacer(1, 1*mm))
        elif s:
            solution_lines.append(s)

    _flush_solution()

    # Grading table
    E.append(Spacer(1, 8*mm))
    E.append(HRFlowable(width="100%", thickness=0.8, color=colors.black))
    E.append(Spacer(1, 3*mm))
    E.append(Paragraph(ar("جدول إسناد الأعداد — عناصر الإجابة"), st["right_bold"]))
    E.append(Spacer(1, 3*mm))
    if grading_schema.get("criteria"):
        E.append(_grading_table(grading_schema, st))

    # Classic per-question grading table
    grading_table = correction.get("grading_table", []) if isinstance(correction, dict) else []
    if grading_table:
        E.append(Spacer(1, 6*mm))
        E.append(Paragraph(ar("توزيع النقاط"), st["right_bold"]))
        E.append(Spacer(1, 3*mm))
        header = [Paragraph(ar(h), st["table_hdr"])
                  for h in ["النقاط", "التعليمة", "التمرين"]]
        rows = [header]
        for entry in grading_table:
            rows.append([
                Paragraph(ar(f"{entry.get('points',0):g} ن"), st["table_cell"]),
                Paragraph(ar(entry.get("instruction", "")),   st["table_cell"]),
                Paragraph(ar(entry.get("exercise", "")),      st["table_cell"]),
            ])
        total = sum(e.get("points", 0) for e in grading_table)
        rows.append([
            Paragraph(ar(f"{total:g} ن"), st["right_bold"]),
            Paragraph("",                  st["table_cell"]),
            Paragraph(ar("المجموع"),       st["right_bold"]),
        ])
        pt = Table(rows, colWidths=[3.5*cm, 7*cm, 5*cm])
        pt.setStyle(TableStyle([
            ("GRID",       (0,0),(-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0),(-1,0),  colors.Color(0.88,0.88,0.93)),
            ("BACKGROUND", (0,-1),(-1,-1),colors.Color(0.95,0.95,0.85)),
            ("FONTNAME",   (0,0),(-1,-1), "Amiri"),
            ("FONTSIZE",   (0,0),(-1,-1), 9),
            ("ALIGN",      (0,0),(-1,-1), "CENTER"),
            ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ]))
        E.append(pt)

    return E


# ── PDF writer ────────────────────────────────────────────────────────────────

def _write_pdf(path: str, elements: list):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
    )
    doc.build(elements)


# ── LangGraph node ────────────────────────────────────────────────────────────

def exporter_node(state: dict) -> dict:
    """LangGraph node: render exam and correction as Arabic PDFs."""
    _ensure_font()
    st = _styles()

    trimester      = state["trimester"]
    exam_text      = state.get("exam_text", "")
    exam_structured = state.get("exam_structured", {})
    correction     = state.get("correction", {})
    grading_schema = state.get("grading_schema", {})

    exam_path  = str(OUTPUT_DIR / f"exam_T{trimester}.pdf")
    corr_path  = str(OUTPUT_DIR / f"correction_T{trimester}.pdf")

    _write_pdf(exam_path,  _build_exam_elements(
        trimester, exam_text, exam_structured, grading_schema, st))
    _write_pdf(corr_path, _build_correction_elements(
        trimester, correction, exam_structured, grading_schema, st))

    return {"exam_pdf_path": exam_path, "correction_pdf_path": corr_path}
