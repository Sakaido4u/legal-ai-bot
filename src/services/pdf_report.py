"""Citation PDF report for one demo analysis run (reportlab)."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DISCLAIMER = "Research prototype - not legal advice."
LEVEL_COLORS = {"low": "#0ca30c", "medium": "#c98500", "high": "#d03b3b"}

_styles = getSampleStyleSheet()
TITLE = ParagraphStyle("ReportTitle", parent=_styles["Title"], fontSize=18, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=_styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=_styles["BodyText"], fontSize=10, leading=14)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=9, leading=12, textColor=colors.HexColor("#52514e"))
SCORE = ParagraphStyle("Score", parent=BODY, fontSize=28, leading=32, alignment=TA_CENTER)
SCORE_LABEL = ParagraphStyle("ScoreLabel", parent=SMALL, alignment=TA_CENTER)


def _p(text: str | None, style: ParagraphStyle = BODY) -> Paragraph:
    # Paragraph parses mini-HTML, so user/model text must be escaped.
    return Paragraph(escape(text or "").replace("\n", "<br/>"), style)


def _format_time(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    except (TypeError, ValueError):
        return iso or ""


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(colors.HexColor("#52514e"))
    canvas.drawString(doc.leftMargin, 12 * mm, DISCLAIMER)
    canvas.drawRightString(A4[0] - doc.rightMargin, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report_pdf(result: dict) -> bytes:
    """Render a load_demo_result() dict as PDF bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title="Compliance analysis report",
        author="Legal AI Compliance Assistant",
    )
    level = str(result.get("risk_level", "low")).lower()
    level_color = colors.HexColor(LEVEL_COLORS.get(level, "#52514e"))

    story = [
        Paragraph("Compliance Analysis Report", TITLE),
        _p(
            "  ·  ".join(
                [
                    f"Generated: {_format_time(result.get('created_at'))}",
                    f"User: {result.get('username', '')}",
                    f"Regulation: {result.get('regulation', 'ALL')}",
                    f"Report #{result.get('id', '')}",
                ]
            ),
            SMALL,
        ),
        Paragraph("Query", H2),
        _p(result.get("query")),
        Paragraph("Risk assessment", H2),
    ]

    score_cell = [
        Paragraph(f'<font color="{LEVEL_COLORS.get(level, "#52514e")}">{int(result.get("risk_score", 0))}</font>'
                  "<font size=12> / 100</font>", SCORE),
        _p("risk score", SCORE_LABEL),
    ]
    level_cell = [
        Paragraph(f'<font color="{LEVEL_COLORS.get(level, "#52514e")}"><b>{escape(level.upper())}</b></font>',
                  ParagraphStyle("Lvl", parent=SCORE, fontSize=20, leading=24)),
        _p("risk level", SCORE_LABEL),
    ]
    risk_table = Table([[score_cell, level_cell]], colWidths=[85 * mm, 85 * mm])
    risk_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, level_color),
                ("LINEAFTER", (0, 0), (0, 0), 0.5, colors.HexColor("#e4e3df")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [
        risk_table,
        Spacer(1, 3),
        _p("Peak heuristic risk across the cited passages (keyword-based; see methodology).", SMALL),
        Paragraph("Answer", H2),
        _p(result.get("answer")),
        Paragraph("Citations", H2),
    ]

    citations = result.get("citations") or []
    threshold = float(result.get("threshold", 0.5))
    if not citations:
        story.append(_p(f"No sources scored above the {threshold:.0%} relevance threshold.", SMALL))
    else:
        story.append(_p(f"Sources with relevance score above {threshold:.0%} (cosine similarity).", SMALL))
        for n, c in enumerate(citations, start=1):
            heading = f"{n}. [{c.get('citation_id', '')}] {c.get('jurisdiction', '')}"
            if c.get("section"):
                heading += f" - {c['section']}"
            block = [
                Spacer(1, 6),
                _p(heading, ParagraphStyle("CitHead", parent=BODY, fontName="Helvetica-Bold")),
                _p(f"Relevance: {float(c.get('score', 0)):.1%}    Source: {c.get('document', '')}", SMALL),
                _p(c.get("excerpt"), BODY),
            ]
            story.append(KeepTogether(block))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
