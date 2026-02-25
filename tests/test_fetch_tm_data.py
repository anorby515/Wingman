"""Tests for scripts/fetch_tm_data.py — the GitHub Action data fetch script."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure repo root is on path so the script can import backend.ticketmaster
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from backend.ticketmaster import RefreshResult
from scripts.fetch_tm_data import build_static_data, build_summary


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_config():
    return {
        "center_city": "Des Moines, IA",
        "artists": {
            "Tyler Childers": {"url": "https://example.com", "genre": "Country / Americana", "paused": False},
            "Zach Bryan": {"url": "https://example.com", "genre": "Country / Americana", "paused": False},
        },
        "venues": {
            "Wells Fargo Arena": {"url": "https://example.com", "city": "Des Moines, IA", "is_local": True, "paused": False},
        },
        "festivals": {},
    }


@pytest.fixture
def sample_result():
    result = RefreshResult()
    result.artist_shows = {
        "Tyler Childers": [
            {
                "date": "Aug 15, 2026",
                "raw_date": "2026-08-15",
                "venue": "Kinnick Stadium",
                "city": "Iowa City, IA",
                "not_yet_on_sale": False,
                "onsale_datetime": None,
                "onsale_tbd": False,
                "presales": [],
                "ticketmaster_url": "https://tm.com/1",
                "lat": 41.65,
                "lon": -91.55,
                "genre": "Country / Americana",
            },
            {
                "date": "Sep 1, 2026",
                "raw_date": "2026-09-01",
                "venue": "Red Rocks",
                "city": "Morrison, CO",
                "not_yet_on_sale": True,
                "onsale_datetime": "2026-03-15T10:00:00Z",
                "onsale_tbd": False,
                "presales": [{"name": "Fan Club", "start_datetime": "2026-03-13T10:00:00Z", "end_datetime": None}],
                "ticketmaster_url": "https://tm.com/2",
                "lat": 39.66,
                "lon": -105.21,
                "genre": "Country / Americana",
            },
        ],
    }
    result.venue_shows = {
        "Wells Fargo Arena": [
            {
                "date": "Oct 10, 2026",
                "raw_date": "2026-10-10",
                "venue": "Wells Fargo Arena",
                "city": "Des Moines, IA",
                "not_yet_on_sale": False,
                "onsale_datetime": None,
                "onsale_tbd": False,
                "presales": [],
                "ticketmaster_url": "https://tm.com/3",
                "lat": 41.59,
                "lon": -93.62,
                "artist": "Zach Bryan",
            },
        ],
    }
    result.festival_shows = {}
    result.artists_not_found = []
    result.venues_not_found = []
    result.festivals_not_found = []
    result.last_refreshed = "2026-02-25T10:00:00+00:00"
    return result


@pytest.fixture
def geocode_cache():
    return {
        "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
    }


# ── build_summary tests ──────────────────────────────────────────────────────

class TestBuildSummary:
    def test_basic_summary_structure(self, sample_result, sample_config, geocode_cache):
        summary = build_summary(sample_result, sample_config, geocode_cache, None)

        assert "generated_at" in summary
        assert summary["center"] == "Des Moines, IA"
        assert summary["center_lat"] == 41.5868
        assert summary["center_lon"] == -93.625
        assert "artist_shows" in summary
        assert "venue_shows" in summary
        assert "changes" in summary
        assert "coming_soon" in summary
        assert "coming_soon_fetched" in summary

    def test_artist_shows_converted(self, sample_result, sample_config, geocode_cache):
        summary = build_summary(sample_result, sample_config, geocode_cache, None)

        assert "Tyler Childers" in summary["artist_shows"]
        shows = summary["artist_shows"]["Tyler Childers"]
        assert len(shows) == 2
        assert shows[0]["date"] == "Aug 15, 2026"
        assert shows[0]["venue"] == "Kinnick Stadium"
        assert shows[0]["status"] == "on_sale"
        assert shows[0]["lat"] == 41.65

    def test_coming_soon_extracted(self, sample_result, sample_config, geocode_cache):
        summary = build_summary(sample_result, sample_config, geocode_cache, None)

        assert len(summary["coming_soon"]) == 1
        cs = summary["coming_soon"][0]
        assert cs["artist"] == "Tyler Childers"
        assert cs["onsale_datetime"] == "2026-03-15T10:00:00Z"
        assert len(cs["presales"]) == 1

    def test_venue_shows_with_tracked_flag(self, sample_result, sample_config, geocode_cache):
        summary = build_summary(sample_result, sample_config, geocode_cache, None)

        assert "Wells Fargo Arena" in summary["venue_shows"]
        vs = summary["venue_shows"]["Wells Fargo Arena"]
        assert len(vs) == 1
        assert vs[0]["artist"] == "Zach Bryan"
        assert vs[0]["tracked"] is True  # Zach Bryan is in config

    def test_all_new_on_first_run(self, sample_result, sample_config, geocode_cache):
        """With no previous summary, all shows should be marked as new."""
        summary = build_summary(sample_result, sample_config, geocode_cache, None)

        for show in summary["artist_shows"]["Tyler Childers"]:
            assert show["is_new"] is True
        assert summary["changes"]["total_added"] == 2

    def test_diff_detection(self, sample_result, sample_config, geocode_cache):
        """Shows that existed in previous summary should not be marked as new."""
        prev = {
            "artist_shows": {
                "Tyler Childers": [
                    {"date": "Aug 15, 2026", "venue": "Kinnick Stadium", "city": "Iowa City, IA", "status": "on_sale"},
                ],
            },
            "venue_shows": {},
        }
        summary = build_summary(sample_result, sample_config, geocode_cache, prev)

        shows = summary["artist_shows"]["Tyler Childers"]
        # First show existed before → not new
        assert shows[0]["is_new"] is False
        # Second show is new
        assert shows[1]["is_new"] is True
        assert summary["changes"]["total_added"] == 1

    def test_removed_show_detection(self, sample_result, sample_config, geocode_cache):
        """Shows in previous but not in new should count as removed."""
        prev = {
            "artist_shows": {
                "Tyler Childers": [
                    {"date": "Aug 15, 2026", "venue": "Kinnick Stadium", "city": "Iowa City, IA", "status": "on_sale"},
                    {"date": "Jul 4, 2026", "venue": "Somewhere", "city": "Somewhere, IA", "status": "on_sale"},
                ],
            },
            "venue_shows": {},
        }
        summary = build_summary(sample_result, sample_config, geocode_cache, prev)

        assert summary["changes"]["total_removed"] == 1
        removed = summary["changes"]["artists"]["Tyler Childers"]["removed"]
        assert len(removed) == 1
        assert removed[0]["venue"] == "Somewhere"


# ── build_static_data tests ──────────────────────────────────────────────────

class TestBuildStaticData:
    def test_basic_structure(self, sample_result, sample_config, geocode_cache):
        summary = build_summary(sample_result, sample_config, geocode_cache, None)
        static = build_static_data(sample_result, sample_config, geocode_cache, summary)

        assert "state" in static
        assert "config" in static
        assert "coming_soon" in static
        assert "coming_soon_fetched" in static

    def test_state_contains_raw_shows(self, sample_result, sample_config, geocode_cache):
        """Static data should contain raw TM format shows (not SummaryShow format)."""
        summary = build_summary(sample_result, sample_config, geocode_cache, None)
        static = build_static_data(sample_result, sample_config, geocode_cache, summary)

        artist_shows = static["state"]["artist_shows"]
        assert "Tyler Childers" in artist_shows
        show = artist_shows["Tyler Childers"][0]
        # Raw TM format fields
        assert "not_yet_on_sale" in show
        assert "ticketmaster_url" in show
        assert "raw_date" in show

    def test_config_strips_secrets(self, sample_result, sample_config, geocode_cache):
        """Config should only have genre, paused, url — no API keys."""
        sample_config["ticketmaster_api_key"] = "secret123"
        summary = build_summary(sample_result, sample_config, geocode_cache, None)
        static = build_static_data(sample_result, sample_config, geocode_cache, summary)

        cfg = static["config"]
        assert cfg["center_city"] == "Des Moines, IA"
        assert "Tyler Childers" in cfg["artists"]
        assert cfg["artists"]["Tyler Childers"]["genre"] == "Country / Americana"
        assert "ticketmaster_api_key" not in cfg

    def test_center_coordinates(self, sample_result, sample_config, geocode_cache):
        summary = build_summary(sample_result, sample_config, geocode_cache, None)
        static = build_static_data(sample_result, sample_config, geocode_cache, summary)

        assert static["state"]["center_lat"] == 41.5868
        assert static["state"]["center_lon"] == -93.625

    def test_venue_config_with_coords(self, sample_result, sample_config, geocode_cache):
        geocode_cache["Des Moines, IA"] = {"lat": 41.5868, "lon": -93.625}
        summary = build_summary(sample_result, sample_config, geocode_cache, None)
        static = build_static_data(sample_result, sample_config, geocode_cache, summary)

        venues = static["config"]["venues"]
        assert "Wells Fargo Arena" in venues
        assert venues["Wells Fargo Arena"]["lat"] == 41.5868
