"""Tests for festival lineup endpoints."""

import json

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MINIMAL_CONFIG


def _config_with_festival(name="Hinterland", url="https://hinterland.com"):
    cfg = dict(MINIMAL_CONFIG)
    cfg["festivals"] = {name: {"url": url, "paused": False}}
    return cfg


@pytest.fixture()
def lineups_client(tmp_path, monkeypatch):
    """TestClient with LINEUPS_FILE monkeypatched and a festival in config."""
    import backend.main as main_mod

    config_file = tmp_path / "wingman_config.json"
    config_file.write_text(json.dumps(_config_with_festival(), indent=2))

    lineups_file = tmp_path / "festival_lineups.json"
    geocode_file = tmp_path / "geocode_cache.json"

    monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
    monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
    monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
    monkeypatch.setattr(main_mod, "GEOCODE_FILE", geocode_file)
    monkeypatch.setattr(main_mod, "LINEUPS_FILE", lineups_file)
    monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

    return TestClient(main_mod.app)


# ── GET /api/festival-lineups ────────────────────────────────────────────────

class TestGetFestivalLineups:
    def test_empty_when_no_file(self, lineups_client):
        r = lineups_client.get("/api/festival-lineups")
        assert r.status_code == 200
        assert r.json() == {}

    def test_returns_data_when_file_exists(self, tmp_path, monkeypatch):
        import backend.main as main_mod

        config_file = tmp_path / "wingman_config.json"
        config_file.write_text(json.dumps(_config_with_festival(), indent=2))

        lineups_file = tmp_path / "festival_lineups.json"
        lineups_data = {
            "Hinterland": {
                "lineup_url": "https://hinterland.com/lineup",
                "days": [{"label": "Day 1", "artists": [{"name": "Caamp", "headliner": False}]}],
            }
        }
        lineups_file.write_text(json.dumps(lineups_data))

        monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
        monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
        monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
        monkeypatch.setattr(main_mod, "GEOCODE_FILE", tmp_path / "geocode_cache.json")
        monkeypatch.setattr(main_mod, "LINEUPS_FILE", lineups_file)
        monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

        client = TestClient(main_mod.app)
        r = client.get("/api/festival-lineups")
        assert r.status_code == 200
        data = r.json()
        assert "Hinterland" in data
        assert data["Hinterland"]["days"][0]["artists"][0]["name"] == "Caamp"

    def test_enriches_with_geocode_data(self, tmp_path, monkeypatch):
        import backend.main as main_mod

        config_file = tmp_path / "wingman_config.json"
        config_file.write_text(json.dumps(_config_with_festival(), indent=2))

        lineups_file = tmp_path / "festival_lineups.json"
        lineups_data = {
            "Hinterland": {
                "venue": "Avenue of the Saints",
                "city": "St. Charles, IA",
                "days": [],
            }
        }
        lineups_file.write_text(json.dumps(lineups_data))

        geocode_file = tmp_path / "geocode_cache.json"
        geocode_file.write_text(json.dumps({
            "Avenue of the Saints, St. Charles, IA": {"lat": 41.29, "lon": -93.07}
        }))

        monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
        monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
        monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
        monkeypatch.setattr(main_mod, "GEOCODE_FILE", geocode_file)
        monkeypatch.setattr(main_mod, "LINEUPS_FILE", lineups_file)
        monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

        client = TestClient(main_mod.app)
        r = client.get("/api/festival-lineups")
        data = r.json()
        assert data["Hinterland"]["lat"] == 41.29
        assert data["Hinterland"]["lon"] == -93.07


# ── PUT /api/festival-lineups/{name} ─────────────────────────────────────────

class TestPutFestivalLineup:
    def test_saves_lineup(self, lineups_client):
        r = lineups_client.put("/api/festival-lineups/Hinterland", json={
            "venue": "Avenue of the Saints",
            "city": "St. Charles, IA",
            "days": [
                {"label": "Friday", "date": "Aug 7, 2026", "artists": [
                    {"name": "Zach Bryan", "headliner": True},
                    {"name": "Caamp", "headliner": False},
                ]},
            ],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["venue"] == "Avenue of the Saints"
        assert len(data["days"]) == 1
        assert data["days"][0]["artists"][0]["name"] == "Zach Bryan"

    def test_404_when_festival_not_in_config(self, lineups_client):
        r = lineups_client.put("/api/festival-lineups/FakeFest", json={
            "days": [],
        })
        assert r.status_code == 404

    def test_merges_with_existing(self, lineups_client):
        # First PUT
        lineups_client.put("/api/festival-lineups/Hinterland", json={
            "image_url": "https://example.com/poster.jpg",
            "venue": "Avenue of the Saints",
            "city": "St. Charles, IA",
            "days": [{"label": "Day 1", "artists": []}],
        })

        # Second PUT without image_url — existing image_url should be preserved
        r = lineups_client.put("/api/festival-lineups/Hinterland", json={
            "days": [{"label": "Day 1", "artists": [{"name": "Caamp", "headliner": False}]}],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["image_url"] == "https://example.com/poster.jpg"
        assert data["venue"] == "Avenue of the Saints"
        assert data["city"] == "St. Charles, IA"


# ── POST /api/festival-lineups/refresh ───────────────────────────────────────

class TestRefreshFestivalLineups:
    def test_500_when_script_missing(self, tmp_path, monkeypatch):
        """Monkeypatch REPO to a temp dir so the script doesn't exist."""
        import backend.main as main_mod

        config_file = tmp_path / "wingman_config.json"
        config_file.write_text(json.dumps(_config_with_festival(), indent=2))

        monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
        monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
        monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
        monkeypatch.setattr(main_mod, "GEOCODE_FILE", tmp_path / "geocode_cache.json")
        monkeypatch.setattr(main_mod, "LINEUPS_FILE", tmp_path / "festival_lineups.json")
        monkeypatch.setattr(main_mod, "REPO", tmp_path)
        monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

        client = TestClient(main_mod.app)
        r = client.post("/api/festival-lineups/refresh")
        assert r.status_code == 500
        assert "Scraper script not found" in r.json()["detail"]
