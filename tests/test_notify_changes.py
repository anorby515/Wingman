"""Tests for scripts/notify_changes.py — pure functions, no network."""

import io
import json
import os
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

# The script is at scripts/notify_changes.py — import it by path manipulation
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import notify_changes


# ── parse_show_date ──────────────────────────────────────────────────────────

class TestParseShowDate:
    def test_valid_date(self):
        result = notify_changes.parse_show_date("Mar 21, 2026")
        assert result == datetime(2026, 3, 21)

    def test_invalid_date(self):
        assert notify_changes.parse_show_date("not a date") is None

    def test_none(self):
        assert notify_changes.parse_show_date(None) is None


# ── is_future_show ───────────────────────────────────────────────────────────

class TestIsFutureShow:
    def test_past_show(self):
        today = datetime(2026, 3, 14)
        assert notify_changes.is_future_show("Mar 01, 2026", today) is False

    def test_future_show(self):
        today = datetime(2026, 3, 14)
        assert notify_changes.is_future_show("Jun 01, 2026", today) is True

    def test_today_show(self):
        today = datetime(2026, 3, 14)
        assert notify_changes.is_future_show("Mar 14, 2026", today) is True

    def test_unparseable_returns_true(self):
        today = datetime(2026, 3, 14)
        assert notify_changes.is_future_show("TBD", today) is True


# ── build_show_keys ──────────────────────────────────────────────────────────

class TestBuildShowKeys:
    def test_extracts_artist_keys(self):
        today = datetime(2026, 3, 14)
        summary = {
            "artist_shows": {
                "Caamp": [
                    {"date": "Jun 1, 2026", "venue": "The Sylvee"},
                ]
            },
            "venue_shows": {},
            "festival_shows": {},
        }
        artist_keys, venue_keys, festival_keys = notify_changes.build_show_keys(summary, today)
        assert "Caamp|Jun 1, 2026|The Sylvee" in artist_keys
        assert len(venue_keys) == 0
        assert len(festival_keys) == 0

    def test_extracts_venue_keys(self):
        today = datetime(2026, 3, 14)
        summary = {
            "artist_shows": {},
            "venue_shows": {
                "Wells Fargo Arena": [
                    {"date": "Jun 20, 2026", "artist": "Zach Bryan"},
                ]
            },
            "festival_shows": {},
        }
        artist_keys, venue_keys, festival_keys = notify_changes.build_show_keys(summary, today)
        assert "Wells Fargo Arena|Jun 20, 2026|Zach Bryan" in venue_keys

    def test_extracts_festival_keys(self):
        today = datetime(2026, 3, 14)
        summary = {
            "artist_shows": {},
            "venue_shows": {},
            "festival_shows": {
                "Hinterland": [
                    {"date": "Aug 1, 2026", "venue": "Avenue of the Saints"},
                ]
            },
        }
        artist_keys, venue_keys, festival_keys = notify_changes.build_show_keys(summary, today)
        assert "Hinterland|Aug 1, 2026|Avenue of the Saints" in festival_keys

    def test_filters_past_shows(self):
        today = datetime(2026, 3, 14)
        summary = {
            "artist_shows": {
                "Caamp": [
                    {"date": "Jan 1, 2026", "venue": "Past Venue"},
                    {"date": "Jun 1, 2026", "venue": "Future Venue"},
                ]
            },
            "venue_shows": {},
            "festival_shows": {},
        }
        artist_keys, _, _ = notify_changes.build_show_keys(summary, today)
        assert len(artist_keys) == 1
        assert "Future Venue" in list(artist_keys)[0]


# ── find_onsale_imminent ─────────────────────────────────────────────────────

class TestFindOnsaleImminent:
    def test_finds_shows_within_48h(self):
        now = datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
        summary = {
            "coming_soon": [
                {
                    "artist": "Tyler Childers",
                    "onsale_datetime": "2026-03-15T10:00:00Z",
                    "onsale_tbd": False,
                    "venue": "Kinnick",
                    "date": "Sep 1, 2026",
                },
            ]
        }
        result = notify_changes.find_onsale_imminent(summary, now)
        assert len(result) == 1
        assert result[0]["artist"] == "Tyler Childers"

    def test_skips_tbd(self):
        now = datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
        summary = {
            "coming_soon": [
                {
                    "artist": "Some Artist",
                    "onsale_datetime": "2026-03-15T10:00:00Z",
                    "onsale_tbd": True,
                    "venue": "Venue",
                    "date": "Sep 1, 2026",
                },
            ]
        }
        result = notify_changes.find_onsale_imminent(summary, now)
        assert len(result) == 0

    def test_skips_outside_window(self):
        now = datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
        summary = {
            "coming_soon": [
                {
                    "artist": "Far Out Artist",
                    "onsale_datetime": "2026-03-20T10:00:00Z",
                    "onsale_tbd": False,
                    "venue": "Venue",
                    "date": "Sep 1, 2026",
                },
            ]
        }
        result = notify_changes.find_onsale_imminent(summary, now)
        assert len(result) == 0

    def test_skips_no_onsale_datetime(self):
        now = datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc)
        summary = {
            "coming_soon": [
                {
                    "artist": "Unknown",
                    "onsale_datetime": None,
                    "onsale_tbd": False,
                    "venue": "Venue",
                    "date": "Sep 1, 2026",
                },
            ]
        }
        result = notify_changes.find_onsale_imminent(summary, now)
        assert len(result) == 0


# ── key_to_display ───────────────────────────────────────────────────────────

class TestKeyToDisplay:
    def test_artist_key(self):
        result = notify_changes.key_to_display("Caamp|Jun 1, 2026|The Sylvee", "artist")
        assert result == "Caamp @ The Sylvee — Jun 1, 2026"

    def test_venue_key(self):
        result = notify_changes.key_to_display("Wells Fargo|Jun 20, 2026|Zach Bryan", "venue")
        assert result == "Zach Bryan @ Wells Fargo — Jun 20, 2026"

    def test_festival_key(self):
        result = notify_changes.key_to_display("Hinterland|Aug 1, 2026|Avenue", "festival")
        assert result == "Hinterland @ Avenue — Aug 1, 2026"

    def test_malformed_key(self):
        result = notify_changes.key_to_display("no pipes here", "artist")
        assert result == "no pipes here"


# ── format_onsale_time ───────────────────────────────────────────────────────

class TestFormatOnsaleTime:
    def test_valid_iso_datetime(self):
        result = notify_changes.format_onsale_time("2026-03-15T16:00:00Z")
        assert "CT" in result
        assert "Mar 15" in result

    def test_invalid_string(self):
        result = notify_changes.format_onsale_time("not a date")
        assert result == "not a date"


# ── format_message ───────────────────────────────────────────────────────────

class TestFormatMessage:
    def test_with_all_sections(self):
        today = datetime(2026, 3, 14)
        msg = notify_changes.format_message(
            new_artist_shows=["Caamp|Jun 1, 2026|The Sylvee"],
            new_venue_events=["Wells Fargo|Jun 20, 2026|Zach Bryan"],
            new_festival_events=["Hinterland|Aug 1, 2026|Avenue"],
            onsale_imminent=[{
                "artist": "Tyler Childers",
                "venue": "Kinnick",
                "date": "Sep 1, 2026",
                "onsale_datetime": "2026-03-15T16:00:00Z",
            }],
            today=today,
        )
        assert "Wingman" in msg
        assert "NEW SHOWS:" in msg
        assert "NEW AT VENUES:" in msg
        assert "NEW FESTIVAL EVENTS:" in msg
        assert "ON SALE SOON:" in msg
        assert "Tyler Childers" in msg

    def test_empty_sections(self):
        today = datetime(2026, 3, 14)
        msg = notify_changes.format_message(
            new_artist_shows=["Caamp|Jun 1, 2026|The Sylvee"],
            new_venue_events=[],
            new_festival_events=[],
            onsale_imminent=[],
            today=today,
        )
        assert "NEW SHOWS:" in msg
        assert "NEW AT VENUES:" not in msg

    def test_truncation_at_limit(self):
        today = datetime(2026, 3, 14)
        # Generate a lot of artist shows to exceed limit
        many_shows = [f"Artist {i}|Jun {i % 28 + 1}, 2026|Venue {i}" for i in range(200)]
        msg = notify_changes.format_message(
            new_artist_shows=many_shows,
            new_venue_events=[],
            new_festival_events=[],
            onsale_imminent=[],
            today=today,
        )
        assert len(msg) <= 3600  # MESSAGE_MAX_CHARS + some margin
        assert "(+" in msg and "more)" in msg


# ── send_ntfy ────────────────────────────────────────────────────────────────

class TestSendNtfy:
    def test_success(self, monkeypatch):
        monkeypatch.setenv("NTFY_TOPIC", "test-topic")

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": "abc123"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda req, timeout=None: mock_resp,
        )
        assert notify_changes.send_ntfy("test body") is True

    def test_missing_env_var(self, monkeypatch):
        monkeypatch.delenv("NTFY_TOPIC", raising=False)
        assert notify_changes.send_ntfy("test body") is False

    def test_http_error(self, monkeypatch):
        monkeypatch.setenv("NTFY_TOPIC", "test-topic")

        def raise_error(req, timeout=None):
            raise urllib.error.HTTPError(
                url="https://ntfy.sh/test",
                code=500, msg="Internal Server Error",
                hdrs={}, fp=io.BytesIO(b"server error"),
            )

        monkeypatch.setattr("urllib.request.urlopen", raise_error)
        assert notify_changes.send_ntfy("test body") is False


# ── save_baseline ────────────────────────────────────────────────────────────

class TestSaveBaseline:
    def test_writes_correct_structure(self, tmp_path, monkeypatch):
        baseline_path = tmp_path / "notification_baseline.json"
        monkeypatch.setattr(notify_changes, "BASELINE_PATH", baseline_path)

        artist_keys = {"Caamp|Jun 1, 2026|The Sylvee", "Zach Bryan|Jun 20, 2026|WFA"}
        venue_keys = {"Wells Fargo|Jun 20, 2026|Zach Bryan"}
        festival_keys = {"Hinterland|Aug 1, 2026|Avenue"}

        notify_changes.save_baseline(artist_keys, venue_keys, festival_keys)

        data = json.loads(baseline_path.read_text())
        assert "updated_at" in data
        assert sorted(data["artist_show_keys"]) == sorted(artist_keys)
        assert data["venue_show_keys"] == sorted(venue_keys)
        assert data["festival_show_keys"] == sorted(festival_keys)
