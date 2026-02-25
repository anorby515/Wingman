"""Tests for background geocoding and GET /api/geocode/progress endpoint."""

import json


def test_geocode_progress_empty(client):
    """Without a geocode cache, returns zero counts and not running."""
    r = client.get("/api/geocode/progress")
    assert r.status_code == 200
    data = r.json()
    assert data["running"] is False
    assert data["total"] == 0
    assert data["done"] == 0
    assert data["total_cached"] == 0


def test_geocode_progress_with_cache(client, monkeypatch):
    """With an existing geocode cache, returns correct total_cached count."""
    import backend.main as main_mod

    cache = {
        "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
        "Chicago, IL": {"lat": 41.8781, "lon": -87.6298},
    }
    main_mod.GEOCODE_FILE.write_text(json.dumps(cache))

    r = client.get("/api/geocode/progress")
    data = r.json()
    assert data["total_cached"] == 2
    assert data["running"] is False


def test_geocode_progress_reflects_running_state(client, monkeypatch):
    """When background geocoding is running, the endpoint reports it."""
    import backend.main as main_mod

    monkeypatch.setattr(main_mod, "_geocode_running", True)
    monkeypatch.setattr(main_mod, "_geocode_total", 5)
    monkeypatch.setattr(main_mod, "_geocode_done", 2)

    r = client.get("/api/geocode/progress")
    data = r.json()
    assert data["running"] is True
    assert data["total"] == 5
    assert data["done"] == 2


def test_collect_ungeocodable_locations(client, monkeypatch):
    """_collect_ungeocodable_locations returns locations for shows missing lat/lon."""
    import backend.main as main_mod

    cache = {
        "last_refreshed": "2026-02-25T10:00:00Z",
        "artist_shows": {
            "Test Artist": [
                {"venue": "Venue A", "city": "City A, IA", "lat": None, "lon": None},
                {"venue": "Venue B", "city": "City B, IA", "lat": 41.0, "lon": -93.0},
            ],
        },
        "venue_shows": {},
        "festival_shows": {},
        "artists_not_found": [],
        "venues_not_found": [],
        "festivals_not_found": [],
    }
    main_mod.TM_CACHE_FILE.write_text(json.dumps(cache))

    locations = main_mod._collect_ungeocodable_locations()
    assert "Venue A, City A, IA" in locations
    assert "City A, IA" in locations
    # Venue B has coords, should not appear
    assert "Venue B, City B, IA" not in locations


def test_collect_ungeocodable_no_cache(client, monkeypatch):
    """Without a cache file, returns empty list."""
    import backend.main as main_mod

    locations = main_mod._collect_ungeocodable_locations()
    assert locations == []


def test_apply_geocodes_to_cache(client, monkeypatch):
    """_apply_geocodes_to_cache fills in lat/lon from geocode cache."""
    import backend.main as main_mod

    # Set up TM cache with missing coords
    tm_cache = {
        "last_refreshed": "2026-02-25T10:00:00Z",
        "artist_shows": {
            "Test Artist": [
                {"venue": "Kinnick Stadium", "city": "Iowa City, IA",
                 "lat": None, "lon": None, "date": "Aug 15, 2026"},
            ],
        },
        "venue_shows": {},
        "festival_shows": {},
    }
    main_mod.TM_CACHE_FILE.write_text(json.dumps(tm_cache))

    # Set up geocode cache with the venue+city match
    geocode = {
        "Kinnick Stadium, Iowa City, IA": {"lat": 41.66, "lon": -91.53},
    }
    main_mod.GEOCODE_FILE.write_text(json.dumps(geocode))

    # Apply geocodes
    main_mod._apply_geocodes_to_cache()

    # Verify TM cache was updated
    updated = json.loads(main_mod.TM_CACHE_FILE.read_text())
    show = updated["artist_shows"]["Test Artist"][0]
    assert show["lat"] == 41.66
    assert show["lon"] == -91.53


def test_apply_geocodes_city_fallback(client, monkeypatch):
    """_apply_geocodes_to_cache falls back to city-only geocode match."""
    import backend.main as main_mod

    tm_cache = {
        "last_refreshed": "2026-02-25T10:00:00Z",
        "artist_shows": {
            "Test Artist": [
                {"venue": "Unknown Venue", "city": "Des Moines, IA",
                 "lat": None, "lon": None, "date": "Sep 1, 2026"},
            ],
        },
        "venue_shows": {},
        "festival_shows": {},
    }
    main_mod.TM_CACHE_FILE.write_text(json.dumps(tm_cache))

    # Only city is in geocode cache, not venue+city
    geocode = {
        "Des Moines, IA": {"lat": 41.5868, "lon": -93.625},
    }
    main_mod.GEOCODE_FILE.write_text(json.dumps(geocode))

    main_mod._apply_geocodes_to_cache()

    updated = json.loads(main_mod.TM_CACHE_FILE.read_text())
    show = updated["artist_shows"]["Test Artist"][0]
    assert show["lat"] == 41.5868
    assert show["lon"] == -93.625


def test_apply_geocodes_skips_already_geocoded(client, monkeypatch):
    """Shows that already have lat/lon are not modified."""
    import backend.main as main_mod

    tm_cache = {
        "last_refreshed": "2026-02-25T10:00:00Z",
        "artist_shows": {
            "Test Artist": [
                {"venue": "Kinnick Stadium", "city": "Iowa City, IA",
                 "lat": 99.0, "lon": -99.0, "date": "Aug 15, 2026"},
            ],
        },
        "venue_shows": {},
        "festival_shows": {},
    }
    main_mod.TM_CACHE_FILE.write_text(json.dumps(tm_cache))

    geocode = {
        "Kinnick Stadium, Iowa City, IA": {"lat": 41.66, "lon": -91.53},
    }
    main_mod.GEOCODE_FILE.write_text(json.dumps(geocode))

    main_mod._apply_geocodes_to_cache()

    updated = json.loads(main_mod.TM_CACHE_FILE.read_text())
    show = updated["artist_shows"]["Test Artist"][0]
    # Should keep original coords, not overwrite
    assert show["lat"] == 99.0
    assert show["lon"] == -99.0
