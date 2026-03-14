"""Tests for GET /api/shows endpoint."""

import json

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MINIMAL_CONFIG


@pytest.fixture()
def shows_client(tmp_path, monkeypatch):
    """TestClient with SUMMARY_FILE also monkeypatched."""
    import backend.main as main_mod

    config_file = tmp_path / "wingman_config.json"
    config_file.write_text(json.dumps(MINIMAL_CONFIG, indent=2))

    summary_file = tmp_path / "summary.json"

    monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
    monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
    monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
    monkeypatch.setattr(main_mod, "GEOCODE_FILE", tmp_path / "geocode_cache.json")
    monkeypatch.setattr(main_mod, "SUMMARY_FILE", summary_file)
    monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

    return TestClient(main_mod.app)


def test_shows_no_summary_file(shows_client):
    """When summary.json does not exist, returns default empty structure."""
    r = shows_client.get("/api/shows")
    assert r.status_code == 200
    data = r.json()
    assert data["artist_shows"] == {}
    assert data["venue_shows"] == {}
    assert data["festival_shows"] == {}
    assert data["coming_soon"] == []
    assert data["festival_coming_soon"] == []
    assert data["artists_not_found"] == []
    assert data["venues_not_found"] == []
    assert data["festivals_not_found"] == []
    assert data["stale"] is True


def test_shows_with_summary_file(tmp_path, monkeypatch):
    """When summary.json exists, returns its parsed content."""
    import backend.main as main_mod

    config_file = tmp_path / "wingman_config.json"
    config_file.write_text(json.dumps(MINIMAL_CONFIG, indent=2))

    summary_file = tmp_path / "summary.json"
    summary_data = {
        "artist_shows": {"Caamp": [{"date": "Jun 1, 2026", "venue": "Sylvee", "city": "Madison, WI"}]},
        "venue_shows": {},
        "festival_shows": {},
        "coming_soon": [],
        "festival_coming_soon": [],
        "artists_not_found": [],
        "venues_not_found": [],
        "festivals_not_found": [],
        "stale": False,
    }
    summary_file.write_text(json.dumps(summary_data))

    monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
    monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
    monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
    monkeypatch.setattr(main_mod, "GEOCODE_FILE", tmp_path / "geocode_cache.json")
    monkeypatch.setattr(main_mod, "SUMMARY_FILE", summary_file)
    monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

    client = TestClient(main_mod.app)
    r = client.get("/api/shows")
    assert r.status_code == 200
    data = r.json()
    assert "Caamp" in data["artist_shows"]
    assert data["artist_shows"]["Caamp"][0]["venue"] == "Sylvee"
    assert data["stale"] is False


def test_shows_all_fields_populated(tmp_path, monkeypatch):
    """When summary.json has all fields populated, they are returned correctly."""
    import backend.main as main_mod

    config_file = tmp_path / "wingman_config.json"
    config_file.write_text(json.dumps(MINIMAL_CONFIG, indent=2))

    summary_file = tmp_path / "summary.json"
    summary_data = {
        "generated_at": "2026-03-14",
        "center": "Des Moines, IA",
        "center_lat": 41.5868,
        "center_lon": -93.625,
        "artist_shows": {
            "Zach Bryan": [
                {"date": "Jun 20, 2026", "venue": "Wells Fargo Arena", "city": "Des Moines, IA",
                 "status": "on_sale", "lat": 41.59, "lon": -93.62, "is_new": True}
            ]
        },
        "venue_shows": {
            "Wells Fargo Arena": [
                {"date": "Jun 20, 2026", "artist": "Zach Bryan", "tracked": True}
            ]
        },
        "festival_shows": {
            "Hinterland": [
                {"date": "Aug 1, 2026", "venue": "Avenue of the Saints", "city": "St. Charles, IA",
                 "event_name": "Hinterland Music Festival", "status": "on_sale"}
            ]
        },
        "coming_soon": [
            {"artist": "Tyler Childers", "date": "Sep 1, 2026", "venue": "Kinnick Stadium",
             "city": "Iowa City, IA", "ticketmaster_url": "https://tm.com/1"}
        ],
        "festival_coming_soon": [],
        "artists_not_found": ["Nobody"],
        "venues_not_found": [],
        "festivals_not_found": ["FakeFest"],
        "stale": False,
    }
    summary_file.write_text(json.dumps(summary_data))

    monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
    monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
    monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
    monkeypatch.setattr(main_mod, "GEOCODE_FILE", tmp_path / "geocode_cache.json")
    monkeypatch.setattr(main_mod, "SUMMARY_FILE", summary_file)
    monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

    client = TestClient(main_mod.app)
    r = client.get("/api/shows")
    assert r.status_code == 200
    data = r.json()

    assert data["generated_at"] == "2026-03-14"
    assert data["center"] == "Des Moines, IA"
    assert data["artist_shows"]["Zach Bryan"][0]["is_new"] is True
    assert data["venue_shows"]["Wells Fargo Arena"][0]["artist"] == "Zach Bryan"
    assert data["festival_shows"]["Hinterland"][0]["event_name"] == "Hinterland Music Festival"
    assert len(data["coming_soon"]) == 1
    assert data["artists_not_found"] == ["Nobody"]
    assert data["festivals_not_found"] == ["FakeFest"]
    assert data["stale"] is False
