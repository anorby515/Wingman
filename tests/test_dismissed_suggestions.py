"""Tests for dismissed suggestions endpoints."""

import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MINIMAL_CONFIG


@pytest.fixture()
def dismissed_client(tmp_path, monkeypatch):
    """TestClient with DISMISSED_FILE monkeypatched."""
    import backend.main as main_mod

    config_file = tmp_path / "wingman_config.json"
    config_file.write_text(json.dumps(MINIMAL_CONFIG, indent=2))

    dismissed_file = tmp_path / "dismissed_suggestions.json"

    monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
    monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
    monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
    monkeypatch.setattr(main_mod, "GEOCODE_FILE", tmp_path / "geocode_cache.json")
    monkeypatch.setattr(main_mod, "DISMISSED_FILE", dismissed_file)
    monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

    return TestClient(main_mod.app)


# ── GET /api/dismissed-suggestions ───────────────────────────────────────────

class TestListDismissedSuggestions:
    def test_empty_when_no_file(self, dismissed_client):
        r = dismissed_client.get("/api/dismissed-suggestions")
        assert r.status_code == 200
        assert r.json() == {}

    def test_returns_dict_when_file_exists(self, tmp_path, monkeypatch):
        import backend.main as main_mod

        config_file = tmp_path / "wingman_config.json"
        config_file.write_text(json.dumps(MINIMAL_CONFIG, indent=2))

        dismissed_file = tmp_path / "dismissed_suggestions.json"
        dismissed_data = {
            "Some Artist": {
                "dismissed_at": "2026-01-15",
                "resurface_after": "2026-07-17",
                "reason": "user declined",
                "source": "top_artists_short_term",
            }
        }
        dismissed_file.write_text(json.dumps(dismissed_data))

        monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
        monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
        monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
        monkeypatch.setattr(main_mod, "GEOCODE_FILE", tmp_path / "geocode_cache.json")
        monkeypatch.setattr(main_mod, "DISMISSED_FILE", dismissed_file)
        monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

        client = TestClient(main_mod.app)
        r = client.get("/api/dismissed-suggestions")
        assert r.status_code == 200
        data = r.json()
        assert "Some Artist" in data
        assert data["Some Artist"]["source"] == "top_artists_short_term"


# ── POST /api/dismissed-suggestions ──────────────────────────────────────────

class TestAddDismissedSuggestion:
    def test_creates_entry_with_correct_dates(self, dismissed_client):
        r = dismissed_client.post("/api/dismissed-suggestions", json={
            "artist": "Bon Iver",
            "source": "top_artists_medium_term",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["ok"] is True
        assert data["artist"] == "Bon Iver"

        # Verify resurface_after is 183 days from today
        today = date.today()
        expected_resurface = (today + timedelta(days=183)).isoformat()
        assert data["resurface_after"] == expected_resurface

        # Verify the stored data
        r2 = dismissed_client.get("/api/dismissed-suggestions")
        stored = r2.json()
        assert "Bon Iver" in stored
        assert stored["Bon Iver"]["dismissed_at"] == today.isoformat()
        assert stored["Bon Iver"]["resurface_after"] == expected_resurface
        assert stored["Bon Iver"]["reason"] == "user declined"
        assert stored["Bon Iver"]["source"] == "top_artists_medium_term"

    def test_custom_reason(self, dismissed_client):
        r = dismissed_client.post("/api/dismissed-suggestions", json={
            "artist": "Fleet Foxes",
            "reason": "not interested",
            "source": "recently_played",
        })
        assert r.status_code == 201

        r2 = dismissed_client.get("/api/dismissed-suggestions")
        assert r2.json()["Fleet Foxes"]["reason"] == "not interested"


# ── DELETE /api/dismissed-suggestions/{artist} ───────────────────────────────

class TestRemoveDismissedSuggestion:
    def test_removes_entry(self, dismissed_client):
        # Add first
        dismissed_client.post("/api/dismissed-suggestions", json={
            "artist": "Phoebe Bridgers",
            "source": "top_artists_long_term",
        })
        # Delete
        r = dismissed_client.delete("/api/dismissed-suggestions/Phoebe Bridgers")
        assert r.status_code == 200
        assert r.json()["ok"] is True

        # Verify gone
        r2 = dismissed_client.get("/api/dismissed-suggestions")
        assert "Phoebe Bridgers" not in r2.json()

    def test_404_when_not_found(self, dismissed_client):
        r = dismissed_client.delete("/api/dismissed-suggestions/Nobody")
        assert r.status_code == 404
