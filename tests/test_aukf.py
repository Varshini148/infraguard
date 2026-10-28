"""
Unit Tests for Adaptive Unscented Kalman Filter (AUKF) Sensor Fusion
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from backend.app.sensor_fusion.aukf import AdaptiveUKF, SensorFusionPipeline

def test_aukf_initialization():
    aukf = AdaptiveUKF()
    aukf.initialize_state(lat=11.1271, lng=78.6569, speed_mps=15.0)
    
    assert aukf.x[0] == 11.1271
    assert aukf.x[1] == 78.6569
    assert aukf.x[2] == 15.0
    assert aukf.x[3] == 0.0
    assert aukf.x[4] == 0.0
    assert aukf.P.shape == (5, 5)
    assert np.all(np.diag(aukf.P) > 0)

def test_aukf_prediction_step():
    aukf = AdaptiveUKF()
    aukf.initialize_state(lat=11.0, lng=78.0, speed_mps=20.0)
    
    initial_lat = aukf.x[0]
    aukf.predict(dt=1.0)
    
    # Forward velocity should translate latitude slightly northwards
    assert aukf.x[0] > initial_lat
    # Covariance trace must be strictly positive
    assert np.trace(aukf.P) > 0

def test_aukf_update_full_measurement():
    aukf = AdaptiveUKF()
    aukf.initialize_state(lat=11.0, lng=78.0, speed_mps=10.0)
    aukf.predict(dt=0.1)

    meas = {
        "lat": 11.0001,
        "lng": 78.0001,
        "speed_mps": 10.5,
        "accel_z": 2.5,
        "vibration_level": 1.9
    }
    aukf.update(meas)
    est = aukf.get_current_estimate()

    assert 10.999 < est["estimated_lat"] < 11.001
    assert est["roughness_index"] >= 0.0
    assert est["anomaly_score"] >= 0.0
    assert est["confidence_factor"] > 0.0

def test_aukf_update_missing_gps():
    aukf = AdaptiveUKF()
    aukf.initialize_state(lat=11.0, lng=78.0, speed_mps=10.0)
    aukf.predict(dt=0.1)

    # GPS dropout, only accelerometer and vibration present
    meas = {
        "lat": None,
        "lng": None,
        "speed_mps": 9.8,
        "accel_z": 3.8,
        "vibration_level": 2.7
    }
    aukf.update(meas)
    est = aukf.get_current_estimate()

    assert est["estimated_lat"] == 11.0 or abs(est["estimated_lat"] - 11.0) < 1e-4
    assert est["anomaly_score"] > 0.0

def test_sensor_data_validation():
    pipeline = SensorFusionPipeline()
    
    # DataFrame with invalid coords and alternative column headers
    raw_data = {
        "Time": ["2026-10-28 10:00:00", "2026-10-28 10:00:01"],
        "Latitude": [11.5, 95.0],  # 95 is invalid (>90)
        "Longitude": [78.5, 78.6],
        "Velocity": [40.0, 42.0],
        "Vertical_Accel": [0.2, 3.4],
        "Vib": [0.4, 2.8]
    }
    df = pd.DataFrame(raw_data)
    clean_df = pipeline.parse_and_validate_sensor_data(df)

    assert "lat" in clean_df.columns
    assert "speed_kmh" in clean_df.columns
    assert "accel_z" in clean_df.columns
    assert pd.isna(clean_df.loc[1, "lat"])  # Out-of-bounds latitude sanitized to NaN
