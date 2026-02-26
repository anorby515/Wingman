#!/usr/bin/env python3
"""Export show data + config into a single static-data.json
that the demo-mode frontend can load without a backend.

Data sources (checked in order):
1. .static_data_fresh marker — if fetch_tm_data.py just ran, skip
2. wingman_config.json + concert_state.json — local files (local dev)
3. docs/summary.json + tracked.json — committed files (CI fallback)
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "concert_state.json"
CONFIG_FILE = ROOT / "wingman_config.json"
TRACKED_FILE = ROOT / "tracked.json"
GEOCODE_CACHE = ROOT / "geocode_cache.json"
SUMMARY_FILE = ROOT / "docs" / "summary.json"
OUT_FILE = ROOT / "frontend" / "public" / "static-data.json"


def _load_tracked_config() -> dict:
    """Load artist/venue/festival config from tracked.json (committed to repo).

    In CI, wingman_config.json is not available (gitignored), but tracked.json
    is committed and contains the same entity data (minus API keys/credentials).
    """
    if not TRACKED_FILE.exists():
        return {"artists": {}, "venues": {}, "festivals": {}}
    try:
        return json.loads(TRACKED_FILE.read_text())
    except Exception:
        return {"artists": {}, "venues": {}, "festivals": {}}


def _export_from_summary(summary: dict) -> dict:
    """Build static-data.json from docs/summary.json (CI fallback).

    The summary has artist_shows in SummaryShow format and coming_soon data.
    Artist/venue config is read from tracked.json (committed to repo).
    """
    tracked = _load_tracked_config()

    artists_cfg = {}
    for name, info in tracked.get("artists", {}).items():
        artists_cfg[name] = {
            "genre": info.get("genre", "Other"),
            "paused": info.get("paused", False),
            "url": info.get("url", ""),
        }

    venues_cfg = {}
    for name, info in tracked.get("venues", {}).items():
        venues_cfg[name] = {
            "city": info.get("city", ""),
            "is_local": info.get("is_local", False),
            "paused": info.get("paused", False),
        }

    return {
        "state": {
            "artist_shows": summary.get("artist_shows", {}),
            "venue_shows": summary.get("venue_shows", {}),
            "center_lat": summary.get("center_lat"),
            "center_lon": summary.get("center_lon"),
        },
        "coming_soon": summary.get("coming_soon", []),
        "coming_soon_fetched": summary.get("coming_soon_fetched"),
        "config": {
            "center_city": tracked.get("center_city", summary.get("center", "")),
            "center_lat": summary.get("center_lat"),
            "center_lon": summary.get("center_lon"),
            "artists": artists_cfg,
            "venues": venues_cfg,
        },
    }


def main():
    # If fetch_tm_data.py already wrote a marker, skip
    # (The marker file is written by fetch_tm_data.py alongside static-data.json)
    marker = ROOT / ".static_data_fresh"
    if marker.exists():
        import time
        if time.time() - marker.stat().st_mtime < 300:
            print("static-data.json was just written by fetch_tm_data.py — skipping export")
            return
        marker.unlink(missing_ok=True)

    # Try the legacy path: concert_state.json + wingman_config.json
    if CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text())

        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
        else:
            print(f"Warning: {STATE_FILE} not found — using empty state")
            state = {}

        # Load geocode cache for center city and venue coordinates
        geocode = {}
        if GEOCODE_CACHE.exists():
            try:
                geocode = json.loads(GEOCODE_CACHE.read_text())
            except Exception:
                pass

        center_city = config.get("center_city", "")
        center_coords = geocode.get(center_city, {})
        if center_coords:
            state["center_lat"] = center_coords.get("lat")
            state["center_lon"] = center_coords.get("lon")
        else:
            if SUMMARY_FILE.exists():
                try:
                    summary = json.loads(SUMMARY_FILE.read_text())
                    if summary.get("center_lat") is not None:
                        state["center_lat"] = summary["center_lat"]
                        state["center_lon"] = summary["center_lon"]
                        print(f"Center coords from summary.json: {state['center_lat']}, {state['center_lon']}")
                except Exception as e:
                    print(f"Warning: could not read center coords from summary.json: {e}")

        artists = {}
        for name, info in config.get("artists", {}).items():
            artists[name] = {
                "genre": info.get("genre", "Other"),
                "paused": info.get("paused", False),
                "url": info.get("url", None),
            }

        venues = {}
        for name, info in config.get("venues", {}).items():
            venue_entry = {
                "city": info.get("city", ""),
                "is_local": info.get("is_local", False),
                "paused": info.get("paused", False),
            }
            venue_city = info.get("city", "")
            venue_coords = geocode.get(venue_city, {})
            if venue_coords:
                venue_entry["lat"] = venue_coords.get("lat")
                venue_entry["lon"] = venue_coords.get("lon")
            venues[name] = venue_entry

        static = {
            "state": state,
            "config": {
                "center_city": center_city,
                "center_lat": state.get("center_lat"),
                "center_lon": state.get("center_lon"),
                "artists": artists,
                "venues": venues,
            },
        }
    elif SUMMARY_FILE.exists():
        # CI fallback: no local config, use committed summary.json
        print(f"No wingman_config.json — falling back to docs/summary.json")
        summary = json.loads(SUMMARY_FILE.read_text())
        static = _export_from_summary(summary)
    else:
        print("Error: no data source available (need wingman_config.json or docs/summary.json)",
              file=sys.stderr)
        sys.exit(1)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(static, indent=2) + "\n")
    print(f"Wrote {OUT_FILE} ({OUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
