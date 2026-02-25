#!/usr/bin/env python3
"""Export show data + config into a single static-data.json
that the demo-mode frontend can load without a backend.

Data sources (checked in order):
1. frontend/public/static-data.json — if already produced by fetch_tm_data.py, skip
2. wingman_config.json + concert_state.json — legacy local files
3. docs/summary.json — committed by the daily GitHub Action (CI fallback)
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "concert_state.json"
CONFIG_FILE = ROOT / "wingman_config.json"
GEOCODE_CACHE = ROOT / "geocode_cache.json"
SUMMARY_FILE = ROOT / "docs" / "summary.json"
OUT_FILE = ROOT / "frontend" / "public" / "static-data.json"


def _export_from_summary(summary: dict) -> dict:
    """Build static-data.json from docs/summary.json (CI fallback).

    The summary has artist_shows in SummaryShow format and coming_soon data.
    The demo frontend reads artist_shows from state.artist_shows.
    """
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
            "center_city": summary.get("center", ""),
            "artists": {},
            "venues": {},
        },
    }


def main():
    # If fetch_tm_data.py already wrote static-data.json, nothing to do
    if OUT_FILE.exists():
        age = OUT_FILE.stat().st_mtime
        import time
        if time.time() - age < 300:  # Written in last 5 minutes
            print(f"static-data.json is fresh (written recently) — skipping export")
            return

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
