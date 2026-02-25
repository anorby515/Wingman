"""Tests for backend/ticketmaster.py shared module."""

from datetime import datetime, timezone
from unittest.mock import patch

from backend.ticketmaster import (
    RefreshProgress,
    RefreshResult,
    build_show,
    detect_triggers,
    fetch_artist_shows,
    name_matches,
)


# ── build_show tests ─────────────────────────────────────────────────────────

class TestBuildShow:
    def _make_event(self, **overrides):
        """Create a minimal TM event dict for testing."""
        event = {
            "name": "Test Event",
            "url": "https://tm.com/event/1",
            "dates": {"start": {"localDate": "2026-08-15"}},
            "sales": {
                "public": {
                    "startDateTime": "2026-01-01T10:00:00Z",
                    "startTBD": False,
                },
            },
            "_embedded": {
                "venues": [{
                    "name": "Test Venue",
                    "city": {"name": "Des Moines"},
                    "state": {"stateCode": "IA"},
                    "country": {"countryCode": "US"},
                }],
                "attractions": [{"name": "Test Artist"}],
            },
        }
        event.update(overrides)
        return event

    def test_basic_show(self):
        now = datetime(2026, 2, 25, tzinfo=timezone.utc)
        event = self._make_event()
        show = build_show(event, now)
        assert show is not None
        assert show["venue"] == "Test Venue"
        assert show["city"] == "Des Moines, IA"
        assert show["date"] == "Aug 15, 2026"
        assert show["not_yet_on_sale"] is False  # onsale was 2026-01-01, before now

    def test_future_onsale(self):
        now = datetime(2026, 2, 25, tzinfo=timezone.utc)
        event = self._make_event()
        event["sales"]["public"]["startDateTime"] = "2026-06-01T10:00:00Z"
        show = build_show(event, now)
        assert show is not None
        assert show["not_yet_on_sale"] is True
        assert show["onsale_datetime"] == "2026-06-01T10:00:00Z"
        assert len(show["presales"]) == 0  # No presales in our test event

    def test_filters_non_na(self):
        now = datetime(2026, 2, 25, tzinfo=timezone.utc)
        event = self._make_event()
        event["_embedded"]["venues"][0]["country"]["countryCode"] = "GB"
        show = build_show(event, now)
        assert show is None

    def test_filters_past_events(self):
        now = datetime(2026, 9, 1, tzinfo=timezone.utc)
        event = self._make_event()  # date is 2026-08-15
        show = build_show(event, now)
        assert show is None

    def test_no_venues(self):
        now = datetime(2026, 2, 25, tzinfo=timezone.utc)
        event = self._make_event()
        event["_embedded"]["venues"] = []
        assert build_show(event, now) is None

    def test_canadian_city_format(self):
        now = datetime(2026, 2, 25, tzinfo=timezone.utc)
        event = self._make_event()
        event["_embedded"]["venues"][0]["country"]["countryCode"] = "CA"
        event["_embedded"]["venues"][0]["city"]["name"] = "Toronto"
        event["_embedded"]["venues"][0]["state"]["stateCode"] = "ON"
        show = build_show(event, now)
        assert show is not None
        assert show["city"] == "Toronto, ON, CA"

    def test_onsale_tbd(self):
        now = datetime(2026, 2, 25, tzinfo=timezone.utc)
        event = self._make_event()
        event["sales"]["public"] = {"startTBD": True}
        show = build_show(event, now)
        assert show is not None
        assert show["not_yet_on_sale"] is True
        assert show["onsale_tbd"] is True


# ── detect_triggers tests ────────────────────────────────────────────────────

class TestDetectTriggers:
    def test_new_event_detected(self):
        result = RefreshResult(
            artist_shows={
                "Caamp": [{"date": "Jun 1, 2026", "venue": "Wooly's", "city": "Des Moines, IA"}],
            },
        )
        triggers = detect_triggers(result, old_cache=None)
        assert len(triggers) == 1
        assert triggers[0]["type"] == "new_event"
        assert triggers[0]["artist"] == "Caamp"

    def test_no_trigger_for_existing_event(self):
        old_cache = {
            "artist_shows": {
                "Caamp": [{"date": "Jun 1, 2026", "venue": "Wooly's", "city": "Des Moines, IA"}],
            },
        }
        result = RefreshResult(
            artist_shows={
                "Caamp": [{"date": "Jun 1, 2026", "venue": "Wooly's", "city": "Des Moines, IA"}],
            },
        )
        triggers = detect_triggers(result, old_cache)
        # Only new_event triggers should be absent — on-sale triggers may still fire
        new_event_triggers = [t for t in triggers if t["type"] == "new_event"]
        assert len(new_event_triggers) == 0

    def test_onsale_48_hours(self):
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        onsale_soon = (now + timedelta(hours=24)).isoformat()

        result = RefreshResult(
            artist_shows={
                "Tyler Childers": [{
                    "date": "Aug 15, 2026",
                    "venue": "Kinnick",
                    "city": "Iowa City, IA",
                    "onsale_datetime": onsale_soon,
                }],
            },
        )
        # Use existing old_cache so no new_event trigger
        old_cache = {
            "artist_shows": {
                "Tyler Childers": [{"date": "Aug 15, 2026", "venue": "Kinnick", "city": "Iowa City, IA"}],
            },
        }
        triggers = detect_triggers(result, old_cache)
        onsale_triggers = [t for t in triggers if t["type"] == "onsale_48_hours"]
        assert len(onsale_triggers) == 1

    def test_onsale_7_days(self):
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        onsale_week = (now + timedelta(days=5)).isoformat()

        result = RefreshResult(
            artist_shows={
                "Hozier": [{
                    "date": "Sep 1, 2026",
                    "venue": "Xcel",
                    "city": "St. Paul, MN",
                    "onsale_datetime": onsale_week,
                }],
            },
        )
        old_cache = {
            "artist_shows": {
                "Hozier": [{"date": "Sep 1, 2026", "venue": "Xcel", "city": "St. Paul, MN"}],
            },
        }
        triggers = detect_triggers(result, old_cache)
        onsale_triggers = [t for t in triggers if t["type"] == "onsale_7_days"]
        assert len(onsale_triggers) == 1


# ── RefreshProgress tests ───────────────────────────────────────────────────

class TestRefreshProgress:
    def test_initial_state(self):
        p = RefreshProgress()
        assert p.running is False
        assert p.total_artists == 0
        assert p.error is None

    def test_progress_tracking(self):
        p = RefreshProgress()
        p.running = True
        p.total_artists = 5
        p.artists_processed = 3
        assert p.artists_processed == 3


# ── fetch_artist_shows tests (with mocked API) ──────────────────────────────

class TestFetchArtistShows:
    def test_skips_paused_artists(self):
        artists = {
            "Active": {"paused": False, "genre": "Rock"},
            "Paused": {"paused": True, "genre": "Rock"},
        }
        with patch("backend.ticketmaster._tm_request", return_value={}):
            shows, not_found = fetch_artist_shows("fake-key", artists)
        # Both return empty because of empty API response, but Paused should be skipped
        assert "Paused" not in shows
        assert "Paused" not in not_found

    def test_not_found_on_empty_response(self):
        artists = {"Nobody": {"paused": False, "genre": "Other"}}
        # Return valid response with no events
        with patch("backend.ticketmaster._tm_request", return_value={"_embedded": {"events": []}}):
            shows, not_found = fetch_artist_shows("fake-key", artists)
        assert "Nobody" in not_found
        assert "Nobody" not in shows
