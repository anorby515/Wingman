"""Tests for /api/notifications endpoints."""

import json


def test_notifications_empty(client):
    """GET /api/notifications with no file returns empty triggers."""
    r = client.get("/api/notifications")
    assert r.status_code == 200
    data = r.json()
    assert data["generated_at"] is None
    assert data["triggers"] == []


def test_notifications_with_data(client, monkeypatch):
    """GET /api/notifications returns triggers from notification_state.json."""
    import backend.main as main_mod

    notification_data = {
        "generated_at": "2026-02-25T10:00:00Z",
        "triggers": [
            {
                "type": "new_event",
                "artist": "Tyler Childers",
                "date": "Aug 15, 2026",
                "venue": "Kinnick Stadium",
                "city": "Iowa City, IA",
            },
        ],
    }
    main_mod.NOTIFICATION_FILE.write_text(json.dumps(notification_data))

    r = client.get("/api/notifications")
    assert r.status_code == 200
    data = r.json()
    assert len(data["triggers"]) == 1
    assert data["triggers"][0]["type"] == "new_event"
    assert data["triggers"][0]["artist"] == "Tyler Childers"


def test_clear_notifications(client, monkeypatch):
    """POST /api/notifications/clear removes the file."""
    import backend.main as main_mod

    main_mod.NOTIFICATION_FILE.write_text(json.dumps({
        "generated_at": "2026-02-25T10:00:00Z",
        "triggers": [{"type": "new_event", "artist": "Test"}],
    }))
    assert main_mod.NOTIFICATION_FILE.exists()

    r = client.post("/api/notifications/clear")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert not main_mod.NOTIFICATION_FILE.exists()

    # Subsequent GET returns empty
    r = client.get("/api/notifications")
    assert r.json()["triggers"] == []
