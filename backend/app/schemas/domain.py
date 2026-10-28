"""
InfraGuard Pydantic Domain Schemas
Validates data payloads for APIs across all platform modules.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

# Auth & User Schemas
class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "analyst"  # 'admin', 'inspector', 'analyst'

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Infrastructure Asset Schemas
class AssetCreate(BaseModel):
    name: str
    category: str  # 'road', 'bridge', 'pipeline', 'power_grid'
    code: str
    location_description: Optional[str] = None
    lat: float
    lng: float
    importance_level: str = "medium"  # 'critical', 'high', 'medium', 'low'
    length_or_area: Optional[float] = None
    year_built: Optional[int] = None

class AssetResponse(AssetCreate):
    id: int
    last_inspected: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Defect Schemas
class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class DefectCreate(BaseModel):
    asset_id: Optional[int] = None
    session_id: Optional[int] = None
    media_id: Optional[int] = None
    category: str
    defect_type: str
    bounding_box: Optional[BoundingBox] = None
    model_confidence: float
    assessed_confidence: Optional[float] = None
    confidence_grade: Optional[str] = "High-confidence prediction"
    severity: str = "moderate"
    lat: Optional[float] = None
    lng: Optional[float] = None
    gps_reliable: bool = True
    timestamp: Optional[datetime] = None

class DefectVerificationUpdate(BaseModel):
    verification_status: str  # 'verified_by_inspection', 'rejected', 'pending_review'
    verification_notes: Optional[str] = None

class DefectResponse(BaseModel):
    id: str
    asset_id: Optional[int]
    session_id: Optional[int]
    media_id: Optional[int]
    category: str
    defect_type: str
    bounding_box: Optional[Dict[str, Any]] = None
    model_confidence: float
    assessed_confidence: float
    confidence_grade: str
    confidence_rationale: Optional[str] = None
    severity: str
    sensor_evidence_id: Optional[int] = None
    sensor_supported: bool
    lat: Optional[float]
    lng: Optional[float]
    gps_reliable: bool
    timestamp: datetime
    verification_status: str
    verification_notes: Optional[str] = None
    verified_by_id: Optional[int] = None
    parent_defect_id: Optional[str] = None
    deterioration_status: str
    risk_score: float
    risk_level: str
    repair_priority_rank: int
    repair_priority_rationale: Optional[str] = None
    estimated_urgency_days: int
    media_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# AI Detection Result Schema
class DetectionItem(BaseModel):
    defect_type: str
    category: str
    confidence: float
    bounding_box: Dict[str, int]
    severity: str
    assessed_confidence: float
    confidence_grade: str
    confidence_rationale: str

class DetectionResponse(BaseModel):
    media_id: int
    file_path: str
    original_filename: str
    file_type: str
    total_detections: int
    detections: List[DetectionItem]
    model_used: str
    model_version: str
    model_status: str
    processing_time_ms: float
    saved_defects: List[str]

# Sensor & AUKF Schemas
class AUKFEstimateItem(BaseModel):
    timestamp: datetime
    estimated_lat: Optional[float]
    estimated_lng: Optional[float]
    estimated_speed: Optional[float]
    anomaly_score: float
    vibration_index: float
    roughness_index: float
    confidence_factor: float
    covariance_trace: float

class SensorAnalysisResponse(BaseModel):
    dataset_id: int
    original_filename: str
    sensor_types: List[str]
    total_samples: int
    sample_rate_hz: float
    vibration_anomalies_detected: int
    fusion_status: str
    state_estimates: List[AUKFEstimateItem]
    associated_defects: List[str]
    reliability_assessment: str

# Duplicate Schemas
class DuplicateItem(BaseModel):
    id: int
    primary_defect_id: str
    duplicate_defect_id: str
    distance_meters: float
    similarity_score: float
    match_type: str
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DuplicateResolution(BaseModel):
    duplicate_id: int
    action: str  # 'confirm_duplicate', 'reject_distinct', 'flag_uncertain'
    notes: Optional[str] = None

# Deterioration Timeline Schemas
class TimelineItem(BaseModel):
    id: int
    defect_id: str
    inspection_date: datetime
    observation_order: int
    visible_dimensions: Optional[Dict[str, float]]
    severity: str
    severity_delta: str
    status: str
    notes: Optional[str]
    image_ref: Optional[str]
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TimelineSummary(BaseModel):
    defect_id: str
    defect_type: str
    category: str
    timeline_records: List[TimelineItem]
    overall_trend: str
    first_detected: datetime
    latest_observation: datetime
    urgency_recommendation: str

# Risk & Prioritization Schemas
class RiskAssessmentItem(BaseModel):
    defect_id: str
    category: str
    defect_type: str
    severity: str
    risk_score: float
    risk_level: str
    contributing_factors: List[str]
    repair_priority_rank: int
    recommended_action: str
    urgency_days: int
    explanation: str

# Model & Dataset Registry Schemas
class AIModelItem(BaseModel):
    id: int
    model_key: str
    name: str
    category: str
    version: str
    supported_classes: List[str]
    source_url: Optional[str]
    license: str
    weight_status: str
    limitations: Optional[str]
    loaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DatasetItem(BaseModel):
    id: int
    name: str
    category: str
    source_url: str
    license: str
    classes: List[str]
    geographic_coverage: str
    annotation_format: str
    download_status: str
    sample_file_count: int
    error_notes: Optional[str]
    suitability_notes: Optional[str]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Dashboard Summary
class DashboardStats(BaseModel):
    total_defects: int
    critical_defects: int
    severe_defects: int
    moderate_defects: int
    minor_defects: int
    by_category: Dict[str, int]
    by_risk_level: Dict[str, int]
    by_verification_status: Dict[str, int]
    by_deterioration_status: Dict[str, int]
    sensor_supported_count: int
    duplicates_detected: int
    recent_defects: List[DefectResponse]
    model_statuses: Dict[str, str]
