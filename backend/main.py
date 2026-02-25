#!/usr/bin/env python3
"""
Wingman PWA Backend
===================
FastAPI server that manages wingman_config.json, serves TM show data from
cache, and triggers data refreshes.  Serves the built React frontend from
../frontend/dist when present.

Start:  uvicorn backend.main:app --reload --port 8000
  (run from the repo root: /home/user/Wingman)
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .ticketmaster import (
    RefreshProgress,
    RefreshResult,
    detect_triggers,
    run_full_refresh,
)

# ── Paths ────────────────────────────────────────────────────────────────────
HERE               = Path(__file__).parent
REPO               = HERE.parent
CONFIG_FILE        = REPO / "wingman_config.json"
FLAGGED_FILE       = REPO / "flagged_items.json"
GEOCODE_FILE       = REPO / "geocode_cache.json"
TM_CACHE_FILE      = REPO / "ticketmaster_cache.json"
NOTIFICATION_FILE  = REPO / "notification_state.json"

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Wingman API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Refresh state ────────────────────────────────────────────────────────────
_refresh_progress: RefreshProgress = RefreshProgress()

# ── Geocode background state ────────────────────────────────────────────────
_geocode_running: bool = False
_geocode_total: int = 0
_geocode_done: int = 0


# ── Config helpers ───────────────────────────────────────────────────────────
def _read_config() -> dict:
    if not CONFIG_FILE.exists():
        raise HTTPException(status_code=404, detail="wingman_config.json not found")
    return json.loads(CONFIG_FILE.read_text())


def _write_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


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


# ── Background geocoding ─────────────────────────────────────────────────────
def _collect_ungeocodable_locations() -> list[str]:
    """Scan TM cache for shows missing lat/lon and return unique location strings."""
    if not TM_CACHE_FILE.exists():
        return []
    try:
        cache = json.loads(TM_CACHE_FILE.read_text())
    except Exception:
        return []

    seen: set[str] = set()
    locations: list[str] = []

    for section in ("artist_shows", "venue_shows", "festival_shows"):
        for _entity, shows in cache.get(section, {}).items():
            for show in shows:
                if show.get("lat") is not None and show.get("lon") is not None:
                    continue
                loc = f"{show.get('venue', '')}, {show.get('city', '')}"
                if loc not in seen:
                    seen.add(loc)
                    locations.append(loc)
                # Also try city-only as fallback key
                city = show.get("city", "")
                if city and city not in seen:
                    seen.add(city)
                    locations.append(city)

    return locations


def _apply_geocodes_to_cache() -> None:
    """Re-read TM cache and fill in lat/lon from geocode cache for any shows still missing coords."""
    if not TM_CACHE_FILE.exists():
        return

    try:
        cache = json.loads(TM_CACHE_FILE.read_text())
    except Exception:
        return

    geocode_data: dict = {}
    if GEOCODE_FILE.exists():
        try:
            geocode_data = json.loads(GEOCODE_FILE.read_text())
        except Exception:
            pass

    updated = False
    for section in ("artist_shows", "venue_shows", "festival_shows"):
        for _entity, shows in cache.get(section, {}).items():
            for show in shows:
                if show.get("lat") is not None and show.get("lon") is not None:
                    continue
                loc = f"{show.get('venue', '')}, {show.get('city', '')}"
                entry = geocode_data.get(loc)
                if not entry:
                    entry = geocode_data.get(show.get("city", ""))
                if entry:
                    show["lat"] = entry["lat"]
                    show["lon"] = entry["lon"]
                    updated = True

    if updated:
        TM_CACHE_FILE.write_text(json.dumps(cache, indent=2))


async def _background_geocode() -> None:
    """Geocode uncached venue locations in the background after a refresh."""
    global _geocode_running, _geocode_total, _geocode_done

    locations = _collect_ungeocodable_locations()
    if not locations:
        return

    _geocode_running = True
    _geocode_total = len(locations)
    _geocode_done = 0

    try:
        for loc in locations:
            await asyncio.to_thread(_geocode, loc)
            _geocode_done += 1
        # Apply newly geocoded data back to the TM cache
        _apply_geocodes_to_cache()
    except Exception:
        pass
    finally:
        _geocode_running = False


# ── Shows endpoint (cache-only, never calls TM API) ─────────────────────────
@app.get("/api/shows")
def get_shows() -> Any:
    """Return ALL event data from TM cache.  NEVER calls the TM API."""
    cfg = _read_config()
    api_configured = bool(cfg.get("ticketmaster_api_key"))

    if not TM_CACHE_FILE.exists():
        return {
            "api_configured": api_configured,
            "artist_shows": {},
            "venue_shows": {},
            "festival_shows": {},
            "coming_soon": [],
            "artists_not_found": [],
            "venues_not_found": [],
            "festivals_not_found": [],
            "last_refreshed": None,
            "stale": True,
        }

    try:
        cache = json.loads(TM_CACHE_FILE.read_text())
    except Exception:
        return {
            "api_configured": api_configured,
            "artist_shows": {},
            "venue_shows": {},
            "festival_shows": {},
            "coming_soon": [],
            "artists_not_found": [],
            "venues_not_found": [],
            "festivals_not_found": [],
            "last_refreshed": None,
            "stale": True,
        }

    # Build coming_soon: filter to only not-yet-on-sale shows across all entities
    coming_soon: list[dict] = []
    for artist, shows in cache.get("artist_shows", {}).items():
        for show in shows:
            if show.get("not_yet_on_sale"):
                coming_soon.append({**show, "artist": artist})
    for venue, shows in cache.get("venue_shows", {}).items():
        for show in shows:
            if show.get("not_yet_on_sale"):
                coming_soon.append({**show, "tracked_venue": venue})
    for festival, shows in cache.get("festival_shows", {}).items():
        for show in shows:
            if show.get("not_yet_on_sale"):
                coming_soon.append({**show, "tracked_festival": festival})

    return {
        "api_configured": api_configured,
        "artist_shows": cache.get("artist_shows", {}),
        "venue_shows": cache.get("venue_shows", {}),
        "festival_shows": cache.get("festival_shows", {}),
        "coming_soon": coming_soon,
        "artists_not_found": cache.get("artists_not_found", []),
        "venues_not_found": cache.get("venues_not_found", []),
        "festivals_not_found": cache.get("festivals_not_found", []),
        "last_refreshed": cache.get("last_refreshed"),
        "stale": False,
    }


# ── Refresh endpoint (triggers TM API fetch) ────────────────────────────────
@app.post("/api/refresh", status_code=202)
async def trigger_refresh() -> Any:
    """Trigger a full TM API fetch cycle. Returns 202 with status polling info."""
    global _refresh_progress

    if _refresh_progress.running:
        raise HTTPException(status_code=409, detail="A refresh is already in progress")

    cfg = _read_config()
    api_key = cfg.get("ticketmaster_api_key") or ""
    if not api_key:
        raise HTTPException(status_code=400, detail="No Ticketmaster API key configured")

    # Reset progress
    _refresh_progress = RefreshProgress()

    # Read previous cache for notification trigger detection
    old_cache: dict | None = None
    if TM_CACHE_FILE.exists():
        try:
            old_cache = json.loads(TM_CACHE_FILE.read_text())
        except Exception:
            pass

    async def _do_refresh():
        global _refresh_progress
        try:
            result = await asyncio.to_thread(
                run_full_refresh,
                api_key,
                cfg.get("artists", {}),
                cfg.get("venues", {}),
                cfg.get("festivals", {}),
                _refresh_progress,
                _geocode,
            )

            # Write cache
            cache_data = {
                "last_refreshed": result.last_refreshed,
                "artist_shows": result.artist_shows,
                "venue_shows": result.venue_shows,
                "festival_shows": result.festival_shows,
                "artists_not_found": result.artists_not_found,
                "venues_not_found": result.venues_not_found,
                "festivals_not_found": result.festivals_not_found,
            }
            TM_CACHE_FILE.write_text(json.dumps(cache_data, indent=2))

            # Detect and write notification triggers
            triggers = detect_triggers(result, old_cache)
            if triggers:
                notification_data = {
                    "generated_at": result.last_refreshed,
                    "triggers": triggers,
                }
                NOTIFICATION_FILE.write_text(json.dumps(notification_data, indent=2))

            # Start background geocoding for shows missing lat/lon
            asyncio.create_task(_background_geocode())

        except Exception as e:
            _refresh_progress.error = str(e)
            _refresh_progress.running = False

    asyncio.create_task(_do_refresh())
    return {"ok": True, "message": "Refresh started. Poll /api/refresh/status for progress."}


@app.get("/api/refresh/status")
def get_refresh_status() -> Any:
    """Return progress of the current or most recent refresh."""
    p = _refresh_progress
    total = p.total_artists + p.total_venues + p.total_festivals
    processed = p.artists_processed + p.venues_processed + p.festivals_processed

    return {
        "running": p.running,
        "phase": p.phase,
        "total": total,
        "processed": processed,
        "artists_total": p.total_artists,
        "artists_processed": p.artists_processed,
        "venues_total": p.total_venues,
        "venues_processed": p.venues_processed,
        "festivals_total": p.total_festivals,
        "festivals_processed": p.festivals_processed,
        "error": p.error,
    }


# ── Notifications ────────────────────────────────────────────────────────────
@app.get("/api/notifications")
def get_notifications() -> Any:
    """Return pending notification triggers."""
    if not NOTIFICATION_FILE.exists():
        return {"generated_at": None, "triggers": []}
    try:
        return json.loads(NOTIFICATION_FILE.read_text())
    except Exception:
        return {"generated_at": None, "triggers": []}


@app.post("/api/notifications/clear")
def clear_notifications() -> Any:
    """Mark notifications as sent by clearing the file."""
    if NOTIFICATION_FILE.exists():
        NOTIFICATION_FILE.unlink(missing_ok=True)
    return {"ok": True}


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
        # Clear TM cache when API key changes
        if TM_CACHE_FILE.exists():
            TM_CACHE_FILE.unlink(missing_ok=True)
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


# ── Geocode progress (for progressive map loading) ──────────────────────────
@app.get("/api/geocode/progress")
def get_geocode_progress() -> Any:
    """Return background geocoding progress for progressive map loading."""
    total_cached = 0
    if GEOCODE_FILE.exists():
        try:
            cache = json.loads(GEOCODE_FILE.read_text())
            total_cached = len(cache)
        except Exception:
            pass

    return {
        "running": _geocode_running,
        "total": _geocode_total,
        "done": _geocode_done,
        "total_cached": total_cached,
    }


# ── Serve built frontend ────────────────────────────────────────────────────
_dist = REPO / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
