"""Tests for /api/venues CRUD endpoints."""


def test_list_venues_empty(client):
    r = client.get("/api/venues")
    assert r.status_code == 200
    assert r.json() == []


def test_add_venue(client):
    r = client.post("/api/venues", json={
        "name": "Wells Fargo Arena",
        "url": "https://wfa.com",
        "city": "Des Moines, IA",
        "is_local": True,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Wells Fargo Arena"
    assert data["city"] == "Des Moines, IA"
    assert data["is_local"] is True
    assert data["paused"] is False


def test_add_venue_duplicate(client):
    payload = {"name": "Val Air", "url": "https://valair.com", "city": "Des Moines, IA"}
    client.post("/api/venues", json=payload)
    r = client.post("/api/venues", json=payload)
    assert r.status_code == 409


def test_patch_venue(client):
    client.post("/api/venues", json={
        "name": "Kinnick Stadium",
        "url": "https://kinnick.com",
        "city": "Iowa City, IA",
    })
    r = client.patch("/api/venues/Kinnick Stadium", json={
        "paused": True, "is_local": False,
    })
    assert r.status_code == 200
    assert r.json()["paused"] is True
    assert r.json()["is_local"] is False


def test_patch_venue_not_found(client):
    r = client.patch("/api/venues/NoPlace", json={"paused": True})
    assert r.status_code == 404


def test_delete_venue(client):
    client.post("/api/venues", json={
        "name": "Wooly's", "url": "https://woolys.com", "city": "Des Moines, IA",
    })
    r = client.delete("/api/venues/Wooly's")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.get("/api/venues")
    assert r.json() == []


def test_delete_venue_not_found(client):
    r = client.delete("/api/venues/Nowhere")
    assert r.status_code == 404
