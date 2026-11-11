"""Unit and integration tests for FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_stats(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "fps" in data
    assert "total_ms" in data


def test_get_and_update_config(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    cfg = response.json()
    assert "source" in cfg

    # Update config
    new_cfg = {"pedestrian": {"conf": 0.45}}
    put_res = client.put("/api/config", json=new_cfg)
    assert put_res.status_code == 200
    assert put_res.json()["status"] == "updated"


def test_get_events(client):
    response = client.get("/api/events?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "total" in data
    assert isinstance(data["events"], list)


def test_pipeline_controls(client):
    stop_res = client.post("/api/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["running"] is False

    start_res = client.post("/api/start")
    assert start_res.status_code == 200

