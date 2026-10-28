"""
InfraGuard Database Entity Models
Defines all SQL schemas for users, infrastructure assets, inspections,
sensor fusion, AI detections, defects, duplicates, deterioration, risk, and audit.
"""

from datetime import datetime
import json
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(30), default="analyst", nullable=False)  # 'admin', 'inspector', 'analyst'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    inspections = relationship("InspectionSession", back_populates="inspector")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(80), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(80), nullable=True)
    details = Column(Text, nullable=True)  # JSON or text
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    category = Column(String(30), nullable=False, index=True)  # 'road', 'bridge', 'pipeline', 'power_grid'
    code = Column(String(50), unique=True, nullable=False, index=True)
    location_description = Column(String(255), nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    importance_level = Column(String(20), default="medium", nullable=False)  # 'critical', 'high', 'medium', 'low'
    length_or_area = Column(Float, nullable=True)  # km or sq.m
    year_built = Column(Integer, nullable=True)
    last_inspected = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    inspections = relationship("InspectionSession", back_populates="asset")
    defects = relationship("Defect", back_populates="asset")


class InspectionSession(Base):
    __tablename__ = "inspection_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_code = Column(String(60), unique=True, nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.id"), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(30), default="in_progress", nullable=False)  # 'in_progress', 'completed', 'reviewed'
    weather_condition = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    asset = relationship("InfrastructureAsset", back_populates="inspections")
    inspector = relationship("User", back_populates="inspections")
    media_records = relationship("MediaRecord", back_populates="session")
    defects = relationship("Defect", back_populates="session")
    sensor_datasets = relationship("SensorDataset", back_populates="session")


class MediaRecord(Base):
    __tablename__ = "media_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("inspection_sessions.id"), nullable=True)
    file_path = Column(String(300), nullable=False)
    original_filename = Column(String(200), nullable=False)
    file_type = Column(String(20), nullable=False)  # 'image', 'video'
    mime_type = Column(String(80), nullable=True)
    file_size_bytes = Column(Integer, nullable=False)
    frame_count = Column(Integer, default=1, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    capture_timestamp = Column(DateTime, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    gps_accuracy_meters = Column(Float, nullable=True)
    gps_reliable = Column(Boolean, default=False, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("InspectionSession", back_populates="media_records")
    defects = relationship("Defect", back_populates="media")


class SensorDataset(Base):
    __tablename__ = "sensor_datasets"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("inspection_sessions.id"), nullable=True)
    file_path = Column(String(300), nullable=False)
    original_filename = Column(String(200), nullable=False)
    sensor_types = Column(String(100), nullable=False)  # e.g. 'gps,accelerometer,vibration,speed'
    sample_rate_hz = Column(Float, default=10.0, nullable=False)
    total_samples = Column(Integer, default=0, nullable=False)
    sync_timestamp_start = Column(DateTime, nullable=True)
    status = Column(String(30), default="processed", nullable=False)  # 'uploaded', 'processing', 'processed', 'error'
    validation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("InspectionSession", back_populates="sensor_datasets")
    measurements = relationship("SensorMeasurement", back_populates="dataset", cascade="all, delete-orphan")
    aukf_estimates = relationship("AukfStateEstimate", back_populates="dataset", cascade="all, delete-orphan")


class SensorMeasurement(Base):
    __tablename__ = "sensor_measurements"

    id = Column(Integer, primary_key=True, index=True)
    sensor_dataset_id = Column(Integer, ForeignKey("sensor_datasets.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    speed_kmh = Column(Float, nullable=True)
    accel_x = Column(Float, nullable=True)
    accel_y = Column(Float, nullable=True)
    accel_z = Column(Float, nullable=True)
    vibration_level = Column(Float, nullable=True)  # m/s^2 or g-rms
    pressure_or_current = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    raw_data_json = Column(Text, nullable=True)

    dataset = relationship("SensorDataset", back_populates="measurements")


class AukfStateEstimate(Base):
    __tablename__ = "aukf_state_estimates"

    id = Column(Integer, primary_key=True, index=True)
    sensor_dataset_id = Column(Integer, ForeignKey("sensor_datasets.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    estimated_lat = Column(Float, nullable=True)
    estimated_lng = Column(Float, nullable=True)
    estimated_speed = Column(Float, nullable=True)
    anomaly_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    vibration_index = Column(Float, default=0.0, nullable=False)
    roughness_index = Column(Float, default=0.0, nullable=False)
    confidence_factor = Column(Float, default=1.0, nullable=False)
    covariance_trace = Column(Float, default=0.0, nullable=False)

    dataset = relationship("SensorDataset", back_populates="aukf_estimates")


class AIModelRegistry(Base):
    __tablename__ = "ai_models_registry"

    id = Column(Integer, primary_key=True, index=True)
    model_key = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(30), nullable=False, index=True)  # 'road', 'bridge', 'pipeline', 'power_grid'
    version = Column(String(20), nullable=False)
    supported_classes = Column(Text, nullable=False)  # JSON list
    source_url = Column(String(300), nullable=True)
    license = Column(String(80), nullable=False)
    weight_path = Column(String(300), nullable=True)
    weight_status = Column(String(40), default="demo_fallback", nullable=False)  # 'loaded', 'pretrained_default', 'demo_fallback', 'missing'
    limitations = Column(Text, nullable=True)
    loaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DatasetRegistry(Base):
    __tablename__ = "dataset_registry"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    category = Column(String(30), nullable=False, index=True)
    source_url = Column(String(300), nullable=False)
    license = Column(String(80), nullable=False)
    classes = Column(Text, nullable=False)  # JSON list
    geographic_coverage = Column(String(150), nullable=False)
    annotation_format = Column(String(50), nullable=False)
    download_status = Column(String(40), default="registered", nullable=False)  # 'registered', 'ready_for_import', 'sample_loaded', 'download_required'
    sample_file_count = Column(Integer, default=0, nullable=False)
    error_notes = Column(Text, nullable=True)
    suitability_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Defect(Base):
    __tablename__ = "defects"

    id = Column(String(50), primary_key=True, index=True)  # Unique ID e.g. DEF-20261028-001
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("inspection_sessions.id"), nullable=True)
    media_id = Column(Integer, ForeignKey("media_records.id"), nullable=True)
    category = Column(String(30), nullable=False, index=True)  # 'road', 'bridge', 'pipeline', 'power_grid'
    defect_type = Column(String(60), nullable=False, index=True)
    bounding_box = Column(Text, nullable=True)  # JSON {"x": int, "y": int, "width": int, "height": int}
    
    # AI & Assessment Confidence
    model_confidence = Column(Float, nullable=False)
    assessed_confidence = Column(Float, nullable=False)
    confidence_grade = Column(String(40), nullable=False)  # High-confidence prediction, Needs review, Sensor-supported, Verified by authorized inspection, Insufficient data
    confidence_rationale = Column(Text, nullable=True)
    
    severity = Column(String(20), default="moderate", nullable=False, index=True)  # 'critical', 'severe', 'moderate', 'minor'
    sensor_evidence_id = Column(Integer, ForeignKey("aukf_state_estimates.id"), nullable=True)
    sensor_supported = Column(Boolean, default=False, nullable=False)
    
    # Location & Reliability
    lat = Column(Float, nullable=True, index=True)
    lng = Column(Float, nullable=True, index=True)
    gps_reliable = Column(Boolean, default=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Verification Status
    verification_status = Column(String(35), default="unverified", nullable=False, index=True)  # 'unverified', 'pending_review', 'verified_by_inspection', 'rejected'
    verification_notes = Column(Text, nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Historical Deterioration
    parent_defect_id = Column(String(50), ForeignKey("defects.id"), nullable=True)
    deterioration_status = Column(String(30), default="new", nullable=False)  # 'new', 'stable', 'worsening', 'unresolved', 'inconclusive'
    
    # Risk & Prioritization
    risk_score = Column(Float, default=0.0, nullable=False)  # 0 to 100
    risk_level = Column(String(20), default="low", nullable=False, index=True)  # 'critical', 'high', 'medium', 'low'
    repair_priority_rank = Column(Integer, default=999, nullable=False, index=True)
    repair_priority_rationale = Column(Text, nullable=True)
    estimated_urgency_days = Column(Integer, default=30, nullable=False)

    # Relationships
    asset = relationship("InfrastructureAsset", back_populates="defects")
    session = relationship("InspectionSession", back_populates="defects")
    media = relationship("MediaRecord", back_populates="defects")
    timelines = relationship("DeteriorationTimeline", back_populates="defect", cascade="all, delete-orphan")


class DefectDuplicate(Base):
    __tablename__ = "defect_duplicates"

    id = Column(Integer, primary_key=True, index=True)
    primary_defect_id = Column(String(50), ForeignKey("defects.id"), nullable=False, index=True)
    duplicate_defect_id = Column(String(50), ForeignKey("defects.id"), nullable=False, index=True)
    distance_meters = Column(Float, nullable=False)
    similarity_score = Column(Float, nullable=False)
    match_type = Column(String(30), nullable=False)  # 'confirmed_duplicate', 'uncertain_match', 'historical_reobservation'
    status = Column(String(30), default="auto_detected", nullable=False)  # 'auto_detected', 'confirmed_by_analyst', 'rejected_distinct'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DeteriorationTimeline(Base):
    __tablename__ = "deterioration_timeline"

    id = Column(Integer, primary_key=True, index=True)
    defect_id = Column(String(50), ForeignKey("defects.id"), nullable=False, index=True)
    inspection_date = Column(DateTime, nullable=False)
    observation_order = Column(Integer, default=1, nullable=False)
    visible_dimensions = Column(Text, nullable=True)  # JSON {"width_cm": float, "length_cm": float, "area_sqcm": float}
    severity = Column(String(20), nullable=False)
    severity_delta = Column(String(30), default="no_change", nullable=False)  # 'increased', 'stable', 'decreased', 'inconclusive'
    status = Column(String(30), default="new", nullable=False)  # 'new', 'stable', 'worsening', 'unresolved', 'inconclusive'
    notes = Column(Text, nullable=True)
    image_ref = Column(String(300), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    defect = relationship("Defect", back_populates="timelines")


class RepairPriority(Base):
    __tablename__ = "repair_priorities"

    id = Column(Integer, primary_key=True, index=True)
    defect_id = Column(String(50), ForeignKey("defects.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    contributing_factors = Column(Text, nullable=False)  # JSON list/dict
    safety_impact = Column(String(50), nullable=False)
    resource_constraint_notes = Column(Text, nullable=True)
    recommended_action = Column(String(200), nullable=False)
    estimated_urgency_days = Column(Integer, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
