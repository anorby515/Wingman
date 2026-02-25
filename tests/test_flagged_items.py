"""Tests for /api/flagged-items endpoints."""

import json


def test_list_flagged_empty(client):
    r = client.get("/api/flagged-items")
    assert r.status_code == 200
    assert r.json() == []


def test_list_flagged_with_data(client, tmp_path, monkeypatch):
    import backend.main as main_mod

    items = [
        {"artist": "Unknown Band", "reason": "Not found on Spotify", "source": "spotify_sync"},
    ]
    main_mod.FLAGGED_FILE.write_text(json.dumps(items))

    r = client.get("/api/flagged-items")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["artist"] == "Unknown Band"


def test_dismiss_flagged_item(client, tmp_path, monkeypatch):
    import backend.main as main_mod

    items = [
        {"artist": "A", "reason": "test"},
        {"artist": "B", "reason": "test"},
    ]
    main_mod.FLAGGED_FILE.write_text(json.dumps(items))

    r = client.delete("/api/flagged-items/0")
    assert r.status_code == 200
    assert r.json()["removed"]["artist"] == "A"

    # Verify only B remains
    r2 = client.get("/api/flagged-items")
    assert len(r2.json()) == 1
    assert r2.json()[0]["artist"] == "B"


def test_dismiss_flagged_item_out_of_range(client):
    r = client.delete("/api/flagged-items/99")
    assert r.status_code == 404
