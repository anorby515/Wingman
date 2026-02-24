#!/usr/bin/env python3
"""Export concert_state.json + wingman_config.json into a single static-data.json
that the demo-mode frontend can load without a backend."""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "concert_state.json"
CONFIG_FILE = ROOT / "wingman_config.json"
GEOCODE_CACHE = ROOT / "geocode_cache.json"
SUMMARY_FILE = ROOT / "docs" / "summary.json"
OUT_FILE = ROOT / "frontend" / "public" / "static-data.json"


def main():
    if not STATE_FILE.exists():
        print(f"Warning: {STATE_FILE} not found — using empty state")
        state = {}
    else:
        state = json.loads(STATE_FILE.read_text())

    if not CONFIG_FILE.exists():
        print(f"Error: {CONFIG_FILE} not found", file=sys.stderr)
        sys.exit(1)

    config = json.loads(CONFIG_FILE.read_text())

    # Load geocode cache for center city and venue coordinates
    geocode = {}
    if GEOCODE_CACHE.exists():
        try:
            geocode = json.loads(GEOCODE_CACHE.read_text())
        except Exception:
            pass

    # Resolve center city coordinates from geocode cache, falling back to
    # docs/summary.json (which is committed and always has geocoded coords).
    # geocode_cache.json is gitignored so it won't exist in CI.
    center_city = config.get("center_city", "")
    center_coords = geocode.get(center_city, {})
    if center_coords:
        state["center_lat"] = center_coords.get("lat")
        state["center_lon"] = center_coords.get("lon")
    else:
        # Fallback: read from docs/summary.json (written by Cowork, committed to git)
        if SUMMARY_FILE.exists():
            try:
                summary = json.loads(SUMMARY_FILE.read_text())
                if summary.get("center_lat") is not None:
                    state["center_lat"] = summary["center_lat"]
                    state["center_lon"] = summary["center_lon"]
                    print(f"Center coords from summary.json: {state['center_lat']}, {state['center_lon']}")
            except Exception as e:
                print(f"Warning: could not read center coords from summary.json: {e}")

    # Strip URLs from config — the demo frontend doesn't need them
    # and they're not useful to expose publicly
    artists = {}
    for name, info in config.get("artists", {}).items():
        artists[name] = {
            "genre": info.get("genre", "Other"),
            "paused": info.get("paused", False),
        }

    # Include venue lat/lon from geocode cache for map rendering
    venues = {}
    for name, info in config.get("venues", {}).items():
        venue_entry = {
            "city": info.get("city", ""),
            "is_local": info.get("is_local", False),
            "paused": info.get("paused", False),
        }
        # Resolve venue coordinates from geocode cache
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
            "artists": artists,
            "venues": venues,
        },
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(static, indent=2) + "\n")
    print(f"Wrote {OUT_FILE} ({OUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
