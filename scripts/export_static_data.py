#!/usr/bin/env python3
"""Export show data + config into a single static-data.json
that the demo-mode frontend can load without a backend.

Data sources (checked in order):
1. .static_data_fresh marker — if fetch_tm_data.py just ran, skip
2. docs/summary.json + tracked.json — committed files (CI / local fallback)
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRACKED_FILE = ROOT / "tracked.json"
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
    """Build static-data.json from docs/summary.json.

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

    if not SUMMARY_FILE.exists():
        print("Error: docs/summary.json not found — no data source available",
              file=sys.stderr)
        sys.exit(1)

    print(f"Exporting from docs/summary.json + tracked.json")
    summary = json.loads(SUMMARY_FILE.read_text())
    static = _export_from_summary(summary)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(static, indent=2) + "\n")
    print(f"Wrote {OUT_FILE} ({OUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
