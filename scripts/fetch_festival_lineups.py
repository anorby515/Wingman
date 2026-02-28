#!/usr/bin/env python3
"""Fetch festival poster images from festival websites.

Reads tracked festivals from tracked.json, fetches each festival's lineup URL,
extracts the poster image (og:image), and writes to festival_lineups.json.

Lineup artist data is managed manually via the Configure UI — this script
never overwrites it. Only the poster image URL is updated.

No pip dependencies — uses only Python stdlib.

Usage:
    python3 scripts/fetch_festival_lineups.py [--dry-run]
"""

from __future__ import annotations

import html.parser
import json
import pathlib
import ssl
import sys
import urllib.request
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRACKED_FILE = ROOT / "tracked.json"
LINEUPS_FILE = ROOT / "festival_lineups.json"

# ── HTML image extractor ──────────────────────────────────────────────────

class _ImageExtractor(html.parser.HTMLParser):
    """Extract og:image (or twitter:image fallback) from HTML."""

    SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__()
        self.og_image: str | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

        if tag == "meta" and self._skip_depth == 0:
            attr_dict = dict(attrs)
            prop = attr_dict.get("property", "")
            name = attr_dict.get("name", "")
            content = attr_dict.get("content", "")
            if prop == "og:image" and content:
                self.og_image = content
            elif name == "twitter:image" and content and not self.og_image:
                self.og_image = content

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)


def _fetch_page(url: str) -> str | None:
    """Fetch a URL and return its HTML content."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def _extract_image(html_content: str) -> str | None:
    """Parse HTML and return og:image URL."""
    extractor = _ImageExtractor()
    try:
        extractor.feed(html_content)
    except Exception:
        pass
    return extractor.og_image


# ── Main logic ──────────────────────────────────────────────────────────────

def _load_existing() -> dict:
    """Load existing festival_lineups.json if present."""
    if LINEUPS_FILE.exists():
        try:
            return json.loads(LINEUPS_FILE.read_text())
        except Exception:
            pass
    return {}


def fetch_poster(name: str, url: str, existing: dict | None = None) -> dict:
    """Fetch poster image for a festival.

    Only updates the image_url. All other data (days, artists, venue, city)
    is preserved from existing data — lineup content is managed manually.
    """
    print(f"\n  Fetching: {url}")

    # Start with existing data or empty structure
    result = dict(existing) if existing else {}
    result.setdefault("lineup_url", url)
    result.setdefault("days", [])

    html_content = _fetch_page(url)
    if not html_content:
        print("  Fetch failed — keeping existing data")
        return result

    og_image = _extract_image(html_content)
    if og_image:
        result["image_url"] = og_image
        print(f"  Poster image: {og_image}")
    else:
        print("  No poster image found on page")

    result["lineup_url"] = url
    result["last_updated"] = date.today().isoformat()

    return result


def main():
    dry_run = "--dry-run" in sys.argv

    if not TRACKED_FILE.exists():
        print("Error: tracked.json not found", file=sys.stderr)
        sys.exit(1)

    tracked = json.loads(TRACKED_FILE.read_text())
    festivals = tracked.get("festivals", {})

    if not festivals:
        print("No festivals found in tracked.json")
        return

    existing = _load_existing()
    updated = dict(existing)

    print(f"Fetching poster images for {len(festivals)} festival(s)...")

    for name, info in festivals.items():
        if info.get("paused", False):
            print(f"\n  Skipping {name} (paused)")
            continue

        url = info.get("url", "")
        if not url:
            print(f"\n  Skipping {name} (no URL)")
            continue

        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")

        result = fetch_poster(name, url, existing=existing.get(name))
        updated[name] = result

    if dry_run:
        print("\n\nDRY RUN — would write:")
        print(json.dumps(updated, indent=2))
    else:
        LINEUPS_FILE.write_text(json.dumps(updated, indent=2) + "\n")
        print(f"\n\nWrote {LINEUPS_FILE}")
        print(f"  {len(updated)} festival(s)")

    # Summary
    print("\n--- Summary ---")
    for name, data in updated.items():
        total = sum(len(d.get("artists", [])) for d in data.get("days", []))
        has_poster = bool(data.get("image_url"))
        parts = []
        if has_poster:
            parts.append("poster")
        if total > 0:
            parts.append(f"{total} artists")
        print(f"  {name}: {', '.join(parts) if parts else 'no data'}")


if __name__ == "__main__":
    main()
