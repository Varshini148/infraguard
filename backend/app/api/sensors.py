"""
InfraGuard Sensor Fusion & AUKF API Endpoints
Handles CSV telemetry ingestion, timestamp validation, AUKF non-linear filtering,
vibration anomaly identification, and sample sensor data generation.
"""

import os
import shutil
import io
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.entities import (
    User, SensorDataset, SensorMeasurement, AukfStateEstimate, Defect
)
from backend.app.sensor_fusion.aukf import sensor_fusion_service
from backend.app.security.auth import get_current_user, log_audit_trail

router = APIRouter(prefix="/sensors", tags=["Sensors & AUKF Fusion"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/datasets")
def list_sensor_datasets(db: Session = Depends(get_db)):
    """List all registered inspection sensor datasets."""
    datasets = db.query(SensorDataset).order_by(SensorDataset.created_at.desc()).all()
    results = []
    for d in datasets:
        results.append({
            "id": d.id,
            "original_filename": d.original_filename,
            "sensor_types": d.sensor_types.split(","),
            "sample_rate_hz": d.sample_rate_hz,
            "total_samples": d.total_samples,
            "status": d.status,
            "created_at": d.created_at.isoformat()
        })
    return results

@router.post("/upload")
async def upload_and_fuse_sensor_data(
    file: UploadFile = File(...),
    session_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Upload CSV sensor telemetry (GPS, Accelerometer, Speed, Vibration).
    Validates physical bounds, synchronizes streams, and runs AUKF fusion.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV sensor telemetry files are supported.")

    unique_filename = f"sensor_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    dest_path = UPLOAD_DIR / unique_filename

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save CSV file: {str(e)}")

    try:
        raw_df = pd.read_csv(dest_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {str(e)}")

    try:
        clean_df = sensor_fusion_service.parse_and_validate_sensor_data(raw_df)
        estimates, summary = sensor_fusion_service.run_aukf_fusion(clean_df)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"AUKF fusion validation error: {str(e)}")

    # Detect sensor types present
    types_found = []
    for col in ["lat", "speed_kmh", "accel_z", "vibration_level"]:
        if col in clean_df.columns and clean_df[col].dropna().count() > 0:
            types_found.append(col)

    dataset_record = SensorDataset(
        session_id=session_id,
        file_path=str(dest_path),
        original_filename=file.filename,
        sensor_types=",".join(types_found),
        sample_rate_hz=10.0,
        total_samples=len(clean_df),
        sync_timestamp_start=clean_df["timestamp"].iloc[0].to_pydatetime() if not clean_df.empty else datetime.utcnow(),
        status="processed",
        validation_notes=f"Processed {len(clean_df)} observations; {summary['anomalies_detected']} vibration anomalies identified."
    )
    db.add(dataset_record)
    db.commit()
    db.refresh(dataset_record)

    # Store estimates
    aukf_db_records = []
    for est in estimates:
        aukf_rec = AukfStateEstimate(
            sensor_dataset_id=dataset_record.id,
            timestamp=datetime.fromisoformat(est["timestamp"]),
            estimated_lat=est["estimated_lat"],
            estimated_lng=est["estimated_lng"],
            estimated_speed=est["estimated_speed_kmh"],
            anomaly_score=est["anomaly_score"],
            vibration_index=est["vertical_accel_mps2"],
            roughness_index=est["roughness_index"],
            confidence_factor=est["confidence_factor"],
            covariance_trace=est["covariance_trace"]
        )
        aukf_db_records.append(aukf_rec)

    db.bulk_save_objects(aukf_db_records)
    db.commit()

    if current_user:
        log_audit_trail(
            db, current_user.id, "SENSOR_AUKF_FUSION", "sensor_datasets", str(dataset_record.id),
            {"samples": len(clean_df), "anomalies": summary["anomalies_detected"]}
        )

    return {
        "dataset_id": dataset_record.id,
        "filename": file.filename,
        "sensor_types": types_found,
        "summary": summary,
        "first_estimates_preview": estimates[:50]
    }

@router.get("/{dataset_id}/estimates")
def get_dataset_estimates(dataset_id: int, limit: int = 200, db: Session = Depends(get_db)):
    """Fetch computed AUKF state trajectory and anomalies for a sensor dataset."""
    records = db.query(AukfStateEstimate).filter(
        AukfStateEstimate.sensor_dataset_id == dataset_id
    ).order_by(AukfStateEstimate.timestamp.asc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "lat": r.estimated_lat,
            "lng": r.estimated_lng,
            "speed_kmh": r.estimated_speed,
            "anomaly_score": r.anomaly_score,
            "roughness_index": r.roughness_index,
            "confidence_factor": r.confidence_factor,
            "covariance_trace": r.covariance_trace
        }
        for r in records
    ]

@router.get("/generate-sample-csv")
def generate_sample_sensor_csv():
    """
    Generates a realistic 10 Hz inspection trajectory CSV located along
    the Salem-Coimbatore Highway (NH 544), Tamil Nadu, India.
    Includes baseline engine vibrations and realistic pothole/crack impact spikes.
    """
    base_time = datetime.utcnow()
    # NH 544 corridor near Salem / Erode, Tamil Nadu
    start_lat = 11.6643
    start_lng = 78.1460
    
    samples = 150
    rows = ["timestamp,lat,lng,speed_kmh,accel_x,accel_y,accel_z,vibration_level"]
    
    curr_lat = start_lat
    curr_lng = start_lng
    
    for i in range(samples):
        t = base_time + timedelta(seconds=i * 0.1)
        speed = 45.0 + math.sin(i * 0.05) * 5.0
        
        # Advance position along highway
        curr_lat += 0.00004
        curr_lng += 0.00006
        
        # Accelerometer simulation
        # At sample 55 to 65: Simulate severe pothole impact
        if 55 <= i <= 65:
            az = round(4.8 + math.sin(i) * 2.2, 3)
            vib = round(3.4 + math.sin(i) * 1.5, 3)
        # At sample 110 to 118: Simulate bridge expansion joint bump
        elif 110 <= i <= 118:
            az = round(2.9 + math.cos(i) * 1.4, 3)
            vib = round(2.2 + math.cos(i) * 0.9, 3)
        else:
            # Baseline pavement texture
            az = round(0.15 + (math.sin(i * 0.3) * 0.25), 3)
            vib = round(0.35 + (math.cos(i * 0.2) * 0.15), 3)

        ax = round(math.sin(i * 0.1) * 0.1, 3)
        ay = round(math.cos(i * 0.1) * 0.1, 3)

        rows.append(f"{t.isoformat()},{curr_lat:.6f},{curr_lng:.6f},{speed:.1f},{ax},{ay},{az},{vib}")

    csv_data = "\n".join(rows)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=infraguard_tamil_nadu_sensor_sample.csv"}
    )
