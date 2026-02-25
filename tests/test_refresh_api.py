"""Tests for POST /api/refresh and GET /api/refresh/status endpoints."""

import json


def test_refresh_no_api_key(client):
    """POST /api/refresh without API key returns 400."""
    r = client.post("/api/refresh")
    assert r.status_code == 400
    assert "No Ticketmaster API key" in r.json()["detail"]


def test_refresh_status_initial(client):
    """GET /api/refresh/status before any refresh shows not running."""
    r = client.get("/api/refresh/status")
    assert r.status_code == 200
    data = r.json()
    assert data["running"] is False
    assert data["total"] == 0
    assert data["processed"] == 0


def test_refresh_status_fields(client):
    """GET /api/refresh/status returns all expected fields."""
    r = client.get("/api/refresh/status")
    data = r.json()
    expected_fields = [
        "running", "phase", "total", "processed",
        "artists_total", "artists_processed",
        "venues_total", "venues_processed",
        "festivals_total", "festivals_processed",
        "error",
    ]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"
