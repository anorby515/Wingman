#!/usr/bin/env python3
"""Fetch festival lineup data from festival websites.

Reads tracked festivals from tracked.json, fetches each festival's lineup URL,
extracts artist names and poster images, and writes to festival_lineups.json.

No pip dependencies — uses only Python stdlib.

Usage:
    python3 scripts/fetch_festival_lineups.py [--dry-run]
"""

from __future__ import annotations

import html.parser
import json
import pathlib
import re
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRACKED_FILE = ROOT / "tracked.json"
LINEUPS_FILE = ROOT / "festival_lineups.json"

# ── HTML text extractor ────────────────────────────────────────────────────

class _TextExtractor(html.parser.HTMLParser):
    """Extract visible text from HTML, preserving structure hints."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "path", "meta", "link"}

    def __init__(self):
        super().__init__()
        self.texts: list[str] = []
        self.og_image: str | None = None
        self.meta_images: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

        # Extract og:image and other meta images
        if tag == "meta":
            prop = attr_dict.get("property", "")
            name = attr_dict.get("name", "")
            content = attr_dict.get("content", "")
            if prop == "og:image" and content:
                self.og_image = content
            elif name == "twitter:image" and content and not self.og_image:
                self.og_image = content

        # Block-level tags get newlines for structure
        if tag in ("div", "p", "h1", "h2", "h3", "h4", "h5", "h6",
                    "li", "tr", "br", "section", "article", "header"):
            self.texts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._skip_depth == 0:
            self.texts.append(data)


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


def _extract_text_and_image(html_content: str) -> tuple[str, str | None]:
    """Parse HTML and return (text_content, og_image_url)."""
    extractor = _TextExtractor()
    try:
        extractor.feed(html_content)
    except Exception:
        pass
    text = "".join(extractor.texts)
    return text, extractor.og_image


# ── Artist name extraction ──────────────────────────────────────────────────

# Words that are NOT artist names (common on festival pages)
NOISE_WORDS = {
    # Festival page structure
    "lineup", "tickets", "festival", "music", "arts", "experience",
    "schedule", "info", "faq", "contact", "sponsors", "partners",
    "vip", "general admission", "ga", "camping", "parking", "map",
    "directions", "volunteer", "about", "news", "shop", "merch",
    "home", "buy tickets", "get tickets", "sold out", "on sale",
    "presented by", "powered by", "sponsored by", "in partnership",
    # Navigation / UI
    "menu", "close", "open", "back", "next", "previous",
    "browse faqs", "search help", "help center", "help",
    "contact us", "safety", "accessibility", "social",
    "buy merch", "book hotel", "download app", "reserve locker",
    "view full lineup", "share lineup", "view lineup",
    # Legal / policy
    "terms", "privacy", "cookie", "copyright", "all rights reserved",
    "privacy policy", "cookie policy", "cookie settings", "cookie management",
    "visitor policy", "terms of use", "terms of service",
    "do not sell or share my personal information",
    # Social / marketing
    "follow us", "subscribe", "newsletter", "email", "sign up",
    "facebook", "instagram", "twitter", "twitter/x", "tiktok",
    "youtube", "spotify", "discord", "reddit",
    "get updates", "connect",
    # Day/date words
    "friday", "saturday", "sunday", "monday", "tuesday", "wednesday",
    "thursday", "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "day 1", "day 2", "day 3", "day 4", "stage", "main stage",
    "second stage", "tent", "more to come", "tba", "tbd",
    "and more", "more artists", "full lineup",
    # Misc page junk
    "no items found.", "our other festivals", "past lineups",
}

# Day header patterns
DAY_PATTERN = re.compile(
    r"^(?:day\s*\d|(?:friday|saturday|sunday|monday|tuesday|wednesday|thursday)"
    r"(?:\s*,?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r"(?:\w*)\s*\d{1,2})?)",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}",
    re.IGNORECASE,
)


def _normalize_for_comparison(name: str) -> str:
    """Strip common festival suffixes and non-alphanumeric chars for matching."""
    s = name.lower().strip()
    for suffix in ("music festival", "music fest", "festival", "fest"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    return re.sub(r"[^a-z0-9]", "", s)


def _is_noise(text: str, festival_name: str = "") -> bool:
    """Return True if text is a common non-artist word."""
    lower = text.lower().strip()
    if lower in NOISE_WORDS:
        return True
    if len(lower) < 2:
        return True
    if len(lower) > 80:
        return True
    # Pure numbers, dates, times
    if re.match(r"^\d+$", lower):
        return True
    if re.match(r"^\d{1,2}:\d{2}", lower):
        return True
    # URLs
    if lower.startswith(("http://", "https://", "www.")):
        return True
    # Copyright lines
    if "©" in lower or "copyright" in lower:
        return True
    # Marketing CTAs and ticket language
    if any(kw in lower for kw in (
        "on sale", "buy now", "sold out", "waitlist", "tickets remain",
        "sign up", "get updates", "limited time", "starting at $",
        "check it out", "learn more", "view premium",
    )):
        return True
    # Looks like a US state abbreviation + city (e.g. "Saint Charles, Iowa")
    if re.match(r"^[a-z\s.]+,\s*[a-z\s]+$", lower) and len(lower) < 40:
        return True
    # All-caps location patterns (e.g. "HARRIET ISLAND REGIONAL PARK")
    if text.isupper() and any(kw in lower for kw in ("park", "island", "center", "arena", "stadium")):
        return True
    # Date range patterns (e.g. "July 30 - Aug. 2, 2026", "April 18-19, 2026")
    if re.match(r"^[a-z]+\.?\s+\d{1,2}\s*[-–]\s*", lower):
        return True
    if re.search(r"\b20\d{2}\b", lower) and re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", lower):
        return True
    # Festival's own name appearing as an "artist" — uses normalised comparison
    # so "Stagecoach Music Festival" is caught for config name "Stage Coach Festival"
    if festival_name:
        if lower == festival_name.lower():
            return True
        fn = _normalize_for_comparison(festival_name)
        tn = _normalize_for_comparison(text)
        if fn and tn and (fn == tn or fn in tn or tn in fn):
            return True
    # "or sign up via email" and similar patterns
    if lower.startswith("or ") and len(lower) < 30:
        return True
    # "be the first to know" type marketing
    if "first to know" in lower or "be the first" in lower:
        return True
    return False


def _extract_artists_from_text(text: str, festival_name: str = "") -> dict[str, list[str]]:
    """Extract artist names from page text, grouped by day if possible.

    Returns a dict mapping day labels to artist lists.
    If no day structure is found, returns {"all": [artists]}.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    days: dict[str, list[str]] = {}
    current_day = "all"
    seen = set()

    for line in lines:
        # Check if this is a day header
        if DAY_PATTERN.match(line) or DATE_PATTERN.match(line):
            current_day = line.strip()
            if current_day not in days:
                days[current_day] = []
            continue

        # Skip noise
        if _is_noise(line, festival_name):
            continue

        # Some pages use bullet separators or pipes
        # Split on common delimiters if line has multiple artists
        candidates = []
        if " | " in line:
            candidates = [s.strip() for s in line.split(" | ")]
        elif " · " in line:
            candidates = [s.strip() for s in line.split(" · ")]
        elif "\u2022" in line:  # bullet
            candidates = [s.strip() for s in line.split("\u2022")]
        else:
            candidates = [line]

        for candidate in candidates:
            candidate = candidate.strip(" \t\r\n•·|–—-*,")
            if not candidate or _is_noise(candidate, festival_name):
                continue

            # Normalize whitespace
            candidate = re.sub(r"\s+", " ", candidate)

            key = candidate.lower()
            if key not in seen:
                seen.add(key)
                if current_day not in days:
                    days[current_day] = []
                days[current_day].append(candidate)

    return days


# ── Main logic ──────────────────────────────────────────────────────────────

def _load_existing() -> dict:
    """Load existing festival_lineups.json if present."""
    if LINEUPS_FILE.exists():
        try:
            return json.loads(LINEUPS_FILE.read_text())
        except Exception:
            pass
    return {}


def scrape_festival(name: str, url: str, existing: dict | None = None) -> dict | None:
    """Scrape a single festival lineup page.

    Returns a lineup dict or None on failure.
    If the scrape yields no artists but existing data has them, preserves
    the existing data (only updating image_url if a new one was found).
    """
    print(f"\n  Fetching: {url}")
    html_content = _fetch_page(url)
    if not html_content:
        if existing and existing.get("days"):
            print(f"  Fetch failed — keeping existing lineup ({sum(len(d.get('artists', [])) for d in existing['days'])} artists)")
            return existing
        return None

    text, og_image = _extract_text_and_image(html_content)
    artist_days = _extract_artists_from_text(text, festival_name=name)

    # Flatten to get total count
    total = sum(len(v) for v in artist_days.values())

    existing_total = 0
    if existing and existing.get("days"):
        existing_total = sum(len(d.get("artists", [])) for d in existing["days"])

    if total == 0 or total < existing_total // 2:
        # Scrape yielded nothing useful (JS-rendered page, image-based lineup, etc.)
        # Preserve existing data if we have it
        if existing and existing_total > 0:
            reason = "no artists found" if total == 0 else f"only {total} artists (existing has {existing_total})"
            print(f"  Scrape yielded {reason} — keeping existing lineup")
            # Still update image_url if we found one and existing doesn't have one
            if og_image and not existing.get("image_url"):
                existing["image_url"] = og_image
                print(f"  Updated poster image: {og_image}")
            return existing

        print(f"  WARNING: No artists extracted from {url}")
        print("  The page may use JavaScript rendering or image-based lineups.")
        print("  You can manually edit festival_lineups.json to add artists.")
        return {
            "lineup_url": url,
            "image_url": og_image,
            "last_updated": date.today().isoformat(),
            "days": [],
            "extraction_note": "No artists extracted automatically. Edit manually.",
        }

    # Build day structure
    days_list = []
    for day_label, artists in artist_days.items():
        if not artists:
            continue
        days_list.append({
            "label": day_label if day_label != "all" else "Full Lineup",
            "artists": [{"name": a, "headliner": i < 3} for i, a in enumerate(artists)],
        })

    print(f"  Found {total} artists across {len(days_list)} day(s)")
    if og_image:
        print(f"  Poster image: {og_image}")

    return {
        "lineup_url": url,
        "image_url": og_image,
        "last_updated": date.today().isoformat(),
        "days": days_list,
    }


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

    print(f"Fetching lineups for {len(festivals)} festival(s)...")

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

        result = scrape_festival(name, url, existing=existing.get(name))
        if result:
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
        note = data.get("extraction_note", "")
        status = f"{total} artists" if total > 0 else f"MANUAL EDIT NEEDED ({note})"
        print(f"  {name}: {status}")

    if any(
        data.get("extraction_note") for data in updated.values()
    ):
        print("\nTIP: For festivals that need manual editing, update festival_lineups.json")
        print("with the lineup data from the festival's website.")


if __name__ == "__main__":
    main()
