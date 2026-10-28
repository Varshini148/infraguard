"""
Unit Tests for Spatial & Temporal Duplicate Detection
"""

import pytest
import math
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.connection import Base
from backend.app.models.entities import Defect
from backend.app.services.duplicate_detection import (
    haversine_distance_meters, duplicate_detection_service
)

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_haversine_distance():
    # Coords 1 km apart approximately
    # 1 deg lat is ~ 111,139 meters
    dist = haversine_distance_meters(11.0, 78.0, 11.009, 78.0)
    assert 990 <= dist <= 1010

def test_confirmed_duplicate_detection(test_db):
    now = datetime.utcnow()
    d1 = Defect(
        id="DEF-TEST-01",
        category="road",
        defect_type="D40: Pothole",
        lat=11.4883,
        lng=77.8683,
        model_confidence=0.9,
        assessed_confidence=0.9,
        confidence_grade="High",
        severity="critical",
        timestamp=now
    )
    test_db.add(d1)
    test_db.commit()

    # Second defect within 5 meters, same type, 2 hours later
    d2 = Defect(
        id="DEF-TEST-02",
        category="road",
        defect_type="D40: Pothole",
        lat=11.48833,
        lng=77.86833,
        model_confidence=0.88,
        assessed_confidence=0.88,
        confidence_grade="High",
        severity="critical",
        timestamp=now + timedelta(hours=2)
    )
    test_db.add(d2)
    test_db.commit()

    matches = duplicate_detection_service.scan_for_duplicates(test_db, d2)
    assert len(matches) == 1
    assert matches[0]["candidate_id"] == "DEF-TEST-01"
    assert matches[0]["match_type"] == "confirmed_duplicate"

def test_uncertain_match_flagging(test_db):
    now = datetime.utcnow()
    d1 = Defect(
        id="DEF-TEST-03",
        category="road",
        defect_type="D40: Pothole",
        lat=11.4883,
        lng=77.8683,
        model_confidence=0.8,
        assessed_confidence=0.8,
        confidence_grade="High",
        severity="critical",
        timestamp=now
    )
    test_db.add(d1)
    test_db.commit()

    # Defect ~25 meters away with differing class
    d2 = Defect(
        id="DEF-TEST-04",
        category="road",
        defect_type="D00: Longitudinal Crack",
        lat=11.4885,
        lng=77.8684,
        model_confidence=0.85,
        assessed_confidence=0.85,
        confidence_grade="High",
        severity="moderate",
        timestamp=now
    )
    test_db.add(d2)
    test_db.commit()

    matches = duplicate_detection_service.scan_for_duplicates(test_db, d2)
    assert len(matches) == 1
    assert matches[0]["match_type"] == "uncertain_match"
