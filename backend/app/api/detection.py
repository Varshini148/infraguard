"""
InfraGuard AI Detection API Endpoints
Handles image uploads, video frame extraction, defect detection across 4 categories,
evidence storage, and model management.
"""

import os
import shutil
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.entities import User, Defect, MediaRecord, InfrastructureAsset
from backend.app.detection.model_loader import model_loader, CATEGORY_MODEL_SPECS
from backend.app.detection.image_detection import image_detection_service
from backend.app.detection.video_detection import video_detection_service
from backend.app.services.duplicate_detection import duplicate_detection_service
from backend.app.services.deterioration import deterioration_service
from backend.app.services.risk_prediction import risk_prediction_service
from backend.app.security.auth import get_current_user, log_audit_trail

router = APIRouter(prefix="/detection", tags=["AI Detection"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

@router.get("/models")
def get_registered_models():
    """Retrieve loading status, supported classes, license, and limitations for all 4 infrastructure models."""
    models_status = {}
    for cat in ["road", "bridge", "pipeline", "power_grid"]:
        models_status[cat] = model_loader.get_model_status(cat)
    return models_status

@router.post("/image")
async def detect_image(
    file: UploadFile = File(...),
    category: str = Form(...),
    asset_id: Optional[int] = Form(None),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    sensor_vibration: Optional[float] = Form(None),
    confidence_threshold: float = Form(0.25),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Upload an inspection image, run category-specific defect detection,
    render visual annotations, evaluate confidence, and persist defect evidence.
    """
    category = category.lower().strip()
    if category not in CATEGORY_MODEL_SPECS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Must be one of: {list(CATEGORY_MODEL_SPECS.keys())}"
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format '{ext}'. Allowed: {list(ALLOWED_IMAGE_EXTS)}"
        )

    # Save uploaded file
    unique_prefix = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    safe_filename = f"{unique_prefix}{ext}"
    dest_path = UPLOAD_DIR / safe_filename

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    file_size = dest_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="File size exceeds maximum 50MB limit.")

    # Create Media Record
    media = MediaRecord(
        file_path=str(dest_path),
        original_filename=file.filename,
        file_type="image",
        mime_type=file.content_type,
        file_size_bytes=file_size,
        frame_count=1,
        lat=lat,
        lng=lng,
        gps_reliable=(lat is not None and lng is not None),
        uploaded_by=current_user.id if current_user else None,
        created_at=datetime.utcnow()
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    # Run detection
    try:
        detection_result = image_detection_service.process_image(
            image_path=str(dest_path),
            category=category,
            confidence_threshold=confidence_threshold,
            lat=lat,
            lng=lng,
            sensor_vibration=sensor_vibration
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

    saved_defect_ids = []
    # Store detected defects in DB
    for det in detection_result["detections"]:
        defect_uuid = f"DEF-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
        
        defect = Defect(
            id=defect_uuid,
            asset_id=asset_id,
            media_id=media.id,
            category=category,
            defect_type=det["defect_type"],
            bounding_box=json.dumps(det["bounding_box"]),
            model_confidence=det["confidence"],
            assessed_confidence=det["assessed_confidence"],
            confidence_grade=det["confidence_grade"],
            confidence_rationale=det["confidence_rationale"],
            severity=det["severity"],
            sensor_supported=(sensor_vibration is not None and sensor_vibration > 1.8),
            lat=lat,
            lng=lng,
            gps_reliable=(lat is not None and lng is not None),
            timestamp=datetime.utcnow(),
            verification_status="unverified",
            deterioration_status="new",
            risk_score=50.0,
            risk_level="medium",
            repair_priority_rank=999
        )
        db.add(defect)
        db.commit()
        db.refresh(defect)

        # Baseline deterioration record
        deterioration_service.record_observation(db, defect, image_ref=detection_result["annotated_filename"])

        # Scan for duplicates
        duplicate_detection_service.scan_for_duplicates(db, defect)

        # Compute initial risk
        risk_prediction_service.calculate_risk(db, defect)

        saved_defect_ids.append(defect_uuid)

    if current_user:
        log_audit_trail(
            db, current_user.id, "IMAGE_DETECTION", "media_records", str(media.id),
            {"category": category, "detections_count": len(saved_defect_ids)}
        )

    return {
        "media_id": media.id,
        "annotated_filename": detection_result["annotated_filename"],
        "annotated_path": f"/processed/{detection_result['annotated_filename']}",
        "total_detections": len(detection_result["detections"]),
        "detections": detection_result["detections"],
        "model_used": detection_result["model_meta"]["name"],
        "model_status": detection_result["model_meta"]["weight_status"],
        "processing_time_ms": detection_result["model_meta"].get("processing_time_ms", 0),
        "saved_defect_ids": saved_defect_ids
    }

@router.post("/video")
async def detect_video(
    file: UploadFile = File(...),
    category: str = Form(...),
    asset_id: Optional[int] = Form(None),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    sampling_interval_sec: float = Form(1.0),
    max_frames: int = Form(15),
    confidence_threshold: float = Form(0.25),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Upload an inspection video, extract frames at specified intervals,
    run category AI defect detection, and collate findings across time.
    """
    category = category.lower().strip()
    if category not in CATEGORY_MODEL_SPECS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Must be one of: {list(CATEGORY_MODEL_SPECS.keys())}"
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{ext}'. Allowed: {list(ALLOWED_VIDEO_EXTS)}"
        )

    unique_prefix = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    safe_filename = f"{unique_prefix}{ext}"
    dest_path = UPLOAD_DIR / safe_filename

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")

    file_size = dest_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES * 2:  # 100MB for video
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Video exceeds maximum 100MB limit.")

    try:
        res = video_detection_service.process_video(
            video_path=str(dest_path),
            category=category,
            sampling_interval_sec=sampling_interval_sec,
            max_frames=max_frames,
            confidence_threshold=confidence_threshold,
            lat=lat,
            lng=lng
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")

    # Store media record
    media = MediaRecord(
        file_path=str(dest_path),
        original_filename=file.filename,
        file_type="video",
        mime_type=file.content_type,
        file_size_bytes=file_size,
        frame_count=res["extracted_frames_count"],
        duration_seconds=res["duration_seconds"],
        lat=lat,
        lng=lng,
        gps_reliable=(lat is not None and lng is not None),
        uploaded_by=current_user.id if current_user else None,
        created_at=datetime.utcnow()
    )
    db.add(media)
    db.commit()

    saved_defect_ids = []
    # Save unique defect detections from video
    for det in res["all_detections"]:
        defect_uuid = f"DEF-VID-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
        defect = Defect(
            id=defect_uuid,
            asset_id=asset_id,
            media_id=media.id,
            category=category,
            defect_type=det["defect_type"],
            bounding_box=json.dumps(det["bounding_box"]),
            model_confidence=det["confidence"],
            assessed_confidence=det["assessed_confidence"],
            confidence_grade=det["confidence_grade"],
            confidence_rationale=f"Video frame #{det.get('frame_index', 0)} ({det.get('timestamp_offset_sec', 0)}s)",
            severity=det["severity"],
            lat=lat,
            lng=lng,
            gps_reliable=(lat is not None and lng is not None),
            timestamp=datetime.utcnow(),
            verification_status="unverified",
            deterioration_status="new",
            risk_score=50.0,
            risk_level="medium",
            repair_priority_rank=999
        )
        db.add(defect)
        db.commit()
        db.refresh(defect)

        deterioration_service.record_observation(db, defect, image_ref=det.get("frame_evidence"))
        duplicate_detection_service.scan_for_duplicates(db, defect)
        risk_prediction_service.calculate_risk(db, defect)
        saved_defect_ids.append(defect_uuid)

    return {
        "media_id": media.id,
        "duration_seconds": res["duration_seconds"],
        "total_video_frames": res["total_video_frames"],
        "extracted_frames_count": res["extracted_frames_count"],
        "unique_detections_count": len(saved_defect_ids),
        "sampled_frames": [
            {
                "frame_index": sf["frame_index"],
                "timestamp_sec": sf["timestamp_sec"],
                "annotated_path": f"/processed/{Path(sf['annotated_path']).name}",
                "detections_count": sf["detections_count"]
            }
            for sf in res["sampled_frames"]
        ],
        "saved_defect_ids": saved_defect_ids
    }
