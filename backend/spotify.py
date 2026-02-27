#!/usr/bin/env python3
"""
Wingman Spotify Module
======================
Handles Spotify OAuth token management and API calls.
Uses only stdlib — no pip dependencies.

Token file: spotify_tokens.json (gitignored, local only)
Redirect URI: http://127.0.0.1:8000/callback
"""

from __future__ import annotations

import base64
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

# ── Constants ────────────────────────────────────────────────────────────────
REDIRECT_URI = "http://127.0.0.1:8000/callback"
SCOPES = "user-follow-read user-follow-modify user-top-read user-read-recently-played"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

TOKENS_FILE = Path(__file__).parent.parent / "spotify_tokens.json"


# ── Token management ─────────────────────────────────────────────────────────

def load_tokens() -> Optional[dict]:
    """Load tokens from spotify_tokens.json. Returns None if not found."""
    if not TOKENS_FILE.exists():
        return None
    try:
        return json.loads(TOKENS_FILE.read_text())
    except Exception:
        return None


def save_tokens(tokens: dict) -> None:
    """Save tokens to spotify_tokens.json."""
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))


def is_connected() -> bool:
    """Return True if spotify_tokens.json exists with a refresh_token."""
    tokens = load_tokens()
    return tokens is not None and bool(tokens.get("refresh_token"))


def get_valid_access_token(client_id: str, client_secret: str) -> Optional[str]:
    """Return a valid access token, refreshing if expired."""
    tokens = load_tokens()
    if not tokens or not tokens.get("refresh_token"):
        return None

    # Check if current access token is still valid (with 60s buffer)
    expires_at = tokens.get("expires_at", 0)
    if time.time() < expires_at - 60:
        return tokens["access_token"]

    # Refresh the access token
    refreshed = _refresh_access_token(tokens["refresh_token"], client_id, client_secret)
    if not refreshed:
        return None

    tokens["access_token"] = refreshed["access_token"]
    tokens["expires_at"] = time.time() + refreshed.get("expires_in", 3600)
    if refreshed.get("refresh_token"):
        tokens["refresh_token"] = refreshed["refresh_token"]
    save_tokens(tokens)
    return tokens["access_token"]


def _refresh_access_token(refresh_token: str, client_id: str, client_secret: str) -> Optional[dict]:
    """Exchange refresh token for new access token."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def exchange_code_for_tokens(code: str, client_id: str, client_secret: str) -> dict:
    """Exchange authorization code for access + refresh tokens. Saves to file."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        token_data = json.loads(resp.read())

    tokens = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "expires_at": time.time() + token_data.get("expires_in", 3600),
        "scope": token_data.get("scope", ""),
    }
    save_tokens(tokens)
    return tokens


def build_auth_url(client_id: str, state: str) -> str:
    """Build the Spotify authorization URL to redirect the user to."""
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "state": state,
    })
    return f"{AUTH_URL}?{params}"


# ── API calls ────────────────────────────────────────────────────────────────

def spotify_get(path: str, access_token: str, params: Optional[dict] = None) -> Any:
    """Make an authenticated GET request to the Spotify API."""
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def spotify_put(path: str, access_token: str, params: Optional[dict] = None) -> int:
    """Make an authenticated PUT request. Returns HTTP status code."""
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        data=b"",  # PUT with empty body
        method="PUT",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
