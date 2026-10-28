"""
Unit Tests for Risk Scoring and Repair Prioritization
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.connection import Base
from backend.app.models.entities import Defect, InfrastructureAsset
from backend.app.services.risk_prediction import risk_prediction_service
from backend.app.services.repair_priority import repair_priority_service

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_risk_scoring_and_ranking(test_db):
    now = datetime.utcnow()
    asset = InfrastructureAsset(
        name="Critical Highway Arterial",
        category="road",
        code="HW-01",
        lat=11.0,
        lng=78.0,
        importance_level="critical"
    )
    test_db.add(asset)
    test_db.commit()

    # Severe worsening defect on critical asset with sensor reinforcement
    d_crit = Defect(
        id="DEF-CRIT",
        asset_id=asset.id,
        category="road",
        defect_type="D40: Pothole",
        severity="critical",
        model_confidence=0.92,
        assessed_confidence=0.98,
        confidence_grade="Sensor-supported",
        sensor_supported=True,
        deterioration_status="worsening",
        lat=11.0,
        lng=78.0,
        timestamp=now - timedelta(days=20)
    )

    # Minor stable defect on critical asset
    d_minor = Defect(
        id="DEF-MINOR",
        asset_id=asset.id,
        category="road",
        defect_type="D10: Transverse Crack",
        severity="minor",
        model_confidence=0.75,
        assessed_confidence=0.75,
        confidence_grade="High",
        sensor_supported=False,
        deterioration_status="stable",
        lat=11.01,
        lng=78.01,
        timestamp=now
    )

    test_db.add_all([d_crit, d_minor])
    test_db.commit()

    risk_info_crit = risk_prediction_service.calculate_risk(test_db, d_crit, asset)
    risk_info_minor = risk_prediction_service.calculate_risk(test_db, d_minor, asset)

    assert risk_info_crit["risk_score"] > risk_info_minor["risk_score"]
    assert risk_info_crit["risk_level"] in ["critical", "high"]

    # Recompute priority ordering
    ranked = repair_priority_service.recompute_priorities(test_db)
    assert len(ranked) == 2
    assert ranked[0]["defect_id"] == "DEF-CRIT"
    assert ranked[0]["rank"] == 1
    assert ranked[1]["defect_id"] == "DEF-MINOR"
    assert ranked[1]["rank"] == 2
