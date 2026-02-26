"""Tests for backend/ticketmaster.py shared module."""

from datetime import datetime, timezone
from unittest.mock import patch

from backend.ticketmaster import (
    RefreshProgress,
    RefreshResult,
    _normalize_venue_name,
    _venue_in_city,
    build_show,
    detect_triggers,
    fetch_artist_shows,
    fetch_venue_shows,
    get_tm_venue_id,
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


# ── Venue ID lookup tests ────────────────────────────────────────────────────

class TestNormalizeVenueName:
    def test_strips_apostrophe(self):
        assert _normalize_venue_name("Wooly's") == "woolys"

    def test_strips_parentheses(self):
        assert _normalize_venue_name("The Salt Shed Indoors (Shed)") == "the salt shed indoors shed"

    def test_lowercase(self):
        assert _normalize_venue_name("Red Rocks") == "red rocks"

    def test_empty(self):
        assert _normalize_venue_name("") == ""


class TestVenueInCity:
    def test_match_us_city(self):
        tm_venue = {
            "city": {"name": "Des Moines"},
            "state": {"stateCode": "IA"},
        }
        assert _venue_in_city(tm_venue, "Des Moines, IA") is True

    def test_case_insensitive(self):
        tm_venue = {
            "city": {"name": "Austin"},
            "state": {"stateCode": "TX"},
        }
        assert _venue_in_city(tm_venue, "Austin, Tx") is True

    def test_wrong_city(self):
        tm_venue = {
            "city": {"name": "Chicago"},
            "state": {"stateCode": "IL"},
        }
        assert _venue_in_city(tm_venue, "Des Moines, IA") is False

    def test_empty_target(self):
        tm_venue = {"city": {"name": "Chicago"}, "state": {"stateCode": "IL"}}
        assert _venue_in_city(tm_venue, "") is False


class TestGetTmVenueId:
    def _make_venue_response(self, venues):
        """Build a TM venues.json API response."""
        return {"_embedded": {"venues": venues}}

    def test_pass1_substring_match(self):
        """Direct substring match should work (existing behaviour)."""
        response = self._make_venue_response([
            {"id": "V1", "name": "Red Rocks Amphitheatre"},
        ])
        with patch("backend.ticketmaster._tm_request", return_value=response):
            assert get_tm_venue_id("key", "Red Rocks") == "V1"

    def test_pass2_normalized_match(self):
        """Punctuation-stripped matching: Wooly's → Woolys."""
        response = self._make_venue_response([
            {"id": "V2", "name": "Woolys"},
        ])
        with patch("backend.ticketmaster._tm_request", return_value=response):
            # "Wooly's" normalises to "woolys", matching "Woolys" → "woolys"
            assert get_tm_venue_id("key", "Wooly's") == "V2"

    def test_pass3_city_fallback(self):
        """City-based fallback when name doesn't match at all."""
        response = self._make_venue_response([
            {
                "id": "V3",
                "name": "ACL Live",
                "city": {"name": "Austin"},
                "state": {"stateCode": "TX"},
            },
        ])
        with patch("backend.ticketmaster._tm_request", return_value=response):
            result = get_tm_venue_id(
                "key", "Austin City Limits Live at The Moody", "Austin, TX",
            )
            assert result == "V3"

    def test_no_match_returns_none(self):
        """No venues returned → None."""
        with patch("backend.ticketmaster._tm_request", return_value={}):
            assert get_tm_venue_id("key", "Nowhere Venue") is None

    def test_city_fallback_wrong_city(self):
        """City fallback shouldn't match a venue in a different city."""
        response = self._make_venue_response([
            {
                "id": "V4",
                "name": "Some Other Place",
                "city": {"name": "Chicago"},
                "state": {"stateCode": "IL"},
            },
        ])
        with patch("backend.ticketmaster._tm_request", return_value=response):
            result = get_tm_venue_id("key", "Test Venue", "Des Moines, IA")
            assert result is None


class TestFetchVenueShows:
    def test_skips_paused_venues(self):
        venues = {
            "Active": {"paused": False, "city": "Des Moines, IA"},
            "Paused": {"paused": True, "city": "Des Moines, IA"},
        }
        with patch("backend.ticketmaster._tm_request", return_value={}):
            shows, not_found = fetch_venue_shows("fake-key", venues)
        assert "Paused" not in shows
        assert "Paused" not in not_found

    def test_venue_not_found(self):
        venues = {"Unknown Venue": {"paused": False, "city": "Nowhere, XX"}}
        with patch("backend.ticketmaster._tm_request", return_value={}):
            shows, not_found = fetch_venue_shows("fake-key", venues)
        assert "Unknown Venue" in not_found
        assert "Unknown Venue" not in shows
