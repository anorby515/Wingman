"""Tests for GET /api/shows endpoint (cache-only, never calls TM API)."""

import json


def test_shows_no_cache(client):
    """Without a cache file, returns empty structure with stale=True."""
    r = client.get("/api/shows")
    assert r.status_code == 200
    data = r.json()
    assert data["stale"] is True
    assert data["last_refreshed"] is None
    assert data["artist_shows"] == {}
    assert data["venue_shows"] == {}
    assert data["festival_shows"] == {}
    assert data["coming_soon"] == []
    assert data["artists_not_found"] == []


def test_shows_with_cache(client, monkeypatch):
    """With a cache file, returns the cached data."""
    import backend.main as main_mod

    cache = {
        "last_refreshed": "2026-02-25T10:00:00Z",
        "artist_shows": {
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
                    "lat": 41.66,
                    "lon": -91.53,
                    "genre": "Country",
                },
            ],
        },
        "venue_shows": {},
        "festival_shows": {},
        "artists_not_found": ["Ghost Band"],
        "venues_not_found": [],
        "festivals_not_found": [],
    }
    main_mod.TM_CACHE_FILE.write_text(json.dumps(cache))

    r = client.get("/api/shows")
    assert r.status_code == 200
    data = r.json()
    assert data["stale"] is False
    assert data["last_refreshed"] == "2026-02-25T10:00:00Z"
    assert "Tyler Childers" in data["artist_shows"]
    assert len(data["artist_shows"]["Tyler Childers"]) == 1
    assert data["artists_not_found"] == ["Ghost Band"]
    assert data["coming_soon"] == []  # No not_yet_on_sale shows


def test_shows_coming_soon_filter(client, monkeypatch):
    """Coming soon list should include only not-yet-on-sale shows."""
    import backend.main as main_mod

    cache = {
        "last_refreshed": "2026-02-25T10:00:00Z",
        "artist_shows": {
            "Zach Bryan": [
                {
                    "date": "Jun 20, 2026",
                    "raw_date": "2026-06-20",
                    "venue": "Wells Fargo Arena",
                    "city": "Des Moines, IA",
                    "not_yet_on_sale": True,
                    "onsale_datetime": "2026-03-01T10:00:00Z",
                    "onsale_tbd": False,
                    "presales": [{"name": "Fan Club", "start_datetime": "2026-02-28T10:00:00Z", "end_datetime": None}],
                    "ticketmaster_url": "https://tm.com/2",
                    "lat": None,
                    "lon": None,
                    "genre": "Country",
                },
                {
                    "date": "Jul 10, 2026",
                    "raw_date": "2026-07-10",
                    "venue": "Red Rocks",
                    "city": "Morrison, CO",
                    "not_yet_on_sale": False,
                    "onsale_datetime": None,
                    "onsale_tbd": False,
                    "presales": [],
                    "ticketmaster_url": "https://tm.com/3",
                    "lat": None,
                    "lon": None,
                    "genre": "Country",
                },
            ],
        },
        "venue_shows": {},
        "festival_shows": {},
        "artists_not_found": [],
        "venues_not_found": [],
        "festivals_not_found": [],
    }
    main_mod.TM_CACHE_FILE.write_text(json.dumps(cache))

    r = client.get("/api/shows")
    data = r.json()
    assert len(data["coming_soon"]) == 1
    assert data["coming_soon"][0]["venue"] == "Wells Fargo Arena"
    assert data["coming_soon"][0]["artist"] == "Zach Bryan"


def test_shows_api_not_configured(client, monkeypatch):
    """Without a TM API key, api_configured should be False."""
    r = client.get("/api/shows")
    assert r.status_code == 200
    assert r.json()["api_configured"] is False


def test_shows_api_configured(client, monkeypatch):
    """With a TM API key, api_configured should be True."""
    import backend.main as main_mod

    cfg = json.loads(main_mod.CONFIG_FILE.read_text())
    cfg["ticketmaster_api_key"] = "test-key"
    main_mod.CONFIG_FILE.write_text(json.dumps(cfg))

    r = client.get("/api/shows")
    assert r.status_code == 200
    assert r.json()["api_configured"] is True
