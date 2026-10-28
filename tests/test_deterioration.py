"""
Unit Tests for Historical Deterioration Analysis
"""

import pytest
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.connection import Base
from backend.app.models.entities import Defect
from backend.app.services.deterioration import deterioration_service

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_deterioration_progression(test_db):
    now = datetime.utcnow()
    defect = Defect(
        id="DEF-DET-01",
        category="bridge",
        defect_type="Concrete Spalling & Exposed Rebar",
        severity="moderate",
        model_confidence=0.85,
        assessed_confidence=0.85,
        confidence_grade="High",
        timestamp=now - timedelta(days=60)
    )
    test_db.add(defect)
    test_db.commit()

    # Observation 1: Baseline established
    obs1 = deterioration_service.record_observation(
        test_db, defect, visible_dimensions={"area_sqcm": 200.0}
    )
    assert obs1.status == "new"
    assert obs1.observation_order == 1

    # Observation 2: 30 days later, expanded area (+100%) -> worsening
    defect.timestamp = now - timedelta(days=30)
    defect.severity = "severe"
    obs2 = deterioration_service.record_observation(
        test_db, defect, visible_dimensions={"area_sqcm": 400.0}
    )
    assert obs2.status == "worsening"
    assert obs2.observation_order == 2
    assert defect.deterioration_status == "worsening"

    # Get full summary
    timeline_summary = deterioration_service.get_defect_timeline(test_db, defect.id)
    assert timeline_summary["total_observations"] == 2
    assert timeline_summary["current_status"] == "worsening"
