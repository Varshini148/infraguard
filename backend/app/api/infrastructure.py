"""
InfraGuard Infrastructure & Defect Management API Endpoints
Provides endpoints for asset tracking, defect filtering, verification workflows,
manual coordinate adjustments, duplicate resolution, and GeoJSON export.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database.connection import get_db
from backend.app.models.entities import (
    User, InfrastructureAsset, Defect, DefectDuplicate, DeteriorationTimeline, MediaRecord
)
from backend.app.schemas.domain import (
    AssetCreate, AssetResponse, DefectVerificationUpdate, DuplicateResolution
)
from backend.app.security.auth import get_current_user, require_roles, log_audit_trail
from backend.app.services.deterioration import deterioration_service
from backend.app.services.risk_prediction import risk_prediction_service

router = APIRouter(prefix="/infrastructure", tags=["Infrastructure & Defects"])

# Assets
@router.get("/assets", response_model=List[AssetResponse])
def list_assets(category: Optional[str] = None, db: Session = Depends(get_db)):
    """List infrastructure assets, optionally filtered by category."""
    q = db.query(InfrastructureAsset)
    if category:
        q = q.filter(InfrastructureAsset.category == category.lower())
    return q.all()

@router.post("/assets", response_model=AssetResponse)
def create_asset(
    payload: AssetCreate,
    current_user: User = Depends(require_roles(["admin", "inspector"])),
    db: Session = Depends(get_db)
):
    """Register a new infrastructure asset in the authority registry."""
    existing = db.query(InfrastructureAsset).filter(InfrastructureAsset.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Asset code already exists.")

    asset = InfrastructureAsset(
        name=payload.name,
        category=payload.category.lower(),
        code=payload.code,
        location_description=payload.location_description,
        lat=payload.lat,
        lng=payload.lng,
        importance_level=payload.importance_level.lower(),
        length_or_area=payload.length_or_area,
        year_built=payload.year_built,
        created_at=datetime.utcnow()
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset

# Defects
@router.get("/defects")
def list_defects(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    risk_level: Optional[str] = None,
    verification_status: Optional[str] = None,
    deterioration_status: Optional[str] = None,
    sensor_supported: Optional[bool] = None,
    has_coords_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Search and filter defect records.
    Filters: category, severity, risk level, verification status, sensor support, coordinates.
    """
    q = db.query(Defect)

    if category:
        q = q.filter(Defect.category == category.lower())
    if severity:
        q = q.filter(Defect.severity == severity.lower())
    if risk_level:
        q = q.filter(Defect.risk_level == risk_level.lower())
    if verification_status:
        q = q.filter(Defect.verification_status == verification_status.lower())
    if deterioration_status:
        q = q.filter(Defect.deterioration_status == deterioration_status.lower())
    if sensor_supported is not None:
        q = q.filter(Defect.sensor_supported == sensor_supported)
    if has_coords_only:
        q = q.filter(Defect.lat.isnot(None), Defect.lng.isnot(None), Defect.gps_reliable == True)

    total_count = q.count()
    records = q.order_by(Defect.repair_priority_rank.asc(), desc(Defect.timestamp)).offset(offset).limit(limit).all()

    items = []
    for d in records:
        bb = None
        if d.bounding_box:
            try:
                bb = json.loads(d.bounding_box) if isinstance(d.bounding_box, str) else d.bounding_box
            except Exception:
                pass
        
        media_path = None
        if d.media:
            # If processed file exists, use it
            media_path = f"/uploads/{Path(d.media.file_path).name}"

        items.append({
            "id": d.id,
            "asset_id": d.asset_id,
            "category": d.category,
            "defect_type": d.defect_type,
            "bounding_box": bb,
            "model_confidence": d.model_confidence,
            "assessed_confidence": d.assessed_confidence,
            "confidence_grade": d.confidence_grade,
            "confidence_rationale": d.confidence_rationale,
            "severity": d.severity,
            "sensor_supported": d.sensor_supported,
            "lat": d.lat,
            "lng": d.lng,
            "gps_reliable": d.gps_reliable,
            "timestamp": d.timestamp.isoformat(),
            "verification_status": d.verification_status,
            "verification_notes": d.verification_notes,
            "deterioration_status": d.deterioration_status,
            "risk_score": d.risk_score,
            "risk_level": d.risk_level,
            "repair_priority_rank": d.repair_priority_rank,
            "repair_priority_rationale": d.repair_priority_rationale,
            "estimated_urgency_days": d.estimated_urgency_days,
            "media_path": media_path
        })

    return {
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "items": items
    }

@router.get("/defects/{defect_id}")
def get_defect(defect_id: str, db: Session = Depends(get_db)):
    """Fetch complete metadata for a specific defect."""
    d = db.query(Defect).filter(Defect.id == defect_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Defect not found")

    bb = None
    if d.bounding_box:
        try:
            bb = json.loads(d.bounding_box) if isinstance(d.bounding_box, str) else d.bounding_box
        except Exception:
            pass

    media_path = f"/uploads/{Path(d.media.file_path).name}" if d.media else None

    return {
        "id": d.id,
        "asset_id": d.asset_id,
        "category": d.category,
        "defect_type": d.defect_type,
        "bounding_box": bb,
        "model_confidence": d.model_confidence,
        "assessed_confidence": d.assessed_confidence,
        "confidence_grade": d.confidence_grade,
        "confidence_rationale": d.confidence_rationale,
        "severity": d.severity,
        "sensor_supported": d.sensor_supported,
        "lat": d.lat,
        "lng": d.lng,
        "gps_reliable": d.gps_reliable,
        "timestamp": d.timestamp.isoformat(),
        "verification_status": d.verification_status,
        "verification_notes": d.verification_notes,
        "deterioration_status": d.deterioration_status,
        "risk_score": d.risk_score,
        "risk_level": d.risk_level,
        "repair_priority_rank": d.repair_priority_rank,
        "repair_priority_rationale": d.repair_priority_rationale,
        "estimated_urgency_days": d.estimated_urgency_days,
        "media_path": media_path
    }

@router.patch("/defects/{defect_id}/verification")
def update_verification(
    defect_id: str,
    payload: DefectVerificationUpdate,
    current_user: User = Depends(require_roles(["admin", "inspector", "analyst"])),
    db: Session = Depends(get_db)
):
    """
    Authorized personnel verification or rejection of an AI-flagged defect.
    Physical verification modifies confidence grade and audit logs.
    """
    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")

    new_status = payload.verification_status.lower()
    if new_status not in ["verified_by_inspection", "rejected", "pending_review", "unverified"]:
        raise HTTPException(status_code=400, detail="Invalid verification status")

    defect.verification_status = new_status
    defect.verification_notes = payload.verification_notes
    defect.verified_by_id = current_user.id

    if new_status == "verified_by_inspection":
        defect.confidence_grade = "Verified by authorized inspection"
        defect.assessed_confidence = 1.0
    elif new_status == "rejected":
        defect.assessed_confidence = 0.0

    # Recalculate risk score with updated verification
    risk_prediction_service.calculate_risk(db, defect)

    log_audit_trail(
        db, current_user.id, "DEFECT_VERIFICATION_UPDATE", "defects", defect.id,
        {"status": new_status, "notes": payload.verification_notes}
    )

    return {"message": "Verification status updated successfully", "defect_id": defect.id, "status": new_status}

@router.patch("/defects/{defect_id}/coordinates")
def update_defect_coordinates(
    defect_id: str,
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    current_user: User = Depends(require_roles(["admin", "inspector", "analyst"])),
    db: Session = Depends(get_db)
):
    """Authorized manual coordinate correction for GPS-less or offset field imagery."""
    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")

    defect.lat = lat
    defect.lng = lng
    defect.gps_reliable = True
    db.commit()

    log_audit_trail(
        db, current_user.id, "COORDINATES_UPDATE", "defects", defect.id,
        {"lat": lat, "lng": lng}
    )

    return {"message": "Coordinates updated successfully", "defect_id": defect.id, "lat": lat, "lng": lng}

@router.get("/defects/{defect_id}/timeline")
def get_defect_timeline(defect_id: str, db: Session = Depends(get_db)):
    """Fetch chronological deterioration progression for a defect."""
    return deterioration_service.get_defect_timeline(db, defect_id)

@router.get("/duplicates")
def list_duplicates(status: Optional[str] = None, db: Session = Depends(get_db)):
    """List auto-detected duplicate defect pairs and uncertain matches."""
    q = db.query(DefectDuplicate)
    if status:
        q = q.filter(DefectDuplicate.status == status)
    dups = q.order_by(DefectDuplicate.created_at.desc()).all()
    
    results = []
    for d in dups:
        results.append({
            "id": d.id,
            "primary_defect_id": d.primary_defect_id,
            "duplicate_defect_id": d.duplicate_defect_id,
            "distance_meters": d.distance_meters,
            "similarity_score": d.similarity_score,
            "match_type": d.match_type,
            "status": d.status,
            "notes": d.notes,
            "created_at": d.created_at.isoformat()
        })
    return results

@router.patch("/duplicates/{duplicate_id}")
def resolve_duplicate(
    duplicate_id: int,
    payload: DuplicateResolution,
    current_user: User = Depends(require_roles(["admin", "analyst"])),
    db: Session = Depends(get_db)
):
    """Confirm a duplicate pair or mark as distinct physical defects."""
    dup = db.query(DefectDuplicate).filter(DefectDuplicate.id == duplicate_id).first()
    if not dup:
        raise HTTPException(status_code=404, detail="Duplicate link not found")

    action = payload.action.lower()
    if action not in ["confirm_duplicate", "reject_distinct", "flag_uncertain"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    if action == "confirm_duplicate":
        dup.status = "confirmed_by_analyst"
        dup.notes = payload.notes or "Confirmed identical physical defect by analyst."
        # Optionally mark secondary defect as duplicate in verification
        sec = db.query(Defect).filter(Defect.id == dup.duplicate_defect_id).first()
        if sec:
            sec.verification_notes = f"Merged into primary defect {dup.primary_defect_id}"
            sec.parent_defect_id = dup.primary_defect_id
    elif action == "reject_distinct":
        dup.status = "rejected_distinct"
        dup.notes = payload.notes or "Confirmed distinct physical defects by analyst."

    db.commit()
    log_audit_trail(db, current_user.id, "RESOLVE_DUPLICATE", "defect_duplicates", str(dup.id), {"action": action})
    return {"message": "Duplicate resolution persisted", "status": dup.status}

@router.get("/geojson")
def get_geojson_defects(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Export verified and georeferenced defects as GeoJSON FeatureCollection."""
    q = db.query(Defect).filter(
        Defect.lat.isnot(None),
        Defect.lng.isnot(None),
        Defect.gps_reliable == True
    )
    if category:
        q = q.filter(Defect.category == category.lower())
    if risk_level:
        q = q.filter(Defect.risk_level == risk_level.lower())

    records = q.all()
    features = []
    for d in records:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [d.lng, d.lat]
            },
            "properties": {
                "id": d.id,
                "category": d.category,
                "defect_type": d.defect_type,
                "severity": d.severity,
                "risk_score": d.risk_score,
                "risk_level": d.risk_level,
                "priority_rank": d.repair_priority_rank,
                "confidence_grade": d.confidence_grade,
                "sensor_supported": d.sensor_supported,
                "deterioration_status": d.deterioration_status,
                "timestamp": d.timestamp.isoformat()
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }
