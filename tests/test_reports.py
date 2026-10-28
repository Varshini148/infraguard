"""
Unit Tests for CSV and PDF Report Generation
"""

import os
import tempfile
from datetime import datetime
from backend.app.models.entities import Defect
from backend.app.reporting.pdf_csv_reports import generate_csv_report, generate_pdf_report

def test_csv_report_generation():
    defects = [
        Defect(
            id="DEF-CSV-01",
            category="road",
            defect_type="D40: Pothole",
            severity="critical",
            risk_score=85.0,
            risk_level="critical",
            repair_priority_rank=1,
            assessed_confidence=0.95,
            confidence_grade="High-confidence prediction",
            sensor_supported=True,
            deterioration_status="worsening",
            lat=11.4883,
            lng=77.8683,
            gps_reliable=True,
            timestamp=datetime.utcnow(),
            verification_status="verified_by_inspection",
            estimated_urgency_days=3,
            repair_priority_rationale="Urgent hazard"
        )
    ]

    csv_text = generate_csv_report(defects, filter_description="Test Filter Scope")
    assert "INFRAGUARD INFRASTRUCTURE DEFECT & MAINTENANCE AUDIT REPORT" in csv_text
    assert "DEF-CSV-01" in csv_text
    assert "D40: Pothole" in csv_text
    assert "85.0" in csv_text

def test_pdf_report_generation():
    defects = [
        Defect(
            id="DEF-PDF-01",
            category="bridge",
            defect_type="Concrete Spalling",
            severity="severe",
            risk_score=78.0,
            risk_level="high",
            repair_priority_rank=1,
            assessed_confidence=0.90,
            confidence_grade="High-confidence prediction",
            sensor_supported=False,
            deterioration_status="stable",
            lat=11.3530,
            lng=77.7281,
            gps_reliable=True,
            timestamp=datetime.utcnow(),
            verification_status="unverified",
            estimated_urgency_days=7,
            repair_priority_rationale="Bridge maintenance required"
        )
    ]

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name

    try:
        out_path = generate_pdf_report(defects, pdf_path, filter_description="Test PDF Report")
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 1000
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

def test_empty_reports_handling():
    csv_text = generate_csv_report([], filter_description="Empty Records")
    assert "Total Filtered Records:,0" in csv_text or "0" in csv_text

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name

    try:
        out_path = generate_pdf_report([], pdf_path, filter_description="Empty Records")
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 500
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
