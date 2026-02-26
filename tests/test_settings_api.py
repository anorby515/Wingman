"""Tests for /api/config and /api/settings endpoints."""

import json


def test_get_config(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert data["center_city"] == "Des Moines, IA"
    assert "artists" in data
    assert "venues" in data
    assert "festivals" in data


def test_patch_settings_center_city(client):
    r = client.patch("/api/settings", json={"center_city": "Chicago, IL"})
    assert r.status_code == 200
    assert r.json()["settings"]["center_city"] == "Chicago, IL"

    # Verify persisted
    r2 = client.get("/api/config")
    assert r2.json()["center_city"] == "Chicago, IL"


def test_patch_settings_ticketmaster_key(client, tmp_path):
    r = client.patch("/api/settings", json={"ticketmaster_api_key": "test-key-123"})
    assert r.status_code == 200
    assert r.json()["settings"]["ticketmaster_api_key"] == "test-key-123"


def test_patch_settings_github_pages_url(client):
    r = client.patch("/api/settings", json={"github_pages_url": "https://example.github.io/Wingman/"})
    assert r.status_code == 200
    assert r.json()["settings"]["github_pages_url"] == "https://example.github.io/Wingman/"
