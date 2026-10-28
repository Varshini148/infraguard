"""
InfraGuard Reporting Engine (CSV and PDF)
Generates audit-ready compliance reports for municipal and infrastructure authorities.
Integrates defect telemetry, AUKF sensor evidence, risk levels, and repair rankings.
"""

import io
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.app.models.entities import Defect

def generate_csv_report(defects: List[Defect], filter_description: str = "All records") -> str:
    """Generate RFC 4180 compliant CSV string representing filtered defects."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header metadata
    writer.writerow(["# INFRAGUARD INFRASTRUCTURE DEFECT & MAINTENANCE AUDIT REPORT"])
    writer.writerow(["# Export Timestamp (UTC):", datetime.utcnow().isoformat()])
    writer.writerow(["# Applied Filter Scope:", filter_description])
    writer.writerow(["# Total Filtered Records:", len(defects)])
    writer.writerow([])

    # Column titles
    headers = [
        "Defect ID",
        "Category",
        "Defect Type",
        "Severity",
        "Risk Score (0-100)",
        "Risk Level",
        "Priority Rank",
        "Assessed Confidence",
        "Confidence Grade",
        "Sensor Supported",
        "Deterioration Status",
        "Latitude",
        "Longitude",
        "GPS Reliable",
        "Detection Timestamp",
        "Verification Status",
        "Urgency Days",
        "Priority Rationale"
    ]
    writer.writerow(headers)

    for d in defects:
        writer.writerow([
            d.id,
            d.category.upper(),
            d.defect_type,
            d.severity.upper(),
            f"{d.risk_score:.1f}",
            d.risk_level.upper(),
            d.repair_priority_rank,
            f"{d.assessed_confidence:.3f}",
            d.confidence_grade,
            "YES" if d.sensor_supported else "NO",
            d.deterioration_status,
            f"{d.lat:.6f}" if d.lat is not None else "N/A",
            f"{d.lng:.6f}" if d.lng is not None else "N/A",
            "RELIABLE" if d.gps_reliable else "UNRELIABLE/MISSING",
            d.timestamp.strftime("%Y-%m-%d %H:%M:%S") if d.timestamp else "N/A",
            d.verification_status,
            d.estimated_urgency_days,
            d.repair_priority_rationale or "N/A"
        ])

    return output.getvalue()


def generate_pdf_report(
    defects: List[Defect],
    output_path: str,
    filter_description: str = "Standard Scope"
) -> str:
    """
    Generate professional multi-page PDF inspection report using ReportLab.
    Includes executive summary, category breakdowns, detailed findings, and engineering disclaimers.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom Pastel-aligned typography
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b")
    )
    header_cell_style = ParagraphStyle(
        "HeaderCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a")
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph("INFRAGUARD — INFRASTRUCTURE INTEGRITY & REPAIR AUDIT", title_style))
    meta_text = (
        f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} &nbsp;|&nbsp; "
        f"<b>Filter Scope:</b> {filter_description} &nbsp;|&nbsp; "
        f"<b>Records Total:</b> {len(defects)}"
    )
    elements.append(Paragraph(meta_text, subtitle_style))
    elements.append(Spacer(1, 10))

    # Executive Summary Card
    crit_count = sum(1 for d in defects if d.risk_level.lower() == "critical")
    high_count = sum(1 for d in defects if d.risk_level.lower() == "high")
    sensor_count = sum(1 for d in defects if d.sensor_supported)
    worsening_count = sum(1 for d in defects if d.deterioration_status.lower() == "worsening")

    summary_data = [
        [
            Paragraph("<b>Total Defects Evaluated</b>", header_cell_style),
            Paragraph("<b>Critical Risk</b>", header_cell_style),
            Paragraph("<b>High Risk</b>", header_cell_style),
            Paragraph("<b>Sensor-Supported (AUKF)</b>", header_cell_style),
            Paragraph("<b>Active Worsening Trend</b>", header_cell_style),
        ],
        [
            Paragraph(f"<font size=12><b>{len(defects)}</b></font>", cell_style),
            Paragraph(f"<font size=12 color='#dc2626'><b>{crit_count}</b></font>", cell_style),
            Paragraph(f"<font size=12 color='#ea580c'><b>{high_count}</b></font>", cell_style),
            Paragraph(f"<font size=12 color='#0284c7'><b>{sensor_count}</b></font>", cell_style),
            Paragraph(f"<font size=12 color='#7c3aed'><b>{worsening_count}</b></font>", cell_style),
        ]
    ]

    t_summary = Table(summary_data, colWidths=[108, 108, 108, 108, 108])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 15))

    # Detailed Table
    table_rows = [
        [
            Paragraph("<b>ID / Rank</b>", header_cell_style),
            Paragraph("<b>Asset / Type</b>", header_cell_style),
            Paragraph("<b>Severity</b>", header_cell_style),
            Paragraph("<b>Risk (0-100)</b>", header_cell_style),
            Paragraph("<b>Confidence / Evidence</b>", header_cell_style),
            Paragraph("<b>Coordinates</b>", header_cell_style),
            Paragraph("<b>Action / Urgency</b>", header_cell_style)
        ]
    ]

    for d in defects[:40]:  # Up to 40 per report sheet
        coords_str = f"{d.lat:.4f}, {d.lng:.4f}" if d.lat and d.lng else "No GPS"
        sensor_tag = "<font color='#0284c7'>[Sensor-AUKF]</font>" if d.sensor_supported else "[Visual]"
        
        table_rows.append([
            Paragraph(f"<b>{d.id}</b><br/>Rank #{d.repair_priority_rank}", cell_style),
            Paragraph(f"<b>{d.category.upper()}</b><br/>{d.defect_type}", cell_style),
            Paragraph(f"<b>{d.severity.upper()}</b><br/>{d.deterioration_status}", cell_style),
            Paragraph(f"<b>{d.risk_score:.1f}</b><br/>({d.risk_level.title()})", cell_style),
            Paragraph(f"{int(d.assessed_confidence*100)}%<br/>{sensor_tag}", cell_style),
            Paragraph(coords_str, cell_style),
            Paragraph(f"Within {d.estimated_urgency_days}d<br/>{d.verification_status}", cell_style)
        ])

    t_details = Table(table_rows, colWidths=[65, 115, 65, 65, 85, 75, 70])
    t_details.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_details)
    elements.append(Spacer(1, 15))

    # Limitations & Legal Disclaimer
    disclaimer = (
        "<b>STATUTORY NOTICE & ENGINEERING LIMITATIONS:</b> This automated maintenance report synthesizes "
        "multimodal computer vision and adaptive sensor telemetry. AI detections and rule-based risk rankings "
        "support maintenance dispatch and triage but do not constitute structural certification or guaranteed "
        "failure prediction. On-site structural engineering verification by certified personnel is required "
        "before capital or structural interventions."
    )
    elements.append(Paragraph(disclaimer, subtitle_style))

    doc.build(elements)
    return output_path
