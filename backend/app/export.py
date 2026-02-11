"""Export functionality for analysis results (JSON, CSV, PDF)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import AnalysisResponse, AnalysisSummary, Finding


def export_json(response: AnalysisResponse) -> str:
    """Export analysis results as JSON."""
    return response.model_dump_json(indent=2)


def export_csv(findings: list[Finding]) -> str:
    """Export findings as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Confidence", "Category", "Title", "Date",
        "Source URL", "Summary", "Evidence", "Sentiment", "Importance",
    ])
    for f in findings:
        writer.writerow([
            f.confidence.value,
            f.category.value,
            f.title,
            f.date or "N/A",
            f.source_url,
            f.summary,
            "; ".join(f.evidence),
            f.sentiment.value,
            f.importance.value,
        ])
    return output.getvalue()


def export_pdf(response: AnalysisResponse) -> bytes:
    """Export analysis results as PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
    )

    elements = []

    # Title
    elements.append(Paragraph("Website Change Analysis Report", title_style))
    elements.append(Paragraph(f"URL: {response.url}", body_style))
    elements.append(Paragraph(f"Analysis period: Last {response.days} days", body_style))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        small_style,
    ))
    elements.append(Spacer(1, 20))

    # Summary
    if response.summary:
        elements.append(Paragraph("Summary", heading_style))
        summary = response.summary
        summary_data = [
            ["Total Findings", str(summary.total_findings)],
            ["Confirmed Recent", str(summary.confirmed_count)],
            ["Likely Recent", str(summary.likely_recent_count)],
        ]
        for cat, count in summary.category_breakdown.items():
            summary_data.append([cat, str(count)])

        table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

    # Findings
    if response.findings:
        elements.append(Paragraph("Detailed Findings", heading_style))
        for i, finding in enumerate(response.findings, 1):
            badge = finding.confidence.value
            elements.append(Paragraph(
                f"<b>#{i} [{badge}] {finding.category.value}</b>",
                body_style,
            ))
            elements.append(Paragraph(f"<b>{finding.title}</b>", body_style))
            if finding.date:
                elements.append(Paragraph(f"Date: {finding.date}", body_style))
            elements.append(Paragraph(f"URL: {finding.source_url}", small_style))
            elements.append(Paragraph(f"{finding.summary}", body_style))

            if finding.evidence:
                evidence_text = "Evidence: " + "; ".join(finding.evidence)
                elements.append(Paragraph(evidence_text, small_style))

            elements.append(Spacer(1, 10))

    # Disclaimer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "Disclaimer: This report is generated automatically. "
        "Dates and change detection are based on available metadata and heuristics. "
        "Results may not be 100% accurate.",
        small_style,
    ))

    doc.build(elements)
    return buffer.getvalue()
