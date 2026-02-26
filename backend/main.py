#!/usr/bin/env python3
"""
Wingman PWA Backend
===================
FastAPI server that manages wingman_config.json (artists, venues, festivals,
settings).  Serves the built React frontend from ../frontend/dist when present.

Start:  uvicorn backend.main:app --reload --port 8000
  (run from the repo root: /home/user/Wingman)
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Paths ────────────────────────────────────────────────────────────────────
HERE               = Path(__file__).parent
REPO               = HERE.parent
CONFIG_FILE        = REPO / "wingman_config.json"
TRACKED_FILE       = REPO / "tracked.json"
FLAGGED_FILE       = REPO / "flagged_items.json"
GEOCODE_FILE       = REPO / "geocode_cache.json"

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Wingman API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Config helpers ───────────────────────────────────────────────────────────
def _read_config() -> dict:
    if not CONFIG_FILE.exists():
        raise HTTPException(status_code=404, detail="wingman_config.json not found")
    return json.loads(CONFIG_FILE.read_text())


def _write_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    _write_tracked(cfg)


def _write_tracked(cfg: dict) -> None:
    """Write tracked.json — a sanitized subset of wingman_config.json
    containing only entity tracking data (no API keys or credentials).
    This file is committed to git so the GitHub Action can read it."""
    tracked = {
        "center_city": cfg.get("center_city", ""),
        "artists": {},
        "venues": {},
        "festivals": {},
    }
    for name, info in cfg.get("artists", {}).items():
        tracked["artists"][name] = {
            "url": info.get("url", ""),
            "genre": info.get("genre", "Other"),
            "paused": info.get("paused", False),
        }
    for name, info in cfg.get("venues", {}).items():
        tracked["venues"][name] = {
            "url": info.get("url", ""),
            "city": info.get("city", ""),
            "is_local": info.get("is_local", False),
            "paused": info.get("paused", False),
        }
    for name, info in cfg.get("festivals", {}).items():
        tracked["festivals"][name] = {
            "url": info.get("url", ""),
            "paused": info.get("paused", False),
        }
    TRACKED_FILE.write_text(json.dumps(tracked, indent=2) + "\n")


# ── Geocoding helper ────────────────────────────────────────────────────────
_last_geocode_call: float = 0.0


def _geocode(location: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a location string, using cache or Nominatim."""
    global _last_geocode_call

    # Check cache first
    cache: dict = {}
    if GEOCODE_FILE.exists():
        try:
            cache = json.loads(GEOCODE_FILE.read_text())
        except Exception:
            pass
    if location in cache:
        entry = cache[location]
        return entry["lat"], entry["lon"]

    # Rate-limit: 1 req/sec
    elapsed = time.time() - _last_geocode_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={urllib.parse.quote(location)}&format=json&limit=1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Wingman/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        _last_geocode_call = time.time()
    except Exception:
        return None

    if not data:
        return None

    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
    cache[location] = {"lat": lat, "lon": lon}
    try:
        GEOCODE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception:
        pass
    return lat, lon


# ── Pydantic models ─────────────────────────────────────────────────────────
class ArtistIn(BaseModel):
    name: str
    url: str
    genre: str = "Other"


class ArtistPatch(BaseModel):
    paused: Optional[bool] = None
    url: Optional[str] = None
    genre: Optional[str] = None


class VenueIn(BaseModel):
    name: str
    url: str
    city: str
    is_local: bool = False


class VenuePatch(BaseModel):
    paused: Optional[bool] = None
    url: Optional[str] = None
    city: Optional[str] = None
    is_local: Optional[bool] = None


class FestivalIn(BaseModel):
    name: str
    url: str


class FestivalPatch(BaseModel):
    paused: Optional[bool] = None
    url: Optional[str] = None


class SettingsPatch(BaseModel):
    center_city: Optional[str] = None
    radius_miles: Optional[int] = None
    cities_in_range: Optional[list[str]] = None
    states_in_range: Optional[list[str]] = None
    github_pages_url: Optional[str] = None
    ticketmaster_api_key: Optional[str] = None


# ── Config endpoint ──────────────────────────────────────────────────────────
@app.get("/api/config")
def get_config() -> Any:
    cfg = _read_config()
    # Attach geocoded center coordinates for the map
    center_city = cfg.get("center_city", "")
    if center_city and "center_lat" not in cfg:
        coords = _geocode(center_city)
        if coords:
            cfg["center_lat"], cfg["center_lon"] = coords
    # Attach geocoded lat/lon to each venue for map rendering
    for name, venue in cfg.get("venues", {}).items():
        if "lat" not in venue and venue.get("city"):
            coords = _geocode(venue["city"])
            if coords:
                venue["lat"], venue["lon"] = coords
    return cfg


# ── Settings ─────────────────────────────────────────────────────────────────
@app.patch("/api/settings")
def patch_settings(body: SettingsPatch) -> Any:
    cfg = _read_config()
    if body.center_city is not None:
        cfg["center_city"] = body.center_city
    if body.radius_miles is not None:
        cfg["radius_miles"] = body.radius_miles
    if body.cities_in_range is not None:
        cfg["cities_in_range"] = body.cities_in_range
    if body.states_in_range is not None:
        cfg["states_in_range"] = body.states_in_range
    if body.github_pages_url is not None:
        cfg["github_pages_url"] = body.github_pages_url
    if body.ticketmaster_api_key is not None:
        cfg["ticketmaster_api_key"] = body.ticketmaster_api_key or None
    _write_config(cfg)
    return {"ok": True, "settings": {
        "center_city": cfg["center_city"],
        "radius_miles": cfg["radius_miles"],
        "cities_in_range": cfg["cities_in_range"],
        "states_in_range": cfg["states_in_range"],
        "github_pages_url": cfg.get("github_pages_url", ""),
        "ticketmaster_api_key": cfg.get("ticketmaster_api_key") or "",
    }}


# ── Artists ──────────────────────────────────────────────────────────────────
@app.get("/api/artists")
def list_artists() -> Any:
    cfg = _read_config()
    return [
        {"name": name, **info}
        for name, info in cfg.get("artists", {}).items()
    ]


@app.post("/api/artists", status_code=201)
def add_artist(body: ArtistIn) -> Any:
    cfg = _read_config()
    if body.name in cfg.get("artists", {}):
        raise HTTPException(status_code=409, detail=f"Artist '{body.name}' already exists")
    cfg.setdefault("artists", {})[body.name] = {
        "url": body.url,
        "genre": body.genre,
        "paused": False,
    }
    _write_config(cfg)
    return {"name": body.name, "url": body.url, "genre": body.genre, "paused": False}


@app.delete("/api/artists/{name}")
def delete_artist(name: str) -> Any:
    cfg = _read_config()
    if name not in cfg.get("artists", {}):
        raise HTTPException(status_code=404, detail=f"Artist '{name}' not found")
    del cfg["artists"][name]
    _write_config(cfg)
    return {"ok": True}


@app.patch("/api/artists/{name}")
def patch_artist(name: str, body: ArtistPatch) -> Any:
    cfg = _read_config()
    if name not in cfg.get("artists", {}):
        raise HTTPException(status_code=404, detail=f"Artist '{name}' not found")
    info = cfg["artists"][name]
    if body.paused is not None:
        info["paused"] = body.paused
    if body.url is not None:
        info["url"] = body.url
    if body.genre is not None:
        info["genre"] = body.genre
    _write_config(cfg)
    return {"name": name, **info}


# ── Venues ───────────────────────────────────────────────────────────────────
@app.get("/api/venues")
def list_venues() -> Any:
    cfg = _read_config()
    return [
        {"name": name, **info}
        for name, info in cfg.get("venues", {}).items()
    ]


@app.post("/api/venues", status_code=201)
def add_venue(body: VenueIn) -> Any:
    cfg = _read_config()
    if body.name in cfg.get("venues", {}):
        raise HTTPException(status_code=409, detail=f"Venue '{body.name}' already exists")
    cfg.setdefault("venues", {})[body.name] = {
        "url": body.url,
        "city": body.city,
        "is_local": body.is_local,
        "paused": False,
    }
    _write_config(cfg)
    return {"name": body.name, "url": body.url, "city": body.city,
            "is_local": body.is_local, "paused": False}


@app.delete("/api/venues/{name}")
def delete_venue(name: str) -> Any:
    cfg = _read_config()
    if name not in cfg.get("venues", {}):
        raise HTTPException(status_code=404, detail=f"Venue '{name}' not found")
    del cfg["venues"][name]
    _write_config(cfg)
    return {"ok": True}


@app.patch("/api/venues/{name}")
def patch_venue(name: str, body: VenuePatch) -> Any:
    cfg = _read_config()
    if name not in cfg.get("venues", {}):
        raise HTTPException(status_code=404, detail=f"Venue '{name}' not found")
    info = cfg["venues"][name]
    if body.paused is not None:
        info["paused"] = body.paused
    if body.url is not None:
        info["url"] = body.url
    if body.city is not None:
        info["city"] = body.city
    if body.is_local is not None:
        info["is_local"] = body.is_local
    _write_config(cfg)
    return {"name": name, **info}


# ── Festivals ────────────────────────────────────────────────────────────────
@app.get("/api/festivals")
def list_festivals() -> Any:
    cfg = _read_config()
    return [
        {"name": name, **info}
        for name, info in cfg.get("festivals", {}).items()
    ]


@app.post("/api/festivals", status_code=201)
def add_festival(body: FestivalIn) -> Any:
    cfg = _read_config()
    if body.name in cfg.get("festivals", {}):
        raise HTTPException(status_code=409, detail=f"Festival '{body.name}' already exists")
    cfg.setdefault("festivals", {})[body.name] = {
        "url": body.url,
        "paused": False,
    }
    _write_config(cfg)
    return {"name": body.name, "url": body.url, "paused": False}


@app.delete("/api/festivals/{name}")
def delete_festival(name: str) -> Any:
    cfg = _read_config()
    if name not in cfg.get("festivals", {}):
        raise HTTPException(status_code=404, detail=f"Festival '{name}' not found")
    del cfg["festivals"][name]
    _write_config(cfg)
    return {"ok": True}


@app.patch("/api/festivals/{name}")
def patch_festival(name: str, body: FestivalPatch) -> Any:
    cfg = _read_config()
    if name not in cfg.get("festivals", {}):
        raise HTTPException(status_code=404, detail=f"Festival '{name}' not found")
    info = cfg["festivals"][name]
    if body.paused is not None:
        info["paused"] = body.paused
    if body.url is not None:
        info["url"] = body.url
    _write_config(cfg)
    return {"name": name, **info}


# ── Flagged Items ────────────────────────────────────────────────────────────
def _read_flagged() -> list[dict]:
    if not FLAGGED_FILE.exists():
        return []
    try:
        return json.loads(FLAGGED_FILE.read_text())
    except Exception:
        return []


def _write_flagged(items: list[dict]) -> None:
    FLAGGED_FILE.write_text(json.dumps(items, indent=2))


@app.get("/api/flagged-items")
def list_flagged_items() -> Any:
    return _read_flagged()


@app.delete("/api/flagged-items/{index}")
def dismiss_flagged_item(index: int) -> Any:
    items = _read_flagged()
    if index < 0 or index >= len(items):
        raise HTTPException(status_code=404, detail="Flagged item not found")
    removed = items.pop(index)
    _write_flagged(items)
    return {"ok": True, "removed": removed}


# ── Serve built frontend ────────────────────────────────────────────────────
_dist = REPO / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
