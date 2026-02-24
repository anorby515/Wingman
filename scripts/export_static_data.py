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

    # Load geocode cache for center city coordinates
    geocode = {}
    if GEOCODE_CACHE.exists():
        try:
            geocode = json.loads(GEOCODE_CACHE.read_text())
        except Exception:
            pass

    # Resolve center city coordinates from geocode cache
    center_city = config.get("center_city", "")
    center_coords = geocode.get(center_city, {})
    if center_coords:
        state["center_lat"] = center_coords.get("lat")
        state["center_lon"] = center_coords.get("lon")

    # Strip URLs from config — the demo frontend doesn't need them
    # and they're not useful to expose publicly
    artists = {}
    for name, info in config.get("artists", {}).items():
        artists[name] = {
            "genre": info.get("genre", "Other"),
            "paused": info.get("paused", False),
        }

    venues = {}
    for name, info in config.get("venues", {}).items():
        venues[name] = {
            "city": info.get("city", ""),
            "is_local": info.get("is_local", False),
            "paused": info.get("paused", False),
        }

    static = {
        "state": state,
        "config": {
            "center_city": center_city,
            "radius_miles": config.get("radius_miles", 0),
            "artists": artists,
            "venues": venues,
        },
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(static, indent=2) + "\n")
    print(f"Wrote {OUT_FILE} ({OUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
