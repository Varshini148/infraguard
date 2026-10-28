"""
API Integration Tests using FastAPI TestClient
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["system"] == "InfraGuard"

def test_auth_login(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"

def test_models_endpoint(client):
    res = client.get("/api/detection/models")
    assert res.status_code == 200
    data = res.json()
    for cat in ["road", "bridge", "pipeline", "power_grid"]:
        assert cat in data
        assert "supported_classes" in data[cat]
        assert "license" in data[cat]

def test_sample_sensor_csv_generation(client):
    res = client.get("/api/sensors/generate-sample-csv")
    assert res.status_code == 200
    assert "timestamp,lat,lng" in res.text
    assert "NH 544" in res.headers.get("content-disposition", "") or "sample" in res.headers.get("content-disposition", "")

def test_defects_and_geojson_endpoints(client):
    res = client.get("/api/infrastructure/defects")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

    res_geo = client.get("/api/infrastructure/geojson")
    assert res_geo.status_code == 200
    geo = res_geo.json()
    assert geo["type"] == "FeatureCollection"
    assert isinstance(geo["features"], list)

def test_summary_report_endpoint(client):
    res = client.get("/api/reports/summary")
    assert res.status_code == 200
    summary = res.json()
    assert "total_defects" in summary
    assert "by_category" in summary
    assert "by_severity" in summary
