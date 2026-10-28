"""
InfraGuard Reports & Exports API Endpoints
Provides filtered CSV and executive PDF reports, and authority dashboard statistics.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database.connection import get_db
from backend.app.models.entities import (
    Defect, InfrastructureAsset, SensorDataset, DefectDuplicate, User
)
from backend.app.reporting.pdf_csv_reports import generate_csv_report, generate_pdf_report
from backend.app.detection.model_loader import model_loader
from backend.app.security.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports & Exports"])

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/summary")
def get_authority_dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns actual database-backed counts, category breakdowns, severity totals,
    sensor-supported figures, and recent defect records.
    """
    total_defects = db.query(Defect).count()
    crit_count = db.query(Defect).filter(Defect.risk_level == "critical").count()
    high_count = db.query(Defect).filter(Defect.risk_level == "high").count()
    med_count = db.query(Defect).filter(Defect.risk_level == "medium").count()
    low_count = db.query(Defect).filter(Defect.risk_level == "low").count()

    sensor_count = db.query(Defect).filter(Defect.sensor_supported == True).count()
    duplicates_count = db.query(DefectDuplicate).count()
    total_assets = db.query(InfrastructureAsset).count()
    sensor_datasets_count = db.query(SensorDataset).count()

    # Category counts
    cats = ["road", "bridge", "pipeline", "power_grid"]
    by_category = {}
    for c in cats:
        by_category[c] = db.query(Defect).filter(Defect.category == c).count()

    # Severity counts
    by_severity = {
        "critical": db.query(Defect).filter(Defect.severity == "critical").count(),
        "severe": db.query(Defect).filter(Defect.severity == "severe").count(),
        "moderate": db.query(Defect).filter(Defect.severity == "moderate").count(),
        "minor": db.query(Defect).filter(Defect.severity == "minor").count(),
    }

    # Verification counts
    by_verification = {
        "unverified": db.query(Defect).filter(Defect.verification_status == "unverified").count(),
        "pending_review": db.query(Defect).filter(Defect.verification_status == "pending_review").count(),
        "verified_by_inspection": db.query(Defect).filter(Defect.verification_status == "verified_by_inspection").count(),
        "rejected": db.query(Defect).filter(Defect.verification_status == "rejected").count()
    }

    # Deterioration counts
    by_deterioration = {
        "new": db.query(Defect).filter(Defect.deterioration_status == "new").count(),
        "stable": db.query(Defect).filter(Defect.deterioration_status == "stable").count(),
        "worsening": db.query(Defect).filter(Defect.deterioration_status == "worsening").count(),
        "unresolved": db.query(Defect).filter(Defect.deterioration_status == "unresolved").count(),
        "inconclusive": db.query(Defect).filter(Defect.deterioration_status == "inconclusive").count()
    }

    # Top recent defects
    recent = db.query(Defect).order_by(desc(Defect.timestamp)).limit(6).all()
    recent_list = []
    for d in recent:
        recent_list.append({
            "id": d.id,
            "category": d.category,
            "defect_type": d.defect_type,
            "severity": d.severity,
            "risk_score": d.risk_score,
            "risk_level": d.risk_level,
            "confidence_grade": d.confidence_grade,
            "sensor_supported": d.sensor_supported,
            "verification_status": d.verification_status,
            "timestamp": d.timestamp.isoformat()
        })

    # Model status overview
    model_statuses = {}
    for c in cats:
        model_statuses[c] = model_loader.get_model_status(c)["weight_status"]

    return {
        "total_defects": total_defects,
        "critical_risk": crit_count,
        "high_risk": high_count,
        "medium_risk": med_count,
        "low_risk": low_count,
        "total_assets": total_assets,
        "sensor_supported_count": sensor_count,
        "sensor_datasets_count": sensor_datasets_count,
        "duplicates_count": duplicates_count,
        "by_category": by_category,
        "by_severity": by_severity,
        "by_verification": by_verification,
        "by_deterioration": by_deterioration,
        "recent_defects": recent_list,
        "model_statuses": model_statuses
    }

@router.get("/csv")
def export_defects_csv(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    verification_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generate and download a filtered CSV report of defect telemetry."""
    q = db.query(Defect)
    filters = []
    if category:
        q = q.filter(Defect.category == category.lower())
        filters.append(f"Category={category}")
    if risk_level:
        q = q.filter(Defect.risk_level == risk_level.lower())
        filters.append(f"RiskLevel={risk_level}")
    if verification_status:
        q = q.filter(Defect.verification_status == verification_status.lower())
        filters.append(f"Verification={verification_status}")

    records = q.order_by(Defect.repair_priority_rank.asc()).all()
    filter_desc = ", ".join(filters) if filters else "All Infrastructure Records"

    csv_content = generate_csv_report(records, filter_description=filter_desc)
    filename = f"infraguard_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/pdf")
def export_defects_pdf(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    verification_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generate and download an official formatted PDF inspection report."""
    q = db.query(Defect)
    filters = []
    if category:
        q = q.filter(Defect.category == category.lower())
        filters.append(f"Category: {category.title()}")
    if risk_level:
        q = q.filter(Defect.risk_level == risk_level.lower())
        filters.append(f"Risk: {risk_level.title()}")
    if verification_status:
        q = q.filter(Defect.verification_status == verification_status.lower())
        filters.append(f"Verification: {verification_status}")

    records = q.order_by(Defect.repair_priority_rank.asc()).all()
    filter_desc = ", ".join(filters) if filters else "Comprehensive Scope (All Infrastructure)"

    pdf_filename = f"infraguard_authority_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = REPORTS_DIR / pdf_filename

    try:
        generate_pdf_report(records, str(pdf_path), filter_description=filter_desc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {str(e)}")

    return FileResponse(
        path=str(pdf_path),
        filename=pdf_filename,
        media_type="application/pdf"
    )
