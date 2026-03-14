"""Tests for backend/spotify.py — token management and API calls."""

import io
import json
import time
import urllib.error
from unittest.mock import MagicMock

import pytest

import backend.spotify as spotify_mod


# ── load_tokens ──────────────────────────────────────────────────────────────

class TestLoadTokens:
    def test_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", tmp_path / "nope.json")
        assert spotify_mod.load_tokens() is None

    def test_file_exists(self, tmp_path, monkeypatch):
        tokens = {"access_token": "abc", "refresh_token": "xyz"}
        f = tmp_path / "tokens.json"
        f.write_text(json.dumps(tokens))
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", f)
        result = spotify_mod.load_tokens()
        assert result == tokens

    def test_corrupt_file(self, tmp_path, monkeypatch):
        f = tmp_path / "tokens.json"
        f.write_text("not json!!!")
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", f)
        assert spotify_mod.load_tokens() is None


# ── save_tokens ──────────────────────────────────────────────────────────────

class TestSaveTokens:
    def test_writes_json(self, tmp_path, monkeypatch):
        f = tmp_path / "tokens.json"
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", f)
        tokens = {"access_token": "abc", "refresh_token": "xyz"}
        spotify_mod.save_tokens(tokens)
        assert json.loads(f.read_text()) == tokens


# ── is_connected ─────────────────────────────────────────────────────────────

class TestIsConnected:
    def test_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", tmp_path / "nope.json")
        assert spotify_mod.is_connected() is False

    def test_no_refresh_token(self, tmp_path, monkeypatch):
        f = tmp_path / "tokens.json"
        f.write_text(json.dumps({"access_token": "abc"}))
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", f)
        assert spotify_mod.is_connected() is False

    def test_with_refresh_token(self, tmp_path, monkeypatch):
        f = tmp_path / "tokens.json"
        f.write_text(json.dumps({"access_token": "abc", "refresh_token": "xyz"}))
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", f)
        assert spotify_mod.is_connected() is True


# ── get_valid_access_token ───────────────────────────────────────────────────

class TestGetValidAccessToken:
    def test_no_tokens(self, tmp_path, monkeypatch):
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", tmp_path / "nope.json")
        assert spotify_mod.get_valid_access_token("cid", "csec") is None

    def test_token_still_valid(self, tmp_path, monkeypatch):
        f = tmp_path / "tokens.json"
        f.write_text(json.dumps({
            "access_token": "valid_token",
            "refresh_token": "rtoken",
            "expires_at": time.time() + 3600,
        }))
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", f)
        result = spotify_mod.get_valid_access_token("cid", "csec")
        assert result == "valid_token"

    def test_token_expired_refreshes(self, tmp_path, monkeypatch):
        f = tmp_path / "tokens.json"
        f.write_text(json.dumps({
            "access_token": "old_token",
            "refresh_token": "rtoken",
            "expires_at": time.time() - 100,
        }))
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", f)

        monkeypatch.setattr(
            spotify_mod, "_refresh_access_token",
            lambda rt, cid, csec: {"access_token": "new_token", "expires_in": 3600},
        )
        result = spotify_mod.get_valid_access_token("cid", "csec")
        assert result == "new_token"

        # Verify tokens were saved with new access_token
        saved = json.loads(f.read_text())
        assert saved["access_token"] == "new_token"

    def test_token_expired_refresh_fails(self, tmp_path, monkeypatch):
        f = tmp_path / "tokens.json"
        f.write_text(json.dumps({
            "access_token": "old_token",
            "refresh_token": "rtoken",
            "expires_at": time.time() - 100,
        }))
        monkeypatch.setattr(spotify_mod, "TOKENS_FILE", f)
        monkeypatch.setattr(
            spotify_mod, "_refresh_access_token",
            lambda rt, cid, csec: None,
        )
        assert spotify_mod.get_valid_access_token("cid", "csec") is None


# ── build_auth_url ───────────────────────────────────────────────────────────

class TestBuildAuthUrl:
    def test_returns_proper_url(self):
        url = spotify_mod.build_auth_url("my_client_id", "my_state")
        assert url.startswith("https://accounts.spotify.com/authorize?")
        assert "client_id=my_client_id" in url
        assert "state=my_state" in url
        assert "response_type=code" in url
        assert "redirect_uri=" in url
        assert "scope=" in url


# ── _refresh_access_token ────────────────────────────────────────────────────

class TestRefreshAccessToken:
    def test_success(self, monkeypatch):
        response_data = json.dumps({"access_token": "new_at", "expires_in": 3600}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda req, timeout=None, context=None: mock_resp,
        )
        result = spotify_mod._refresh_access_token("rt", "cid", "csec")
        assert result["access_token"] == "new_at"

    def test_failure(self, monkeypatch):
        def raise_error(*args, **kwargs):
            raise urllib.error.HTTPError(
                url="https://accounts.spotify.com/api/token",
                code=400, msg="Bad Request", hdrs={}, fp=io.BytesIO(b""),
            )

        monkeypatch.setattr("urllib.request.urlopen", raise_error)
        result = spotify_mod._refresh_access_token("rt", "cid", "csec")
        assert result is None


# ── spotify_get ──────────────────────────────────────────────────────────────

class TestSpotifyGet:
    def test_success(self, monkeypatch):
        response_data = json.dumps({"display_name": "Test User"}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda req, timeout=None, context=None: mock_resp,
        )
        result = spotify_mod.spotify_get("/me", "token123")
        assert result["display_name"] == "Test User"

    def test_with_params(self, monkeypatch):
        response_data = json.dumps({"items": []}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        captured_req = {}

        def mock_urlopen(req, timeout=None, context=None):
            captured_req["url"] = req.full_url
            return mock_resp

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        spotify_mod.spotify_get("/me/following", "token", params={"type": "artist"})
        assert "type=artist" in captured_req["url"]

    def test_error(self, monkeypatch):
        def raise_error(*args, **kwargs):
            raise urllib.error.HTTPError(
                url="https://api.spotify.com/v1/me",
                code=401, msg="Unauthorized", hdrs={}, fp=io.BytesIO(b""),
            )

        monkeypatch.setattr("urllib.request.urlopen", raise_error)
        with pytest.raises(urllib.error.HTTPError):
            spotify_mod.spotify_get("/me", "bad_token")


# ── spotify_put ──────────────────────────────────────────────────────────────

class TestSpotifyPut:
    def test_success(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda req, timeout=None, context=None: mock_resp,
        )
        status = spotify_mod.spotify_put("/me/following", "token", params={"type": "artist", "ids": "123"})
        assert status == 204

    def test_http_error_returns_code(self, monkeypatch):
        def raise_error(*args, **kwargs):
            raise urllib.error.HTTPError(
                url="https://api.spotify.com/v1/me/following",
                code=403, msg="Forbidden", hdrs={}, fp=io.BytesIO(b""),
            )

        monkeypatch.setattr("urllib.request.urlopen", raise_error)
        status = spotify_mod.spotify_put("/me/following", "token")
        assert status == 403
