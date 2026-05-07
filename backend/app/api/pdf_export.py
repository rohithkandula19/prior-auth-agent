"""Render a Determination as a printable PDF."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.determination import Determination
from app.schemas.patient import Patient
from app.schemas.policy import Policy


STATUS_LABEL = {
    "met": "Met",
    "not_met": "Not met",
    "partial": "Partial",
    "insufficient_evidence": "Insufficient",
}


def render_pdf(
    determination: Determination,
    policy: Policy,
    patient: Patient,
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        title=f"Prior Auth Determination {determination.id}",
        author="Prior Auth Agent",
    )

    styles = getSampleStyleSheet()
    eyebrow = ParagraphStyle(
        "eyebrow",
        parent=styles["Normal"],
        fontSize=8,
        textColor=HexColor("#8a8472"),
        spaceAfter=4,
        leading=10,
    )
    h1 = ParagraphStyle(
        "h1",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        spaceAfter=14,
        textColor=HexColor("#111111"),
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=14,
        spaceAfter=6,
        textColor=HexColor("#111111"),
    )
    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
    )
    soft = ParagraphStyle(
        "soft",
        parent=body,
        textColor=HexColor("#6b6b6b"),
    )

    flow: list = []

    flow.append(Paragraph("Prior Authorization Determination", eyebrow))
    flow.append(
        Paragraph(
            f"{policy.procedure_name} &middot; {patient.id}",
            h1,
        )
    )

    decision_color = {
        "approved": HexColor("#1f7a4d"),
        "denied": HexColor("#b3261e"),
        "needs_more_info": HexColor("#a86b00"),
    }.get(determination.decision, HexColor("#111111"))

    summary_data = [
        ["Decision", "Confidence", "Latency", "Cost"],
        [
            f'<font color="{decision_color.hexval()}"><b>{determination.decision.replace("_", " ").title()}</b></font>',
            f"{determination.confidence:.2f}",
            f"{determination.latency_ms} ms",
            f"${determination.cost_usd:.4f}",
        ],
    ]
    summary_data[1] = [Paragraph(c, body) for c in summary_data[1]]
    summary_table = Table(summary_data, colWidths=[1.6 * inch] * 4)
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#8a8472")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, HexColor("#e8e6df")),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 1), (-1, 1), 6),
            ]
        )
    )
    flow.append(summary_table)

    flow.append(Paragraph("Recommended action", h2))
    flow.append(Paragraph(_safe(determination.recommended_action), body))

    if determination.gaps:
        flow.append(Paragraph("Documentation gaps", h2))
        for g in determination.gaps:
            flow.append(Paragraph(f"&bull; {_safe(g)}", body))

    flow.append(Paragraph("Criteria", h2))
    crit_by_id = {c.id: c for c in policy.criteria}
    for ev in determination.criterion_evaluations:
        crit = crit_by_id.get(ev.criterion_id)
        if not crit:
            continue
        title = _safe(crit.text.replace("\n", " ").strip()[:140])
        status = STATUS_LABEL.get(ev.status, ev.status)
        flow.append(
            Paragraph(
                f"<b>{crit.id}</b> &middot; {crit.type} &middot; "
                f"<b>{status}</b> &middot; {title}",
                body,
            )
        )
        if ev.reasoning:
            flow.append(Paragraph(_safe(ev.reasoning), soft))
        flow.append(Spacer(1, 4))

    flow.append(Paragraph("Citations", h2))
    flow.append(
        Paragraph(
            "Verbatim spans into the policy and chart text are preserved in "
            "the JSON record. Open the determination in the web UI for the "
            "interactive citation viewer.",
            soft,
        )
    )
    flow.append(
        Paragraph(
            f"Determination id: {determination.id} &middot; Generated {determination.created_at.isoformat()}",
            soft,
        )
    )

    doc.build(flow)
    return buf.getvalue()


def _safe(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
