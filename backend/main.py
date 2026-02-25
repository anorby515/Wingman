#!/usr/bin/env python3
"""
Wingman PWA Backend
===================
FastAPI server that manages wingman_config.json, concert_state.json,
and the Claude scheduled-tasks.json.  Serves the built React frontend
from ../frontend/dist when present.

Start:  uvicorn backend.main:app --reload --port 8000
  (run from the repo root: /home/user/Wingman)
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
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

# ── Paths ────────────────────────────────────────────────────────────────────
HERE          = Path(__file__).parent
REPO          = HERE.parent
CONFIG_FILE      = REPO / "wingman_config.json"
STATE_FILE       = REPO / "concert_state.json"
FLAGGED_FILE     = REPO / "flagged_items.json"
GEOCODE_FILE     = REPO / "geocode_cache.json"
TM_CACHE_FILE    = REPO / "ticketmaster_cache.json"
TM_CACHE_TTL_HRS = 6
SCRIPT           = REPO / "concert_weekly.py"
SCHEDULE_FILE    = Path("/sessions/eager-gracious-cray/mnt/.claude/scheduled-tasks.json")

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Wingman API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Run-job state ─────────────────────────────────────────────────────────────
_run_proc: Optional[asyncio.subprocess.Process] = None
_run_log:  list[str] = []
_run_returncode: Optional[int] = None


# ── Config helpers ────────────────────────────────────────────────────────────
def _read_config() -> dict:
    if not CONFIG_FILE.exists():
        raise HTTPException(status_code=404, detail="wingman_config.json not found")
    return json.loads(CONFIG_FILE.read_text())


def _write_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


# ── Geocoding helper ──────────────────────────────────────────────────────────
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


# ── Pydantic models ───────────────────────────────────────────────────────────
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


class SchedulePatch(BaseModel):
    next_run: Optional[str] = None       # ISO datetime string
    cron: Optional[str] = None           # cron expression
    enabled: Optional[bool] = None


# ── State endpoint ────────────────────────────────────────────────────────────
@app.get("/api/state")
def get_state() -> Any:
    if not STATE_FILE.exists():
        return {"last_run": None, "artist_shows": {}, "venue_shows": {}}
    return json.loads(STATE_FILE.read_text())


# ── Config endpoint ───────────────────────────────────────────────────────────
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


# ── Settings ──────────────────────────────────────────────────────────────────
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


# ── Artists ───────────────────────────────────────────────────────────────────
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


# ── Venues ────────────────────────────────────────────────────────────────────
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


# ── Festivals ─────────────────────────────────────────────────────────────────
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


# ── Schedule ──────────────────────────────────────────────────────────────────
def _read_schedule() -> dict:
    if SCHEDULE_FILE.exists():
        try:
            data = json.loads(SCHEDULE_FILE.read_text())
            # Support both list-of-tasks and single object formats
            tasks = data if isinstance(data, list) else [data]
            for task in tasks:
                if "concert" in str(task.get("name", "")).lower() or \
                   "concert" in str(task.get("command", "")).lower() or \
                   "concert_weekly" in str(task.get("command", "")).lower():
                    return task
            # Return first task if no concert-specific one found
            if tasks:
                return tasks[0]
        except Exception:
            pass
    return {"next_run": None, "cron": "0 9 * * 6", "enabled": True,
            "_note": f"Schedule file not found at {SCHEDULE_FILE}"}


def _write_schedule(task: dict) -> None:
    if not SCHEDULE_FILE.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Schedule file not accessible at {SCHEDULE_FILE}. "
                   "Changes saved to config only."
        )
    try:
        data = json.loads(SCHEDULE_FILE.read_text())
        tasks = data if isinstance(data, list) else [data]
        # Find and update the concert task
        updated = False
        for i, t in enumerate(tasks):
            if "concert" in str(t.get("name", "")).lower() or \
               "concert_weekly" in str(t.get("command", "")).lower():
                tasks[i].update(task)
                updated = True
                break
        if not updated and tasks:
            tasks[0].update(task)
        out = tasks if isinstance(data, list) else tasks[0]
        SCHEDULE_FILE.write_text(json.dumps(out, indent=2))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not write schedule: {e}")


@app.get("/api/schedule")
def get_schedule() -> Any:
    return _read_schedule()


@app.patch("/api/schedule")
def patch_schedule(body: SchedulePatch) -> Any:
    task = _read_schedule()
    updates: dict = {}
    if body.next_run is not None:
        updates["next_run"] = body.next_run
    if body.cron is not None:
        updates["cron"] = body.cron
    if body.enabled is not None:
        updates["enabled"] = body.enabled

    if not updates:
        return task

    try:
        _write_schedule(updates)
        task.update(updates)
    except HTTPException as e:
        # Schedule file unavailable — store desired next_run in config as fallback
        cfg = _read_config()
        cfg["_next_run_override"] = updates.get("next_run")
        _write_config(cfg)
        task.update(updates)
        task["_warning"] = str(e.detail)

    return task


# ── Run now ───────────────────────────────────────────────────────────────────
@app.get("/api/run/status")
def run_status() -> Any:
    global _run_proc, _run_log, _run_returncode
    if _run_proc is None:
        return {"running": False, "returncode": _run_returncode, "log": _run_log}
    if _run_proc.returncode is not None:
        return {"running": False, "returncode": _run_proc.returncode, "log": _run_log}
    return {"running": True, "returncode": None, "log": _run_log}


@app.post("/api/run")
async def trigger_run() -> Any:
    global _run_proc, _run_log, _run_returncode

    if _run_proc is not None and _run_proc.returncode is None:
        raise HTTPException(status_code=409, detail="A run is already in progress")

    _run_log = []
    _run_returncode = None

    async def _stream():
        global _run_proc, _run_log, _run_returncode
        _run_proc = await asyncio.create_subprocess_exec(
            sys.executable, str(SCRIPT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(REPO),
        )
        async for line in _run_proc.stdout:
            _run_log.append(line.decode(errors="replace").rstrip())
        await _run_proc.wait()
        _run_returncode = _run_proc.returncode

    asyncio.create_task(_stream())
    return {"ok": True, "message": "Run started. Poll /api/run/status for progress."}


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


# ── Ticketmaster Coming Soon ──────────────────────────────────────────────────

def _name_matches(artist_name: str, attraction_names: list[str]) -> bool:
    """Return True if artist_name has a reasonable TM attraction name match."""
    a = artist_name.lower()
    for n in attraction_names:
        nl = n.lower()
        if a in nl or nl in a:
            return True
    return False


def _format_show_date(local_date: str) -> str:
    """Convert '2026-07-15' → 'Jul 15, 2026'."""
    try:
        dt = datetime.strptime(local_date, "%Y-%m-%d")
        return dt.strftime("%b %-d, %Y")
    except Exception:
        return local_date


def _fetch_tm_coming_soon(api_key: str, artists: dict) -> list[dict]:
    """Call Ticketmaster Discovery API for each tracked artist.
    Returns shows whose public on-sale date is in the future."""
    now_utc = datetime.now(timezone.utc)
    results: list[dict] = []

    for artist_name, artist_info in artists.items():
        if artist_info.get("paused", False):
            continue

        params = urllib.parse.urlencode({
            "apikey": api_key,
            "keyword": artist_name,
            "classificationName": "music",
            "size": "50",
            "sort": "date,asc",
        })
        url = f"https://app.ticketmaster.com/discovery/v2/events.json?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Wingman/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception:
            continue

        events = data.get("_embedded", {}).get("events", [])

        for event in events:
            # Validate attraction name match (when attractions are present)
            attractions = event.get("_embedded", {}).get("attractions", [])
            if attractions:
                names = [a.get("name", "") for a in attractions]
                if not _name_matches(artist_name, names):
                    continue

            # Only North America
            venues = event.get("_embedded", {}).get("venues", [])
            if not venues:
                continue
            venue = venues[0]
            country = venue.get("country", {}).get("countryCode", "")
            if country not in ("US", "CA", "MX"):
                continue

            # Only shows whose public on-sale is in the future
            sales = event.get("sales", {})
            public_sale = sales.get("public", {})
            onsale_str = public_sale.get("startDateTime")
            onsale_tbd = public_sale.get("startTBD", False)

            if onsale_str:
                try:
                    onsale_dt = datetime.fromisoformat(onsale_str.replace("Z", "+00:00"))
                    if onsale_dt <= now_utc:
                        continue  # Already on sale
                except Exception:
                    continue
            elif not onsale_tbd:
                continue  # No future on-sale info at all

            # Extract presales
            presales = []
            for p in sales.get("presales", []):
                presales.append({
                    "name": p.get("name", "Presale"),
                    "start_datetime": p.get("startDateTime"),
                    "end_datetime": p.get("endDateTime"),
                })

            # Format city
            city_name = venue.get("city", {}).get("name", "")
            state_code = venue.get("state", {}).get("stateCode", "")
            if country == "US":
                city = f"{city_name}, {state_code}" if state_code else city_name
            elif country == "CA":
                city = f"{city_name}, {state_code}, CA" if state_code else f"{city_name}, CA"
            else:
                city = f"{city_name}, MX"

            # Geocode venue
            venue_name = venue.get("name", "")
            lat, lon = None, None
            coords = _geocode(f"{venue_name}, {city}")
            if not coords:
                coords = _geocode(city)
            if coords:
                lat, lon = coords

            results.append({
                "artist": artist_name,
                "genre": artist_info.get("genre", "Other"),
                "date": _format_show_date(
                    event.get("dates", {}).get("start", {}).get("localDate", "")
                ),
                "venue": venue_name,
                "city": city,
                "onsale_datetime": onsale_str,
                "onsale_tbd": onsale_tbd,
                "presales": presales,
                "ticketmaster_url": event.get("url", ""),
                "lat": lat,
                "lon": lon,
            })

    return results


@app.get("/api/coming-soon")
def get_coming_soon(force: bool = False) -> Any:
    cfg = _read_config()
    api_key = cfg.get("ticketmaster_api_key") or ""

    if not api_key:
        return {"api_configured": False, "shows": [], "last_fetched": None}

    now_utc = datetime.now(timezone.utc)

    # Return cached data if fresh
    if not force and TM_CACHE_FILE.exists():
        try:
            cache = json.loads(TM_CACHE_FILE.read_text())
            fetched_at = datetime.fromisoformat(cache["last_fetched"])
            age_hours = (now_utc - fetched_at).total_seconds() / 3600
            if age_hours < TM_CACHE_TTL_HRS:
                return {
                    "api_configured": True,
                    "shows": cache.get("shows", []),
                    "last_fetched": cache["last_fetched"],
                }
        except Exception:
            pass

    # Fetch fresh from TM API
    shows = _fetch_tm_coming_soon(api_key, cfg.get("artists", {}))
    last_fetched = now_utc.isoformat()

    try:
        TM_CACHE_FILE.write_text(json.dumps(
            {"last_fetched": last_fetched, "shows": shows}, indent=2
        ))
    except Exception:
        pass

    return {"api_configured": True, "shows": shows, "last_fetched": last_fetched}


# ── Serve built frontend ──────────────────────────────────────────────────────
_dist = REPO / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
