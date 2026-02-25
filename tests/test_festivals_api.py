"""Tests for /api/festivals CRUD endpoints."""


def test_list_festivals_empty(client):
    r = client.get("/api/festivals")
    assert r.status_code == 200
    assert r.json() == []


def test_add_festival(client):
    r = client.post("/api/festivals", json={
        "name": "Hinterland",
        "url": "https://hinterland.com",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Hinterland"
    assert data["paused"] is False


def test_add_festival_duplicate(client):
    payload = {"name": "Bonnaroo", "url": "https://bonnaroo.com"}
    client.post("/api/festivals", json=payload)
    r = client.post("/api/festivals", json=payload)
    assert r.status_code == 409


def test_patch_festival(client):
    client.post("/api/festivals", json={
        "name": "Hinterland", "url": "https://hinterland.com",
    })
    r = client.patch("/api/festivals/Hinterland", json={"paused": True})
    assert r.status_code == 200
    assert r.json()["paused"] is True


def test_patch_festival_not_found(client):
    r = client.patch("/api/festivals/NoFest", json={"paused": True})
    assert r.status_code == 404


def test_delete_festival(client):
    client.post("/api/festivals", json={
        "name": "Lollapalooza", "url": "https://lolla.com",
    })
    r = client.delete("/api/festivals/Lollapalooza")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.get("/api/festivals")
    assert r.json() == []


def test_delete_festival_not_found(client):
    r = client.delete("/api/festivals/Ghost")
    assert r.status_code == 404
