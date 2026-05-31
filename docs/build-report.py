"""Generate docs/final-report.pdf from docs/final-report.md.

Lightweight markdown → PDF using reportlab. Run from repo root:

    pip install reportlab markdown
    python docs/build-report.py
"""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
SRC_MD = ROOT / "final-report.md"
OUT_PDF = ROOT / "final-report.pdf"


def _styles() -> dict:
    s = getSampleStyleSheet()
    base = ParagraphStyle(
        "body",
        parent=s["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    return {
        "title": ParagraphStyle(
            "title",
            parent=s["Title"],
            fontSize=20,
            leading=24,
            spaceAfter=12,
            textColor=colors.HexColor("#1f3a68"),
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=s["Heading1"],
            fontSize=15,
            leading=18,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor("#1f3a68"),
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=s["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#3a5fa8"),
        ),
        "h3": ParagraphStyle(
            "h3", parent=s["Heading3"], fontSize=11, leading=14, spaceBefore=8, spaceAfter=4
        ),
        "body": base,
        "code": ParagraphStyle(
            "code",
            parent=base,
            fontName="Courier",
            fontSize=8,
            leading=10,
            leftIndent=10,
            backColor=colors.HexColor("#f4f4f4"),
        ),
        "meta": ParagraphStyle(
            "meta", parent=base, fontSize=9, textColor=colors.HexColor("#666666")
        ),
    }


def _inline(text: str) -> str:
    """Convert markdown inline syntax to reportlab-friendly HTML-ish."""
    text = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


def _parse_table(lines: list[str], idx: int) -> tuple[Table, int]:
    """Parse a markdown table starting at lines[idx]; return (Table, new_idx)."""
    rows: list[list[str]] = []
    while idx < len(lines) and lines[idx].strip().startswith("|"):
        line = lines[idx].strip()
        if re.fullmatch(r"\|[\s\-:|]+\|", line):
            idx += 1
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
        idx += 1

    if not rows:
        return None, idx

    styles = _styles()
    body_style = ParagraphStyle("tbl", parent=styles["body"], fontSize=8, leading=10)
    head_style = ParagraphStyle(
        "tblh", parent=body_style, fontName="Helvetica-Bold", textColor=colors.white
    )

    rendered = []
    for r_i, row in enumerate(rows):
        style = head_style if r_i == 0 else body_style
        rendered.append([Paragraph(_inline(c), style) for c in row])

    table = Table(rendered, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a68")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#999999")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7fa")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table, idx


def md_to_flowables(md: str) -> list:
    styles = _styles()
    flow = []
    lines = md.split("\n")
    i = 0
    in_code = False
    code_buf: list[str] = []

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            if in_code:
                flow.append(
                    Paragraph("<br/>".join(code_buf).replace(" ", "&nbsp;"), styles["code"])
                )
                flow.append(Spacer(1, 4))
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            code_buf.append(safe)
            i += 1
            continue

        stripped = line.strip()

        if not stripped:
            flow.append(Spacer(1, 4))
            i += 1
            continue

        if stripped.startswith("# "):
            flow.append(Paragraph(_inline(stripped[2:]), styles["title"]))
        elif stripped.startswith("## "):
            flow.append(Paragraph(_inline(stripped[3:]), styles["h1"]))
        elif stripped.startswith("### "):
            flow.append(Paragraph(_inline(stripped[4:]), styles["h2"]))
        elif stripped.startswith("#### "):
            flow.append(Paragraph(_inline(stripped[5:]), styles["h3"]))
        elif stripped == "---":
            flow.append(Spacer(1, 6))
        elif stripped.startswith("|") and stripped.endswith("|"):
            tbl, i = _parse_table(lines, i)
            if tbl is not None:
                flow.append(tbl)
                flow.append(Spacer(1, 6))
            continue
        elif stripped.startswith(("- ", "* ", "1. ")):
            text = re.sub(r"^([-*]|\d+\.)\s+", "", stripped)
            flow.append(Paragraph(f"&bull;&nbsp; {_inline(text)}", styles["body"]))
        elif stripped.startswith(">"):
            flow.append(Paragraph(_inline(stripped.lstrip("> ")), styles["meta"]))
        else:
            flow.append(Paragraph(_inline(stripped), styles["body"]))

        i += 1

    return flow


def build() -> Path:
    md = SRC_MD.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="PDF Merger API — Final Rapor",
        author="demirhan",
    )
    flow = md_to_flowables(md)
    doc.build(flow)
    return OUT_PDF


if __name__ == "__main__":
    out = build()
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
