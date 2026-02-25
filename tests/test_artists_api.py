"""Tests for /api/artists CRUD endpoints."""


def test_list_artists_empty(client):
    r = client.get("/api/artists")
    assert r.status_code == 200
    assert r.json() == []


def test_add_artist(client):
    r = client.post("/api/artists", json={
        "name": "Tyler Childers",
        "url": "https://tylerchilders.com/tour",
        "genre": "Country",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Tyler Childers"
    assert data["genre"] == "Country"
    assert data["paused"] is False


def test_add_artist_duplicate(client):
    payload = {"name": "Zach Bryan", "url": "https://zb.com", "genre": "Country"}
    client.post("/api/artists", json=payload)
    r = client.post("/api/artists", json=payload)
    assert r.status_code == 409


def test_list_artists_after_add(client):
    client.post("/api/artists", json={
        "name": "Caamp", "url": "https://caamp.com", "genre": "Indie",
    })
    r = client.get("/api/artists")
    assert r.status_code == 200
    artists = r.json()
    assert len(artists) == 1
    assert artists[0]["name"] == "Caamp"


def test_patch_artist(client):
    client.post("/api/artists", json={
        "name": "Hozier", "url": "https://hozier.com", "genre": "Indie",
    })
    r = client.patch("/api/artists/Hozier", json={"paused": True, "genre": "Alt"})
    assert r.status_code == 200
    data = r.json()
    assert data["paused"] is True
    assert data["genre"] == "Alt"


def test_patch_artist_not_found(client):
    r = client.patch("/api/artists/Nobody", json={"paused": True})
    assert r.status_code == 404


def test_delete_artist(client):
    client.post("/api/artists", json={
        "name": "Waxahatchee", "url": "https://wax.com", "genre": "Indie",
    })
    r = client.delete("/api/artists/Waxahatchee")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Verify gone
    r = client.get("/api/artists")
    assert r.json() == []


def test_delete_artist_not_found(client):
    r = client.delete("/api/artists/Ghost")
    assert r.status_code == 404
