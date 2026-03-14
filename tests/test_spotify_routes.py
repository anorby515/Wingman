"""Tests for Spotify OAuth routes in backend/main.py."""

import json

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MINIMAL_CONFIG


@pytest.fixture()
def spotify_client(tmp_path, monkeypatch):
    """TestClient with Spotify-related paths monkeypatched."""
    import backend.main as main_mod

    config_file = tmp_path / "wingman_config.json"
    config_file.write_text(json.dumps(MINIMAL_CONFIG, indent=2))

    tokens_file = tmp_path / "spotify_tokens.json"

    monkeypatch.setattr(main_mod, "CONFIG_FILE", config_file)
    monkeypatch.setattr(main_mod, "TRACKED_FILE", tmp_path / "tracked.json")
    monkeypatch.setattr(main_mod, "FLAGGED_FILE", tmp_path / "flagged_items.json")
    monkeypatch.setattr(main_mod, "GEOCODE_FILE", tmp_path / "geocode_cache.json")
    monkeypatch.setattr(main_mod, "SPOTIFY_TOKENS_FILE", tokens_file)
    monkeypatch.setattr(main_mod, "_geocode", lambda loc: None)

    return TestClient(main_mod.app)


# ── GET /api/spotify/status ──────────────────────────────────────────────────

class TestSpotifyStatus:
    def test_not_connected_no_tokens(self, spotify_client, monkeypatch):
        import backend.main as main_mod
        monkeypatch.setattr(main_mod.spotify_mod, "is_connected", lambda: False)
        r = spotify_client.get("/api/spotify/status")
        assert r.status_code == 200
        data = r.json()
        assert data["connected"] is False
        assert data["display_name"] is None

    def test_connected_with_tokens(self, spotify_client, monkeypatch):
        import backend.main as main_mod
        monkeypatch.setattr(main_mod.spotify_mod, "is_connected", lambda: True)
        monkeypatch.setattr(
            main_mod.spotify_mod, "get_valid_access_token",
            lambda cid, csec: "valid_token",
        )
        monkeypatch.setattr(
            main_mod.spotify_mod, "spotify_get",
            lambda path, token: {"display_name": "TestUser"},
        )
        # Need spotify creds in config
        cfg = json.loads(main_mod.CONFIG_FILE.read_text())
        cfg["spotify_client_id"] = "test_cid"
        cfg["spotify_client_secret"] = "test_csec"
        main_mod.CONFIG_FILE.write_text(json.dumps(cfg))

        r = spotify_client.get("/api/spotify/status")
        assert r.status_code == 200
        data = r.json()
        assert data["connected"] is True
        assert data["display_name"] == "TestUser"


# ── GET /auth/spotify ────────────────────────────────────────────────────────

class TestAuthSpotify:
    def test_redirect_when_configured(self, spotify_client, monkeypatch):
        import backend.main as main_mod
        cfg = json.loads(main_mod.CONFIG_FILE.read_text())
        cfg["spotify_client_id"] = "my_client_id"
        main_mod.CONFIG_FILE.write_text(json.dumps(cfg))

        r = spotify_client.get("/auth/spotify", follow_redirects=False)
        assert r.status_code == 307
        location = r.headers["location"]
        assert "accounts.spotify.com/authorize" in location
        assert "client_id=my_client_id" in location

    def test_400_when_not_configured(self, spotify_client):
        r = spotify_client.get("/auth/spotify")
        assert r.status_code == 400
        assert "Client ID" in r.json()["detail"]


# ── GET /callback ────────────────────────────────────────────────────────────

class TestSpotifyCallback:
    def test_exchanges_code_for_tokens(self, spotify_client, monkeypatch):
        import backend.main as main_mod
        cfg = json.loads(main_mod.CONFIG_FILE.read_text())
        cfg["spotify_client_id"] = "cid"
        cfg["spotify_client_secret"] = "csec"
        main_mod.CONFIG_FILE.write_text(json.dumps(cfg))

        monkeypatch.setattr(
            main_mod.spotify_mod, "exchange_code_for_tokens",
            lambda code, cid, csec: {"access_token": "at", "refresh_token": "rt"},
        )

        r = spotify_client.get("/callback", params={"code": "auth_code_123"}, follow_redirects=False)
        assert r.status_code == 307
        assert "spotify_connected=1" in r.headers["location"]

    def test_handles_error_param(self, spotify_client):
        r = spotify_client.get("/callback", params={"error": "access_denied"}, follow_redirects=False)
        assert r.status_code == 307
        assert "spotify_error=access_denied" in r.headers["location"]

    def test_handles_missing_code(self, spotify_client):
        r = spotify_client.get("/callback")
        assert r.status_code == 400
        assert "Missing authorization code" in r.json()["detail"]

    def test_exchange_failure_redirects_with_error(self, spotify_client, monkeypatch):
        import backend.main as main_mod
        cfg = json.loads(main_mod.CONFIG_FILE.read_text())
        cfg["spotify_client_id"] = "cid"
        cfg["spotify_client_secret"] = "csec"
        main_mod.CONFIG_FILE.write_text(json.dumps(cfg))

        def fail_exchange(code, cid, csec):
            raise RuntimeError("Token exchange failed")

        monkeypatch.setattr(main_mod.spotify_mod, "exchange_code_for_tokens", fail_exchange)

        r = spotify_client.get("/callback", params={"code": "bad_code"}, follow_redirects=False)
        assert r.status_code == 307
        assert "spotify_error=" in r.headers["location"]


# ── DELETE /api/spotify/disconnect ───────────────────────────────────────────

class TestSpotifyDisconnect:
    def test_removes_token_file(self, spotify_client, monkeypatch):
        import backend.main as main_mod
        # Create the tokens file
        main_mod.SPOTIFY_TOKENS_FILE.write_text(json.dumps({"access_token": "at"}))

        r = spotify_client.delete("/api/spotify/disconnect")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert not main_mod.SPOTIFY_TOKENS_FILE.exists()

    def test_succeeds_even_if_no_file(self, spotify_client):
        r = spotify_client.delete("/api/spotify/disconnect")
        assert r.status_code == 200
        assert r.json()["ok"] is True
