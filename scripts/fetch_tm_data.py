#!/usr/bin/env python3
"""
Wingman Daily Data Fetch Script
================================
Used by the GitHub Action to fetch Ticketmaster data, geocode venues,
generate docs/summary.json, docs/history/YYYY-MM-DD.json, and
frontend/public/static-data.json for the demo build.

Uses the shared TM logic from backend/ticketmaster.py.

Usage:
  python scripts/fetch_tm_data.py [--config PATH] [--api-key KEY]

Environment variables:
  TICKETMASTER_API_KEY — TM API key (required in CI)
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# Add repo root to path so we can import from backend
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.ticketmaster import RefreshProgress, RefreshResult, run_full_refresh


# ── Geocoding ────────────────────────────────────────────────────────────────

def geocode(location: str, cache: dict) -> tuple[float, float] | None:
    """Geocode a location string using Nominatim, with caching."""
    if location in cache:
        entry = cache[location]
        return (entry["lat"], entry["lon"])

    # Rate limit: 1 req/sec
    time.sleep(1)

    params = urllib.parse.urlencode({
        "q": location,
        "format": "json",
        "limit": "1",
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Wingman/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read())
            if results:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                cache[location] = {"lat": lat, "lon": lon}
                return (lat, lon)
    except Exception as e:
        print(f"  Geocoding failed for '{location}': {e}")
    return None


# ── Config loading ───────────────────────────────────────────────────────────

def load_config(config_path: pathlib.Path) -> dict:
    """Load tracking config from tracked.json (committed) or wingman_config.json (local).

    In CI, tracked.json is always available since it's committed to the repo.
    Locally, wingman_config.json is the primary source (tracked.json is also fine).
    """
    if config_path.exists():
        print(f"Loading config from {config_path}")
        return json.loads(config_path.read_text())

    print(f"Error: config file not found: {config_path}", file=sys.stderr)
    sys.exit(1)


# ── Summary generation ───────────────────────────────────────────────────────

def build_summary(
    result: RefreshResult,
    config: dict,
    geocode_cache: dict,
    prev_summary: dict | None,
) -> dict:
    """Build docs/summary.json from a TM refresh result."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    center_city = config.get("center_city", "")

    # Center coordinates
    center_coords = geocode_cache.get(center_city, {})
    center_lat = center_coords.get("lat", 0.0)
    center_lon = center_coords.get("lon", 0.0)

    # Previous data for diff detection
    prev_artist_shows = prev_summary.get("artist_shows", {}) if prev_summary else {}
    prev_show_keys: set[str] = set()
    for artist, shows in prev_artist_shows.items():
        for show in shows:
            prev_show_keys.add(f"{artist}|{show.get('date', '')}|{show.get('venue', '')}")

    prev_venue_shows = prev_summary.get("venue_shows", {}) if prev_summary else {}
    prev_venue_keys: set[str] = set()
    for venue, shows in prev_venue_shows.items():
        for show in shows:
            prev_venue_keys.add(f"{venue}|{show.get('date', '')}|{show.get('artist', '')}")

    # Tracked artist names for venue show "tracked" flag
    tracked_artist_names = {a.lower() for a in config.get("artists", {})}

    # ── Artist shows ──
    summary_artist_shows: dict[str, list] = {}
    coming_soon: list[dict] = []
    changes_artists: dict[str, dict] = {}
    total_added = 0
    total_removed = 0

    for artist, shows in result.artist_shows.items():
        summary_shows = []
        added = []

        for show in shows:
            key = f"{artist}|{show['date']}|{show['venue']}"
            is_new = key not in prev_show_keys

            summary_show = {
                "date": show["date"],
                "venue": show["venue"],
                "city": show["city"],
                "status": "on_sale",
                "lat": show.get("lat"),
                "lon": show.get("lon"),
                "is_new": is_new,
            }
            summary_shows.append(summary_show)

            if is_new:
                added.append(summary_show)
                total_added += 1

            # Collect coming-soon shows
            if show.get("not_yet_on_sale"):
                coming_soon.append({
                    "artist": artist,
                    "genre": show.get("genre", "Other"),
                    "date": show["date"],
                    "venue": show["venue"],
                    "city": show["city"],
                    "onsale_datetime": show.get("onsale_datetime"),
                    "onsale_tbd": show.get("onsale_tbd", False),
                    "presales": show.get("presales", []),
                    "ticketmaster_url": show.get("ticketmaster_url", ""),
                    "lat": show.get("lat"),
                    "lon": show.get("lon"),
                })

        if summary_shows:
            summary_artist_shows[artist] = summary_shows

        # Detect removed shows
        removed = []
        if artist in prev_artist_shows:
            new_keys = {f"{artist}|{s['date']}|{s['venue']}" for s in shows}
            for prev_show in prev_artist_shows[artist]:
                pk = f"{artist}|{prev_show.get('date', '')}|{prev_show.get('venue', '')}"
                if pk not in new_keys:
                    removed.append(prev_show)
                    total_removed += 1

        if added or removed:
            changes_artists[artist] = {
                "added": added,
                "removed": removed,
                "newly_sold": [],
            }

    # ── Venue shows ──
    summary_venue_shows: dict[str, list] = {}
    changes_venues: dict[str, dict] = {}

    for venue, shows in result.venue_shows.items():
        venue_summary = []
        v_added = []

        for show in shows:
            artist = show.get("artist", "")
            tracked = artist.lower() in tracked_artist_names
            entry = {"date": show["date"], "artist": artist, "tracked": tracked}
            venue_summary.append(entry)

            key = f"{venue}|{show['date']}|{artist}"
            if key not in prev_venue_keys:
                v_added.append(entry)

        if venue_summary:
            summary_venue_shows[venue] = venue_summary

        # Detect removed venue shows
        v_removed = []
        if venue in prev_venue_shows:
            new_keys = {f"{venue}|{s['date']}|{s.get('artist', '')}" for s in shows}
            for prev_show in prev_venue_shows[venue]:
                pk = f"{venue}|{prev_show.get('date', '')}|{prev_show.get('artist', '')}"
                if pk not in new_keys:
                    v_removed.append(prev_show)

        if v_added or v_removed:
            changes_venues[venue] = {"added": v_added, "removed": v_removed}

    return {
        "generated_at": today,
        "center": center_city,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "artist_shows": summary_artist_shows,
        "venue_shows": summary_venue_shows,
        "changes": {
            "artists": changes_artists,
            "venues": changes_venues,
            "total_added": total_added,
            "total_removed": total_removed,
            "total_sold_out": 0,
        },
        "coming_soon": coming_soon,
        "coming_soon_fetched": datetime.now(timezone.utc).isoformat(),
    }


# ── Static data for demo frontend ───────────────────────────────────────────

def build_static_data(
    result: RefreshResult,
    config: dict,
    geocode_cache: dict,
    summary: dict,
) -> dict:
    """Build frontend/public/static-data.json for the demo-mode frontend.

    The demo frontend expects:
      state.artist_shows — TM cache format (with not_yet_on_sale, ticketmaster_url, etc.)
      state.venue_shows  — TM cache venue format (with artist field)
      state.center_lat / state.center_lon
      coming_soon        — array of coming soon shows
      coming_soon_fetched — ISO 8601 timestamp
      config.center_city / config.artists / config.venues
    """
    center_city = config.get("center_city", "")
    center_coords = geocode_cache.get(center_city, {})

    # Artist config (stripped of secrets)
    artists_cfg = {}
    for name, info in config.get("artists", {}).items():
        artists_cfg[name] = {
            "genre": info.get("genre", "Other"),
            "paused": info.get("paused", False),
            "url": info.get("url", ""),
        }

    # Venue config with coordinates
    venues_cfg = {}
    for name, info in config.get("venues", {}).items():
        entry = {
            "city": info.get("city", ""),
            "is_local": info.get("is_local", False),
            "paused": info.get("paused", False),
        }
        venue_city = info.get("city", "")
        coords = geocode_cache.get(venue_city, {})
        if coords:
            entry["lat"] = coords["lat"]
            entry["lon"] = coords["lon"]
        venues_cfg[name] = entry

    return {
        "state": {
            "artist_shows": result.artist_shows,
            "venue_shows": result.venue_shows,
            "center_lat": center_coords.get("lat"),
            "center_lon": center_coords.get("lon"),
        },
        "coming_soon": summary.get("coming_soon", []),
        "coming_soon_fetched": summary.get("coming_soon_fetched"),
        "config": {
            "center_city": center_city,
            "artists": artists_cfg,
            "venues": venues_cfg,
        },
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Wingman Daily TM Data Fetch")
    parser.add_argument(
        "--config", type=str,
        default=str(ROOT / "tracked.json"),
        help="Path to tracked.json or wingman_config.json",
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="Override TM API key (default: env TICKETMASTER_API_KEY or config)",
    )
    args = parser.parse_args()

    config = load_config(pathlib.Path(args.config))

    # Resolve API key: CLI flag > env var > config file
    api_key = (
        args.api_key
        or os.environ.get("TICKETMASTER_API_KEY")
        or config.get("ticketmaster_api_key")
    )
    if not api_key:
        print("Error: no Ticketmaster API key provided", file=sys.stderr)
        print("Set TICKETMASTER_API_KEY env var or include in config", file=sys.stderr)
        sys.exit(1)

    # Load previous summary for diff detection
    summary_path = ROOT / "docs" / "summary.json"
    prev_summary = None
    if summary_path.exists():
        try:
            prev_summary = json.loads(summary_path.read_text())
        except Exception:
            pass

    # Geocode cache (may not exist in CI on first run)
    geocode_cache: dict = {}
    geocode_cache_path = ROOT / "geocode_cache.json"
    if geocode_cache_path.exists():
        try:
            geocode_cache = json.loads(geocode_cache_path.read_text())
        except Exception:
            pass

    # Also load coords from previous summary as fallback
    if prev_summary:
        center = prev_summary.get("center", "")
        if center and center not in geocode_cache:
            clat = prev_summary.get("center_lat")
            clon = prev_summary.get("center_lon")
            if clat is not None and clon is not None:
                geocode_cache[center] = {"lat": clat, "lon": clon}

    # Geocode center city
    center_city = config.get("center_city", "")
    if center_city and center_city not in geocode_cache:
        print(f"Geocoding center city: {center_city}")
        geocode(center_city, geocode_cache)

    artists = config.get("artists", {})
    venues = config.get("venues", {})
    festivals = config.get("festivals", {})

    active_artists = sum(1 for a in artists.values() if not a.get("paused"))
    active_venues = sum(1 for v in venues.values() if not v.get("paused"))
    active_festivals = sum(1 for f in festivals.values() if not f.get("paused"))

    print(f"Fetching TM data: {active_artists} artists, "
          f"{active_venues} venues, {active_festivals} festivals")

    progress = RefreshProgress()

    def geocode_fn(location: str) -> tuple[float, float] | None:
        return geocode(location, geocode_cache)

    result = run_full_refresh(
        api_key, artists, venues, festivals, progress, geocode_fn,
    )

    total_shows = sum(len(s) for s in result.artist_shows.values())
    print(f"Fetched: {len(result.artist_shows)} artists with shows, "
          f"{total_shows} total shows")
    if result.artists_not_found:
        print(f"Artists not found on TM: {', '.join(result.artists_not_found)}")
    if result.venues_not_found:
        print(f"Venues not found on TM: {', '.join(result.venues_not_found)}")
    if result.festivals_not_found:
        print(f"Festivals not found on TM: {', '.join(result.festivals_not_found)}")

    # Build docs/summary.json
    summary = build_summary(result, config, geocode_cache, prev_summary)

    docs_dir = ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {summary_path} ({summary_path.stat().st_size:,} bytes)")

    # Write docs/history/YYYY-MM-DD.json
    history_dir = docs_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history_path = history_dir / f"{today}.json"
    history_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {history_path}")

    # Build frontend/public/static-data.json for demo build
    static_data = build_static_data(result, config, geocode_cache, summary)
    static_path = ROOT / "frontend" / "public" / "static-data.json"
    static_path.parent.mkdir(parents=True, exist_ok=True)
    static_path.write_text(json.dumps(static_data, indent=2) + "\n")
    print(f"Wrote {static_path} ({static_path.stat().st_size:,} bytes)")

    # Print summary stats
    print(f"\n--- Summary ---")
    print(f"Date: {today}")
    print(f"Artists with shows: {len(result.artist_shows)}")
    print(f"Total shows: {total_shows}")
    print(f"Changes: +{summary['changes']['total_added']} added, "
          f"-{summary['changes']['total_removed']} removed")

    # Write stats for the workflow to read via $GITHUB_OUTPUT
    stats_path = ROOT / ".fetch_stats.json"
    stats_path.write_text(json.dumps({
        "date": today,
        "artists_count": len(result.artist_shows),
        "total_shows": total_shows,
    }))


if __name__ == "__main__":
    main()
