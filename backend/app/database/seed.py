"""
InfraGuard Database Seeder
Populates initial authorized staff, infrastructure assets in Tamil Nadu, India,
candidate datasets, sample AI defects, deterioration timelines, and duplicates.
"""

from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    User, InfrastructureAsset, Defect, DefectDuplicate, DeteriorationTimeline, SensorDataset
)
from backend.app.security.auth import hash_password
from backend.app.services.dataset_registry import initialize_dataset_registry
from backend.app.services.repair_priority import repair_priority_service

def seed_database(db: Session):
    """Seed initial demonstration and operational data if database is empty."""
    # 1. Users
    if db.query(User).count() == 0:
        admin = User(
            username="admin",
            email="admin@infraguard.gov.in",
            hashed_password=hash_password("admin123"),
            full_name="Chief Infrastructure Engineer",
            role="admin",
            is_active=True
        )
        inspector = User(
            username="inspector",
            email="inspector@infraguard.gov.in",
            hashed_password=hash_password("inspector123"),
            full_name="Senior Field Inspector",
            role="inspector",
            is_active=True
        )
        analyst = User(
            username="analyst",
            email="analyst@infraguard.gov.in",
            hashed_password=hash_password("analyst123"),
            full_name="Maintenance Data Analyst",
            role="analyst",
            is_active=True
        )
        db.add_all([admin, inspector, analyst])
        db.commit()

    # 2. Dataset Registry
    initialize_dataset_registry(db)

    # 3. Infrastructure Assets (Tamil Nadu, India focus)
    if db.query(InfrastructureAsset).count() == 0:
        assets = [
            InfrastructureAsset(
                name="NH 544 Salem-Coimbatore Express Highway Segment",
                category="road",
                code="ASSET-RD-TN-01",
                location_description="NH 544 Km 42-48, Sankagiri Bypass, Tamil Nadu",
                lat=11.4883,
                lng=77.8683,
                importance_level="critical",
                length_or_area=6.2,
                year_built=2014,
                created_at=datetime.utcnow()
            ),
            InfrastructureAsset(
                name="Cauvery River Bridge Substructure (Erode)",
                category="bridge",
                code="ASSET-BR-TN-02",
                location_description="Cauvery Bridge Span 4-8, Pallipalayam-Erode, Tamil Nadu",
                lat=11.3530,
                lng=77.7281,
                importance_level="critical",
                length_or_area=0.85,
                year_built=1998,
                created_at=datetime.utcnow()
            ),
            InfrastructureAsset(
                name="Ennore-Manali Industrial Gas & Effluent Pipeline Corridor",
                category="pipeline",
                code="ASSET-PL-TN-03",
                location_description="Zone 3 Subterranean Trunk Line, North Chennai, Tamil Nadu",
                lat=13.2084,
                lng=80.3235,
                importance_level="high",
                length_or_area=14.5,
                year_built=2008,
                created_at=datetime.utcnow()
            ),
            InfrastructureAsset(
                name="Mettur-Salem 400kV High-Voltage Transmission Corridor",
                category="power_grid",
                code="ASSET-PG-TN-04",
                location_description="Towers 112 to 140, Mettur Dam Environs, Tamil Nadu",
                lat=11.7962,
                lng=77.8016,
                importance_level="critical",
                length_or_area=28.0,
                year_built=2011,
                created_at=datetime.utcnow()
            )
        ]
        db.add_all(assets)
        db.commit()

    # 4. Realistic Seed Defects with actual GPS, sensor correlation, and deterioration history
    if db.query(Defect).count() == 0:
        road_asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.code == "ASSET-RD-TN-01").first()
        bridge_asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.code == "ASSET-BR-TN-02").first()
        pipeline_asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.code == "ASSET-PL-TN-03").first()
        power_asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.code == "ASSET-PG-TN-04").first()

        now = datetime.utcnow()

        seed_defects = [
            # Defect 1: Critical Road Pothole with Sensor Anomaly
            Defect(
                id="DEF-20261028-RD01",
                asset_id=road_asset.id if road_asset else None,
                category="road",
                defect_type="D40: Pothole",
                bounding_box=json.dumps({"x": 140, "y": 280, "width": 180, "height": 110}),
                model_confidence=0.91,
                assessed_confidence=0.97,
                confidence_grade="Sensor-supported",
                confidence_rationale="Raw model confidence: 91%; Reinforced by AUKF vertical acceleration anomaly (3.8 m/s²)",
                severity="critical",
                sensor_supported=True,
                lat=11.4892,
                lng=77.8695,
                gps_reliable=True,
                timestamp=now - timedelta(days=12),
                verification_status="verified_by_inspection",
                verification_notes="Verified by Field Inspector during NHAI quarterly check.",
                deterioration_status="worsening",
                risk_score=88.5,
                risk_level="critical",
                repair_priority_rank=1,
                repair_priority_rationale="Rank #1: Critical risk (88.5/100). Critical D40: Pothole showing worsening progression on critical NH 544 arterial.",
                estimated_urgency_days=3
            ),
            # Defect 2: Road Longitudinal Crack (Stable)
            Defect(
                id="DEF-20261028-RD02",
                asset_id=road_asset.id if road_asset else None,
                category="road",
                defect_type="D00: Longitudinal Crack",
                bounding_box=json.dumps({"x": 220, "y": 150, "width": 80, "height": 260}),
                model_confidence=0.86,
                assessed_confidence=0.86,
                confidence_grade="High-confidence prediction",
                confidence_rationale="Model confidence: 86%; GPS verified; stable pavement vibration",
                severity="moderate",
                sensor_supported=False,
                lat=11.4915,
                lng=77.8720,
                gps_reliable=True,
                timestamp=now - timedelta(days=35),
                verification_status="unverified",
                deterioration_status="stable",
                risk_score=52.0,
                risk_level="medium",
                repair_priority_rank=3,
                repair_priority_rationale="Rank #3: Moderate risk (52.0/100). Condition stable across 35 days; routine seal coat scheduled.",
                estimated_urgency_days=21
            ),
            # Defect 3: Bridge Pier Concrete Spalling & Exposed Rebar
            Defect(
                id="DEF-20261028-BR01",
                asset_id=bridge_asset.id if bridge_asset else None,
                category="bridge",
                defect_type="Concrete Spalling & Exposed Rebar",
                bounding_box=json.dumps({"x": 95, "y": 180, "width": 210, "height": 190}),
                model_confidence=0.89,
                assessed_confidence=0.92,
                confidence_grade="High-confidence prediction",
                confidence_rationale="Model confidence: 89%; Visual concrete cross-verification verified by drone nadir",
                severity="severe",
                sensor_supported=False,
                lat=11.3538,
                lng=77.7289,
                gps_reliable=True,
                timestamp=now - timedelta(days=22),
                verification_status="verified_by_inspection",
                verification_notes="Confirmed surface rebar oxidation on Pier 5 substructure.",
                deterioration_status="worsening",
                risk_score=78.2,
                risk_level="high",
                repair_priority_rank=2,
                repair_priority_rationale="Rank #2: High risk (78.2/100). Severe spalling on major river bridge pier. Rebar anti-corrosion patch required within 7 days.",
                estimated_urgency_days=7
            ),
            # Defect 4: Pipeline Joint Displacement
            Defect(
                id="DEF-20261028-PL01",
                asset_id=pipeline_asset.id if pipeline_asset else None,
                category="pipeline",
                defect_type="Joint Displacement",
                bounding_box=json.dumps({"x": 160, "y": 140, "width": 150, "height": 130}),
                model_confidence=0.78,
                assessed_confidence=0.78,
                confidence_grade="Needs review",
                confidence_rationale="CCTV robotic visual inference: 78%; Low internal lighting variance requires second pass",
                severity="moderate",
                sensor_supported=False,
                lat=13.2091,
                lng=80.3242,
                gps_reliable=True,
                timestamp=now - timedelta(days=8),
                verification_status="pending_review",
                deterioration_status="new",
                risk_score=58.4,
                risk_level="medium",
                repair_priority_rank=4,
                repair_priority_rationale="Rank #4: Moderate risk (58.4/100). Joint displacement in municipal effluent line; needs review before pressure test.",
                estimated_urgency_days=18
            ),
            # Defect 5: Power Grid Broken Insulator Disc
            Defect(
                id="DEF-20261028-PG01",
                asset_id=power_asset.id if power_asset else None,
                category="power_grid",
                defect_type="Broken Insulator Disc",
                bounding_box=json.dumps({"x": 240, "y": 90, "width": 95, "height": 85}),
                model_confidence=0.93,
                assessed_confidence=0.93,
                confidence_grade="High-confidence prediction",
                confidence_rationale="High-resolution UAV inspection: 93% match on ceramic insulator disc fracture",
                severity="severe",
                sensor_supported=False,
                lat=11.7970,
                lng=77.8025,
                gps_reliable=True,
                timestamp=now - timedelta(days=5),
                verification_status="unverified",
                deterioration_status="new",
                risk_score=71.0,
                risk_level="high",
                repair_priority_rank=5,
                repair_priority_rationale="Rank #5: High risk (71.0/100). Broken insulator on 400kV transmission tower risks flashover fault under rain.",
                estimated_urgency_days=7
            )
        ]

        db.add_all(seed_defects)
        db.commit()

        # Seed Deterioration Timelines for Defect 1 (3 chronological observations)
        d1 = seed_defects[0]
        t1 = DeteriorationTimeline(
            defect_id=d1.id,
            inspection_date=now - timedelta(days=60),
            observation_order=1,
            visible_dimensions=json.dumps({"width_cm": 25.0, "length_cm": 30.0, "area_sqcm": 750.0}),
            severity="moderate",
            severity_delta="baseline_established",
            status="new",
            notes="Initial observation: Moderate pavement depression noted.",
            recorded_at=now - timedelta(days=60)
        )
        t2 = DeteriorationTimeline(
            defect_id=d1.id,
            inspection_date=now - timedelta(days=30),
            observation_order=2,
            visible_dimensions=json.dumps({"width_cm": 35.0, "length_cm": 42.0, "area_sqcm": 1470.0}),
            severity="severe",
            severity_delta="increased",
            status="worsening",
            notes="Follow-up observation: Asphalt detachment and edge raveling expanded area by +96%.",
            recorded_at=now - timedelta(days=30)
        )
        t3 = DeteriorationTimeline(
            defect_id=d1.id,
            inspection_date=d1.timestamp,
            observation_order=3,
            visible_dimensions=json.dumps({"width_cm": 45.0, "length_cm": 55.0, "area_sqcm": 2475.0}),
            severity="critical",
            severity_delta="increased",
            status="worsening",
            notes="Latest observation: Deep pothole reaching granular base course; high vehicle impact hazard.",
            recorded_at=d1.timestamp
        )
        db.add_all([t1, t2, t3])
        db.commit()

        # Seed Duplicate entry (Uncertain match for demonstration)
        dup = DefectDuplicate(
            primary_defect_id=seed_defects[0].id,
            duplicate_defect_id=seed_defects[1].id,
            distance_meters=27.4,
            similarity_score=0.42,
            match_type="uncertain_match",
            status="auto_detected",
            notes="Near proximity (27.4m) on NH 544 segment. Distinct defect types ('Pothole' vs 'Longitudinal Crack') flagged for analyst confirmation."
        )
        db.add(dup)
        db.commit()

        # Recalculate repair priorities
        repair_priority_service.recompute_priorities(db)
