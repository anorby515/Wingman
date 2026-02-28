"""
Wingman Ticketmaster Module
============================
Shared logic for fetching and processing Ticketmaster Discovery API data.
Used by both the local backend (POST /api/refresh) and the GitHub Action
script (scripts/fetch_tm_data.py).

This module NEVER reads or writes cache files — callers handle persistence.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional


# ── Helpers ──────────────────────────────────────────────────────────────────

def name_matches(entity_name: str, attraction_names: list[str]) -> bool:
    """Return True if entity_name has a reasonable TM attraction name match.

    Uses case-insensitive substring matching: either the entity name appears
    inside the attraction name or vice-versa.
    """
    a = entity_name.lower()
    for n in attraction_names:
        nl = n.lower()
        if a in nl or nl in a:
            return True
    return False


def _normalize_festival_name(name: str) -> str:
    """Normalize a festival name for fuzzy matching.

    Strips common suffixes (festival, music festival, fest), removes all
    non-alphanumeric characters, and lowercases.  This lets
    "Stage Coach Festival" match "Stagecoach" on Ticketmaster.
    """
    s = name.lower().strip()
    # Strip common suffixes (order matters: longest first)
    for suffix in ("music festival", "music fest", "festival", "fest"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    # Remove all non-alphanumeric characters
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def festival_name_matches(festival_name: str, event_name: str) -> bool:
    """Return True if a TM event name plausibly matches a tracked festival.

    First tries the normal substring match used for artists/venues.
    Falls back to a normalised comparison that strips spaces, punctuation,
    and common suffixes like "festival" / "fest".
    """
    # Fast path: exact substring match (existing behaviour)
    fl = festival_name.lower()
    el = event_name.lower()
    if fl in el or el in fl:
        return True

    # Normalised match: "Stage Coach Festival" ↔ "Stagecoach"
    fn = _normalize_festival_name(festival_name)
    en = _normalize_festival_name(event_name)
    if fn and en:
        # For very short normalised names (< 4 chars), require exact match
        # to avoid false positives like "acl" matching inside "oraclecloud"
        shorter = min(len(fn), len(en))
        if shorter < 4:
            if fn == en:
                return True
        elif fn in en or en in fn:
            return True

    return False


def format_show_date(local_date: str) -> str:
    """Convert '2026-07-15' to 'Jul 15, 2026'. Returns input on failure."""
    try:
        dt = datetime.strptime(local_date, "%Y-%m-%d")
        return dt.strftime("%b %-d, %Y")
    except Exception:
        return local_date


def _format_city(venue: dict) -> str:
    """Build a display city string from a TM venue object."""
    country = venue.get("country", {}).get("countryCode", "")
    city_name = venue.get("city", {}).get("name", "")
    state_code = venue.get("state", {}).get("stateCode", "")
    if country == "US":
        return f"{city_name}, {state_code}" if state_code else city_name
    elif country == "CA":
        return f"{city_name}, {state_code}, CA" if state_code else f"{city_name}, CA"
    else:
        return f"{city_name}, MX"


def _is_north_america(venue: dict) -> bool:
    """Check if a TM venue is in North America (US, CA, MX)."""
    return venue.get("country", {}).get("countryCode", "") in ("US", "CA", "MX")


def _extract_presales(sales: dict) -> list[dict]:
    """Extract presale windows from a TM event's sales object."""
    presales = []
    for p in sales.get("presales", []):
        presales.append({
            "name": p.get("name", "Presale"),
            "start_datetime": p.get("startDateTime"),
            "end_datetime": p.get("endDateTime"),
        })
    return presales


# ── Data classes for results ─────────────────────────────────────────────────

@dataclass
class RefreshProgress:
    """Tracks progress of a TM refresh operation."""
    running: bool = False
    total_artists: int = 0
    total_venues: int = 0
    total_festivals: int = 0
    artists_processed: int = 0
    venues_processed: int = 0
    festivals_processed: int = 0
    phase: str = ""  # "artists", "venues", "festivals", "done"
    error: Optional[str] = None


@dataclass
class RefreshResult:
    """Complete result from a full TM refresh."""
    artist_shows: dict[str, list[dict]] = field(default_factory=dict)
    venue_shows: dict[str, list[dict]] = field(default_factory=dict)
    festival_shows: dict[str, list[dict]] = field(default_factory=dict)
    artists_not_found: list[str] = field(default_factory=list)
    venues_not_found: list[str] = field(default_factory=list)
    festivals_not_found: list[str] = field(default_factory=list)
    last_refreshed: str = ""


# ── TM API helpers ───────────────────────────────────────────────────────────

def _tm_request(url: str) -> dict:
    """Make a GET request to the TM API. Returns parsed JSON or empty dict."""
    req = urllib.request.Request(url, headers={"User-Agent": "Wingman/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return {}


def _normalize_venue_name(name: str) -> str:
    """Strip punctuation and extra whitespace for fuzzy venue matching."""
    return re.sub(r"[^\w\s]", "", name).lower().strip()


def _parse_city_state(city_str: str) -> tuple[str, str]:
    """Parse 'City, ST' into (city_lower, state_lower)."""
    parts = [p.strip() for p in city_str.split(",")]
    city = parts[0].lower() if parts else ""
    state = parts[1].strip().lower() if len(parts) > 1 else ""
    return city, state


def _venue_in_city(tm_venue: dict, target_city: str) -> bool:
    """Check if a TM venue object is in the target city (city + state match)."""
    if not target_city:
        return False
    city_name, state_code = _parse_city_state(target_city)
    tm_city = tm_venue.get("city", {}).get("name", "").lower()
    tm_state = tm_venue.get("state", {}).get("stateCode", "").lower()
    return bool(city_name and city_name == tm_city
                and (not state_code or state_code == tm_state))


def _venue_in_state(tm_venue: dict, target_city: str) -> bool:
    """Check if a TM venue is in the same state (looser than city match).

    Handles cases like Waukee, IA vs West Des Moines, IA.
    """
    if not target_city:
        return False
    _, state_code = _parse_city_state(target_city)
    if not state_code:
        return False
    tm_state = tm_venue.get("state", {}).get("stateCode", "").lower()
    return state_code == tm_state


def get_tm_venue_id(
    api_key: str, venue_name: str, venue_city: str = "",
) -> str | None:
    """Look up Ticketmaster venue ID for a given venue name.

    Uses a four-pass strategy:
      1. Substring name match (existing behaviour)
      2. Normalised name match (strip punctuation)
      3. City-based fallback (first result in the same city)
      4. State-based fallback (first result in the same state)

    When venue_city is provided, stateCode is also sent to the API
    to help TM return more relevant results.
    """
    search_params: dict[str, str] = {
        "apikey": api_key,
        "keyword": venue_name,
        "size": "10",
    }
    # Add stateCode when available — helps TM narrow venue search
    if venue_city:
        _, state = _parse_city_state(venue_city)
        if state:
            search_params["stateCode"] = state.upper()

    url = (
        "https://app.ticketmaster.com/discovery/v2/venues.json?"
        + urllib.parse.urlencode(search_params)
    )
    data = _tm_request(url)
    venues = data.get("_embedded", {}).get("venues", [])

    # Pass 1: substring match on raw names
    for tv in venues:
        if name_matches(venue_name, [tv.get("name", "")]):
            return tv.get("id")

    # Pass 2: substring match on normalised names (strips punctuation)
    norm = _normalize_venue_name(venue_name)
    for tv in venues:
        tn = _normalize_venue_name(tv.get("name", ""))
        if norm and tn and (norm in tn or tn in norm):
            return tv.get("id")

    # Pass 3: city-based fallback — first venue in the same city
    if venue_city:
        for tv in venues:
            if _venue_in_city(tv, venue_city):
                return tv.get("id")

    # Pass 4: state-based fallback — first venue in the same state
    # Handles cases like Waukee, IA vs West Des Moines, IA
    if venue_city:
        for tv in venues:
            if _venue_in_state(tv, venue_city):
                return tv.get("id")

    return None


def build_show(event: dict, now_utc: datetime) -> dict | None:
    """Extract a normalised show dict from a TM event object.

    Returns None if the event is outside North America or in the past.
    Includes both on-sale and not-yet-on-sale shows.
    """
    venues = event.get("_embedded", {}).get("venues", [])
    if not venues:
        return None
    venue = venues[0]
    if not _is_north_america(venue):
        return None

    local_date = event.get("dates", {}).get("start", {}).get("localDate", "")
    if not local_date:
        return None
    if local_date < now_utc.date().isoformat():
        return None  # Past event

    # Determine on-sale status
    sales = event.get("sales", {})
    public_sale = sales.get("public", {})
    onsale_str = public_sale.get("startDateTime")
    onsale_tbd = public_sale.get("startTBD", False)

    not_yet_on_sale = False
    if onsale_str:
        try:
            onsale_dt = datetime.fromisoformat(onsale_str.replace("Z", "+00:00"))
            not_yet_on_sale = onsale_dt > now_utc
        except Exception:
            pass
    elif onsale_tbd:
        not_yet_on_sale = True

    presales = _extract_presales(sales) if not_yet_on_sale else []

    return {
        "date": format_show_date(local_date),
        "raw_date": local_date,
        "venue": venue.get("name", ""),
        "city": _format_city(venue),
        "not_yet_on_sale": not_yet_on_sale,
        "onsale_datetime": onsale_str if not_yet_on_sale else None,
        "onsale_tbd": onsale_tbd if not_yet_on_sale else False,
        "presales": presales,
        "ticketmaster_url": event.get("url", ""),
        "lat": None,
        "lon": None,
    }


# ── Fetch functions ──────────────────────────────────────────────────────────

def fetch_artist_shows(
    api_key: str,
    artists: dict[str, dict],
    progress: RefreshProgress | None = None,
    geocode_fn: Callable[[str], tuple[float, float] | None] | None = None,
) -> tuple[dict[str, list[dict]], list[str]]:
    """Fetch all upcoming NA shows for each tracked artist.

    Returns (artist_shows, artists_not_found).
    """
    now_utc = datetime.now(timezone.utc)
    results: dict[str, list[dict]] = {}
    not_found: list[str] = []

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
        data = _tm_request(url)

        if not data:
            # Network/API error — skip, don't flag as not found
            if progress:
                progress.artists_processed += 1
            continue

        events = data.get("_embedded", {}).get("events", [])
        matched_any = False
        shows: list[dict] = []

        for event in events:
            attractions = event.get("_embedded", {}).get("attractions", [])
            if attractions and not name_matches(artist_name, [a.get("name", "") for a in attractions]):
                continue

            # Check NA before counting as matched
            tm_venues = event.get("_embedded", {}).get("venues", [])
            if tm_venues and _is_north_america(tm_venues[0]):
                matched_any = True

            show = build_show(event, now_utc)
            if show:
                show["genre"] = artist_info.get("genre", "Other")
                if geocode_fn:
                    coords = geocode_fn(f"{show['venue']}, {show['city']}")
                    if not coords:
                        coords = geocode_fn(show["city"])
                    if coords:
                        show["lat"], show["lon"] = coords
                shows.append(show)

        if shows:
            results[artist_name] = shows
        if not matched_any:
            not_found.append(artist_name)

        if progress:
            progress.artists_processed += 1

    return results, not_found


def fetch_venue_shows(
    api_key: str,
    venues: dict[str, dict],
    progress: RefreshProgress | None = None,
    geocode_fn: Callable[[str], tuple[float, float] | None] | None = None,
) -> tuple[dict[str, list[dict]], list[str]]:
    """Fetch all upcoming NA shows at each tracked venue.

    Returns (venue_shows, venues_not_found).
    """
    now_utc = datetime.now(timezone.utc)
    results: dict[str, list[dict]] = {}
    not_found: list[str] = []

    for venue_name, venue_info in venues.items():
        if venue_info.get("paused", False):
            continue

        venue_city = venue_info.get("city", "")
        venue_id = get_tm_venue_id(api_key, venue_name, venue_city)
        if not venue_id:
            not_found.append(venue_name)
            if progress:
                progress.venues_processed += 1
            continue

        params = urllib.parse.urlencode({
            "apikey": api_key,
            "venueId": venue_id,
            "classificationName": "music",
            "size": "50",
            "sort": "date,asc",
        })
        url = f"https://app.ticketmaster.com/discovery/v2/events.json?{params}"
        data = _tm_request(url)

        shows: list[dict] = []
        for event in data.get("_embedded", {}).get("events", []):
            attractions = event.get("_embedded", {}).get("attractions", [])
            artist = attractions[0].get("name", "") if attractions else event.get("name", "")

            show = build_show(event, now_utc)
            if show:
                show["artist"] = artist
                if geocode_fn:
                    coords = geocode_fn(f"{show['venue']}, {show['city']}")
                    if not coords:
                        coords = geocode_fn(show["city"])
                    if coords:
                        show["lat"], show["lon"] = coords
                shows.append(show)

        if shows:
            results[venue_name] = shows
        else:
            not_found.append(venue_name)

        if progress:
            progress.venues_processed += 1

    return results, not_found


def fetch_festival_shows(
    api_key: str,
    festivals: dict[str, dict],
    progress: RefreshProgress | None = None,
    geocode_fn: Callable[[str], tuple[float, float] | None] | None = None,
) -> tuple[dict[str, list[dict]], list[str]]:
    """Fetch all upcoming festival events on TM.

    Returns (festival_shows, festivals_not_found).
    Uses festival-specific name matching that handles common variations
    (e.g. "Stage Coach Festival" matching "Stagecoach" on TM).
    Deduplicates shows by (date, venue) since TM often lists multiple
    events per festival day.
    """
    now_utc = datetime.now(timezone.utc)
    results: dict[str, list[dict]] = {}
    not_found: list[str] = []

    for festival_name, festival_info in festivals.items():
        if festival_info.get("paused", False):
            continue

        # Try multiple keyword variations to increase hit rate
        keywords_to_try = [festival_name]
        normalized = _normalize_festival_name(festival_name)
        # If normalizing changed the name meaningfully, also search with
        # the raw normalized form (e.g. "Stagecoach" for "Stage Coach Festival")
        if normalized and normalized != re.sub(r"[^a-z0-9]", "", festival_name.lower()):
            keywords_to_try.append(normalized)

        shows: list[dict] = []
        matched_any = False
        seen_date_venue: set[str] = set()

        for keyword in keywords_to_try:
            params = urllib.parse.urlencode({
                "apikey": api_key,
                "keyword": keyword,
                "classificationName": "music",
                "size": "50",
                "sort": "date,asc",
            })
            url = f"https://app.ticketmaster.com/discovery/v2/events.json?{params}"
            data = _tm_request(url)

            for event in data.get("_embedded", {}).get("events", []):
                event_name = event.get("name", "")
                if not festival_name_matches(festival_name, event_name):
                    continue

                tm_venues = event.get("_embedded", {}).get("venues", [])
                if tm_venues and _is_north_america(tm_venues[0]):
                    matched_any = True

                show = build_show(event, now_utc)
                if show:
                    # Deduplicate by date + venue (festivals often have
                    # multiple TM events per day for different stages/tickets)
                    dedup_key = f"{show['date']}|{show['venue']}"
                    if dedup_key in seen_date_venue:
                        continue
                    seen_date_venue.add(dedup_key)

                    show["event_name"] = event_name
                    if geocode_fn:
                        coords = geocode_fn(f"{show['venue']}, {show['city']}")
                        if not coords:
                            coords = geocode_fn(show["city"])
                        if coords:
                            show["lat"], show["lon"] = coords
                    shows.append(show)

            # If we found matches with the first keyword, skip the rest
            if matched_any:
                break

        if shows:
            results[festival_name] = shows
        if not matched_any:
            not_found.append(festival_name)

        if progress:
            progress.festivals_processed += 1

    return results, not_found


def run_full_refresh(
    api_key: str,
    artists: dict[str, dict],
    venues: dict[str, dict],
    festivals: dict[str, dict],
    progress: RefreshProgress | None = None,
    geocode_fn: Callable[[str], tuple[float, float] | None] | None = None,
) -> RefreshResult:
    """Run a complete TM refresh for all entities.

    This is the main entry point used by both the local backend and the
    GitHub Action script.
    """
    if progress:
        progress.running = True
        progress.total_artists = sum(1 for a in artists.values() if not a.get("paused", False))
        progress.total_venues = sum(1 for v in venues.values() if not v.get("paused", False))
        progress.total_festivals = sum(1 for f in festivals.values() if not f.get("paused", False))

    result = RefreshResult()

    try:
        # Phase 1: Artists
        if progress:
            progress.phase = "artists"
        result.artist_shows, result.artists_not_found = fetch_artist_shows(
            api_key, artists, progress, geocode_fn
        )

        # Phase 2: Venues
        if progress:
            progress.phase = "venues"
        result.venue_shows, result.venues_not_found = fetch_venue_shows(
            api_key, venues, progress, geocode_fn
        )

        # Phase 3: Festivals
        if progress:
            progress.phase = "festivals"
        result.festival_shows, result.festivals_not_found = fetch_festival_shows(
            api_key, festivals, progress, geocode_fn
        )

        result.last_refreshed = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        if progress:
            progress.error = str(e)
        raise
    finally:
        if progress:
            progress.phase = "done"
            progress.running = False

    return result


# ── Notification trigger detection ───────────────────────────────────────────

def detect_triggers(
    new_result: RefreshResult,
    old_cache: dict | None,
) -> list[dict]:
    """Compare new refresh result against previous cache to detect notification triggers.

    Returns a list of trigger dicts with type, artist, date, venue, city, etc.
    """
    triggers: list[dict] = []
    now_utc = datetime.now(timezone.utc)

    # Build set of old event keys for comparison
    old_event_keys: set[str] = set()
    if old_cache:
        for artist, shows in old_cache.get("artist_shows", {}).items():
            for show in shows:
                key = f"{artist}|{show.get('date', '')}|{show.get('venue', '')}"
                old_event_keys.add(key)

    # Check for new events
    for artist, shows in new_result.artist_shows.items():
        for show in shows:
            key = f"{artist}|{show.get('date', '')}|{show.get('venue', '')}"
            if key not in old_event_keys:
                triggers.append({
                    "type": "new_event",
                    "artist": artist,
                    "date": show.get("date", ""),
                    "venue": show.get("venue", ""),
                    "city": show.get("city", ""),
                })

            # Check on-sale-soon triggers
            onsale_str = show.get("onsale_datetime")
            if onsale_str:
                try:
                    onsale_dt = datetime.fromisoformat(onsale_str.replace("Z", "+00:00"))
                    hours_until = (onsale_dt - now_utc).total_seconds() / 3600

                    if 0 < hours_until <= 48:
                        triggers.append({
                            "type": "onsale_48_hours",
                            "artist": artist,
                            "date": show.get("date", ""),
                            "venue": show.get("venue", ""),
                            "city": show.get("city", ""),
                            "onsale_datetime": onsale_str,
                        })
                    elif 48 < hours_until <= 168:  # 7 days
                        triggers.append({
                            "type": "onsale_7_days",
                            "artist": artist,
                            "date": show.get("date", ""),
                            "venue": show.get("venue", ""),
                            "city": show.get("city", ""),
                            "onsale_datetime": onsale_str,
                        })
                except Exception:
                    pass

    return triggers
