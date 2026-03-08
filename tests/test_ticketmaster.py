"""Tests for backend/ticketmaster.py shared module."""

from datetime import datetime, timezone
from unittest.mock import patch

from backend.ticketmaster import (
    RefreshProgress,
    RefreshResult,
    _normalize_festival_name,
    _normalize_venue_name,
    _venue_in_city,
    _venue_in_state,
    build_show,
    detect_triggers,
    fetch_artist_shows,
    fetch_festival_shows,
    fetch_venue_shows,
    festival_name_matches,
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


class TestVenueInState:
    def test_same_state(self):
        tm_venue = {
            "city": {"name": "Waukee"},
            "state": {"stateCode": "IA"},
        }
        assert _venue_in_state(tm_venue, "West Des Moines, IA") is True

    def test_different_state(self):
        tm_venue = {
            "city": {"name": "Chicago"},
            "state": {"stateCode": "IL"},
        }
        assert _venue_in_state(tm_venue, "Des Moines, IA") is False

    def test_empty_target(self):
        tm_venue = {"city": {"name": "Waukee"}, "state": {"stateCode": "IA"}}
        assert _venue_in_state(tm_venue, "") is False

    def test_no_state_in_target(self):
        tm_venue = {"city": {"name": "Waukee"}, "state": {"stateCode": "IA"}}
        assert _venue_in_state(tm_venue, "Waukee") is False


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

    def test_pass4_state_fallback(self):
        """State-based fallback: Vibrant Music Hall in Waukee vs West Des Moines."""
        response = self._make_venue_response([
            {
                "id": "V5",
                "name": "Vibrant Music Hall",
                "city": {"name": "Waukee"},
                "state": {"stateCode": "IA"},
            },
        ])
        with patch("backend.ticketmaster._tm_request", return_value=response):
            # Pass 1 matches by name, so this actually hits pass 1
            result = get_tm_venue_id("key", "Vibrant Music Hall", "West Des Moines, IA")
            assert result == "V5"

    def test_state_fallback_different_name(self):
        """State-based fallback with completely different name."""
        response = self._make_venue_response([
            {
                "id": "V6",
                "name": "Totally Different Name",
                "city": {"name": "Waukee"},
                "state": {"stateCode": "IA"},
            },
        ])
        with patch("backend.ticketmaster._tm_request", return_value=response):
            result = get_tm_venue_id("key", "Some Venue", "West Des Moines, IA")
            assert result == "V6"

    def test_no_match_returns_none(self):
        """No venues returned → None."""
        with patch("backend.ticketmaster._tm_request", return_value={}):
            assert get_tm_venue_id("key", "Nowhere Venue") is None

    def test_city_fallback_wrong_state(self):
        """Should not match a venue in a completely different state."""
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

    def test_sends_state_code_in_api_call(self):
        """When venue_city is provided, stateCode should be in the API URL."""
        with patch("backend.ticketmaster._tm_request", return_value={}) as mock:
            get_tm_venue_id("key", "Test", "Des Moines, IA")
            url = mock.call_args[0][0]
            assert "stateCode=IA" in url


class TestNormalizeFestivalName:
    def test_strips_festival_suffix(self):
        assert _normalize_festival_name("Hinterland Music Festival") == "hinterland"

    def test_strips_fest_suffix(self):
        assert _normalize_festival_name("We Fest") == "we"

    def test_removes_spaces_and_punctuation(self):
        assert _normalize_festival_name("Stage Coach Festival") == "stagecoach"

    def test_plain_name(self):
        assert _normalize_festival_name("Stagecoach") == "stagecoach"

    def test_music_fest_suffix(self):
        assert _normalize_festival_name("Bonnaroo Music Fest") == "bonnaroo"

    def test_no_suffix(self):
        assert _normalize_festival_name("Two Step Inn") == "twostepinn"


class TestFestivalNameMatches:
    def test_exact_match(self):
        assert festival_name_matches("Hinterland Music Festival", "Hinterland Music Festival") is True

    def test_substring_match(self):
        assert festival_name_matches("Hinterland Music Festival", "Hinterland Music Festival 2026") is True

    def test_stagecoach_variation(self):
        """'Stage Coach Festival' should match 'Stagecoach' on TM."""
        assert festival_name_matches("Stage Coach Festival", "Stagecoach") is True

    def test_stagecoach_full_event(self):
        """'Stage Coach Festival' should match 'Stagecoach Music Festival 2026'."""
        assert festival_name_matches("Stage Coach Festival", "Stagecoach Music Festival 2026") is True

    def test_we_fest_match(self):
        assert festival_name_matches("We Fest", "WE Fest 2026") is True

    def test_no_match(self):
        assert festival_name_matches("Bonnaroo", "Coachella") is False

    def test_partial_word_no_false_positive(self):
        """Should not match completely unrelated events."""
        assert festival_name_matches("ACL Fest", "Oracle Cloud Festival") is False


class TestFetchFestivalShows:
    def test_skips_paused_festivals(self):
        festivals = {
            "Active Fest": {"paused": False},
            "Paused Fest": {"paused": True},
        }
        with patch("backend.ticketmaster._tm_request", return_value={}):
            shows, not_found = fetch_festival_shows("fake-key", festivals)
        assert "Paused Fest" not in shows
        assert "Paused Fest" not in not_found

    def test_deduplicates_by_date_venue(self):
        """Multiple TM events on same date+venue should be deduplicated."""
        festivals = {"Test Fest": {"paused": False}}
        # Two events on same date at same venue (e.g. different ticket types)
        response = {
            "_embedded": {
                "events": [
                    {
                        "name": "Test Fest Day 1",
                        "url": "https://tm.com/1",
                        "dates": {"start": {"localDate": "2026-07-15"}},
                        "sales": {"public": {"startDateTime": "2026-01-01T10:00:00Z"}},
                        "_embedded": {
                            "venues": [{
                                "name": "Big Park",
                                "city": {"name": "Austin"},
                                "state": {"stateCode": "TX"},
                                "country": {"countryCode": "US"},
                            }],
                        },
                    },
                    {
                        "name": "Test Fest Day 1 - VIP",
                        "url": "https://tm.com/2",
                        "dates": {"start": {"localDate": "2026-07-15"}},
                        "sales": {"public": {"startDateTime": "2026-01-01T10:00:00Z"}},
                        "_embedded": {
                            "venues": [{
                                "name": "Big Park",
                                "city": {"name": "Austin"},
                                "state": {"stateCode": "TX"},
                                "country": {"countryCode": "US"},
                            }],
                        },
                    },
                ],
            },
        }
        with patch("backend.ticketmaster._tm_request", return_value=response):
            shows, not_found = fetch_festival_shows("fake-key", festivals)
        assert "Test Fest" in shows
        assert len(shows["Test Fest"]) == 1  # Deduplicated


class TestNameMatches:
    def test_exact_match(self):
        assert name_matches("Pearl Jam", ["Pearl Jam"]) is True

    def test_substring_in_attraction(self):
        assert name_matches("Pearl Jam", ["Pearl Jam Live"]) is True

    def test_case_insensitive(self):
        assert name_matches("pearl jam", ["Pearl Jam"]) is True

    def test_rejects_tribute(self):
        assert name_matches("Pearl Jam", ["Pearl Jam Tribute"]) is False

    def test_rejects_tribute_case_insensitive(self):
        assert name_matches("Pearl Jam", ["pearl jam TRIBUTE band"]) is False

    def test_rejects_cover_band(self):
        assert name_matches("Foo Fighters", ["Foo Fighters Cover Band"]) is False

    def test_rejects_salute(self):
        assert name_matches("Led Zeppelin", ["A Salute to Led Zeppelin"]) is False

    def test_does_not_reject_real_artist(self):
        assert name_matches("Caamp", ["Caamp"]) is True

    def test_no_match_returns_false(self):
        assert name_matches("Radiohead", ["Pearl Jam"]) is False


class TestFetchArtistShowsDedup:
    def _make_wrigley_event(self, name: str, url: str) -> dict:
        return {
            "name": name,
            "url": url,
            "dates": {"start": {"localDate": "2026-07-11"}},
            "sales": {"public": {"startDateTime": "2026-01-01T10:00:00Z"}},
            "_embedded": {
                "venues": [{
                    "name": "Wrigley Field",
                    "city": {"name": "Chicago"},
                    "state": {"stateCode": "IL"},
                    "country": {"countryCode": "US"},
                }],
                "attractions": [{"name": "Pearl Jam"}],
            },
        }

    def test_deduplicates_same_date_venue(self):
        """Three TM listings for same Pearl Jam @ Wrigley show deduplicate to one."""
        artists = {"Pearl Jam": {"paused": False, "genre": "Rock"}}
        response = {
            "_embedded": {
                "events": [
                    self._make_wrigley_event("Pearl Jam GA Floor", "https://tm.com/1"),
                    self._make_wrigley_event("Pearl Jam Reserved Seating", "https://tm.com/2"),
                    self._make_wrigley_event("Pearl Jam VIP Package", "https://tm.com/3"),
                ],
            },
        }
        with patch("backend.ticketmaster._tm_request", return_value=response):
            shows, _ = fetch_artist_shows("fake-key", artists)
        assert "Pearl Jam" in shows
        assert len(shows["Pearl Jam"]) == 1

    def test_keeps_different_dates(self):
        """Events on different dates at the same venue should all be kept."""
        artists = {"Pearl Jam": {"paused": False, "genre": "Rock"}}

        def make_event(date: str) -> dict:
            e = self._make_wrigley_event(f"Pearl Jam {date}", "https://tm.com/x")
            e["dates"]["start"]["localDate"] = date
            return e

        response = {
            "_embedded": {
                "events": [
                    make_event("2026-07-11"),
                    make_event("2026-07-12"),
                    make_event("2026-07-13"),
                ],
            },
        }
        with patch("backend.ticketmaster._tm_request", return_value=response):
            shows, _ = fetch_artist_shows("fake-key", artists)
        assert "Pearl Jam" in shows
        assert len(shows["Pearl Jam"]) == 3

    def test_uses_attraction_id_when_present(self):
        """When tm_attraction_id is set, API call uses attractionId param."""
        artists = {"Pearl Jam": {"paused": False, "genre": "Rock", "tm_attraction_id": "K8vZ917Hfn0"}}
        with patch("backend.ticketmaster._tm_request", return_value={}) as mock_req:
            fetch_artist_shows("fake-key", artists)
        url = mock_req.call_args[0][0]
        assert "attractionId=K8vZ917Hfn0" in url
        assert "keyword=" not in url

    def test_uses_keyword_when_no_attraction_id(self):
        """Without tm_attraction_id, API call uses keyword param."""
        artists = {"Pearl Jam": {"paused": False, "genre": "Rock"}}
        with patch("backend.ticketmaster._tm_request", return_value={}) as mock_req:
            fetch_artist_shows("fake-key", artists)
        url = mock_req.call_args[0][0]
        assert "keyword=" in url
        assert "attractionId=" not in url


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
