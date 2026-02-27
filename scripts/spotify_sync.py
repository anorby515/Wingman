#!/usr/bin/env python3
"""
Wingman Spotify Sync
====================
Interactive 3-phase Spotify sync. Run from the repo root:

    python3 scripts/spotify_sync.py

Phase 1 — Spotify follows not in Wingman (add artists)
Phase 2 — Wingman artists not followed on Spotify (batch follow)
Phase 3 — Listening history suggestions (discover new artists)
"""

from __future__ import annotations

import json
import sys
import time
import webbrowser
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from backend.spotify import (
    get_valid_access_token,
    spotify_get,
    spotify_put,
    TOKENS_FILE,
)

CONFIG_FILE    = REPO / "wingman_config.json"
DISMISSED_FILE = REPO / "dismissed_suggestions.json"
FLAGGED_FILE   = REPO / "flagged_items.json"

# ── Genre mapping ─────────────────────────────────────────────────────────────

GENRE_MAP = [
    (["country", "americana", "bluegrass", "western"], "Country / Americana"),
    (["folk", "singer-songwriter", "acoustic"], "Folk / Singer-Songwriter"),
    (["indie", "alternative", "alt-rock", "college"], "Indie / Alt-Rock"),
    (["electronic", "art rock", "experimental", "synth"], "Electronic / Art-Rock"),
    (["pop"], "Pop"),
    (["hip hop", "rap", "r&b", "soul"], "Hip-Hop / R&B"),
    (["rock", "classic rock", "hard rock"], "Rock"),
    (["jazz", "blues"], "Jazz / Blues"),
]

def map_genre(spotify_genres: list[str]) -> str:
    combined = " ".join(spotify_genres).lower()
    for keywords, label in GENRE_MAP:
        if any(k in combined for k in keywords):
            return label
    return "Other"


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())

def write_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    # Also update tracked.json
    tracked = {
        "center_city": cfg.get("center_city", ""),
        "artists": {
            name: {"url": info.get("url",""), "genre": info.get("genre","Other"), "paused": info.get("paused", False)}
            for name, info in cfg.get("artists", {}).items()
        },
        "venues": {
            name: {"url": info.get("url",""), "city": info.get("city",""), "is_local": info.get("is_local", False), "paused": info.get("paused", False)}
            for name, info in cfg.get("venues", {}).items()
        },
        "festivals": {
            name: {"url": info.get("url",""), "paused": info.get("paused", False)}
            for name, info in cfg.get("festivals", {}).items()
        },
    }
    (REPO / "tracked.json").write_text(json.dumps(tracked, indent=2) + "\n")

def read_dismissed() -> dict:
    if not DISMISSED_FILE.exists():
        return {}
    try:
        return json.loads(DISMISSED_FILE.read_text())
    except Exception:
        return {}

def write_dismissed(data: dict) -> None:
    DISMISSED_FILE.write_text(json.dumps(data, indent=2))

def read_flagged() -> list:
    if not FLAGGED_FILE.exists():
        return []
    try:
        return json.loads(FLAGGED_FILE.read_text())
    except Exception:
        return []

def write_flagged(items: list) -> None:
    FLAGGED_FILE.write_text(json.dumps(items, indent=2))

def dismiss_artist(name: str, source: str, reason: str = "user declined") -> None:
    today = date.today()
    data = read_dismissed()
    data[name] = {
        "dismissed_at": today.isoformat(),
        "resurface_after": (today + timedelta(days=183)).isoformat(),
        "reason": reason,
        "source": source,
    }
    write_dismissed(data)

def prompt(msg: str) -> str:
    try:
        return input(msg).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n\nSync interrupted.")
        sys.exit(0)

def hr() -> None:
    print("\n" + "─" * 60)

def paginate_following(token: str) -> list[dict]:
    """Fetch all followed artists, handling pagination."""
    import urllib.error
    from urllib.parse import urlparse, parse_qs
    artists = []
    url = "/me/following"
    params: dict | None = {"type": "artist", "limit": 50}
    while True:
        try:
            data = spotify_get(url, token, params)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"\n  ⚠ Spotify API error {e.code} on {url}: {body}")
            return artists
        page = data.get("artists", {})
        artists.extend(page.get("items", []))
        next_url = page.get("next")
        if not next_url:
            break
        # Extract only the path (strip /v1 prefix since API_BASE already has it)
        parsed = urlparse(next_url)
        path = parsed.path
        if path.startswith("/v1"):
            path = path[3:]
        url = path
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        time.sleep(0.1)
    return artists


# ── Phase 1 ───────────────────────────────────────────────────────────────────

def phase1(token: str, cfg: dict) -> tuple[int, int]:
    """Spotify follows → Wingman. Returns (added, dismissed)."""
    hr()
    print("PHASE 1 — Spotify follows not in Wingman")
    print("Fetching your Spotify follows...")

    follows = paginate_following(token)
    wingman_lower = {k.lower(): k for k in cfg.get("artists", {}).keys()}
    new_artists = [a for a in follows if a["name"].lower() not in wingman_lower]

    if not new_artists:
        print("✓ All your Spotify follows are already in Wingman.")
        return 0, 0

    print(f"\nYou follow {len(new_artists)} artists on Spotify that aren't in Wingman.")

    added = 0
    dismissed = 0

    for i, artist in enumerate(new_artists, 1):
        hr()
        name = artist["name"]
        genres = artist.get("genres", [])
        genre_label = map_genre(genres)
        spotify_url = artist.get("external_urls", {}).get("spotify", "")
        print(f"[{i}/{len(new_artists)}] ➕ {name}")
        print(f"  Genres: {', '.join(genres[:3]) if genres else 'unknown'} → {genre_label}")
        print(f"  Spotify: {spotify_url}")

        ans = prompt("\nAdd to Wingman? [y]es / [n]o / [d]ismiss 6mo / [s]kip all: ")

        if ans in ("s", "skip"):
            print("Skipping remaining Phase 1 artists.")
            break
        elif ans in ("y", "yes"):
            # Search for tour URL
            print(f"\n  Searching for {name}'s official tour page...")
            tour_url = find_tour_url(name)
            print(f"  → {tour_url}")
            cfg.setdefault("artists", {})[name] = {
                "url": tour_url,
                "genre": genre_label,
                "paused": False,
            }
            write_config(cfg)
            print(f"  ✓ Added {name}")
            added += 1
        elif ans in ("d", "dismiss"):
            dismiss_artist(name, "spotify_follows")
            print(f"  Dismissed {name} for 6 months.")
            dismissed += 1
        else:
            print("  Skipped.")

    return added, dismissed


def find_tour_url(artist_name: str) -> str:
    """Search for artist's official tour page. Opens browser for user to confirm."""
    from urllib.parse import quote
    query = f"{artist_name} official tour dates"
    search_url = f"https://www.google.com/search?q={quote(query)}"

    print(f"\n  Opening Google search for: {query}")
    print(f"  Look for the artist's own website (not Ticketmaster/Songkick).")
    print(f"  Prefer a /tour or /shows page. Copy the URL and paste it below.")
    webbrowser.open(search_url)
    time.sleep(1)

    url = input("  Tour URL (or press Enter to skip): ").strip()
    return url if url else ""


# ── Phase 2 ───────────────────────────────────────────────────────────────────

def phase2(token: str, cfg: dict) -> int:
    """Wingman artists → Spotify follows. Returns count followed."""
    hr()
    print("PHASE 2 — Wingman artists not followed on Spotify")
    print("Searching Spotify for each Wingman artist...")

    follows = paginate_following(token)
    followed_lower = {a["name"].lower() for a in follows}

    to_follow = []
    not_found = []
    flagged = read_flagged()

    artists = {k: v for k, v in cfg.get("artists", {}).items() if not v.get("paused")}

    for name in artists:
        if name.lower() in followed_lower:
            continue
        # Search Spotify
        results = spotify_get("/search", token, {"q": name, "type": "artist", "limit": 5})
        items = results.get("artists", {}).get("items", [])
        match = None
        for item in items:
            if item["name"].lower() == name.lower():
                match = item
                break
        if not match and items:
            # Accept close match if popularity > 10
            for item in items:
                if name.lower() in item["name"].lower() or item["name"].lower() in name.lower():
                    if item.get("popularity", 0) > 10:
                        match = item
                        break
        if match:
            to_follow.append({
                "name": name,
                "spotify_id": match["id"],
                "spotify_url": match.get("external_urls", {}).get("spotify", ""),
                "popularity": match.get("popularity", 0),
            })
        else:
            not_found.append(name)
            flagged.append({"type": "spotify_not_found", "name": name, "note": "Not found on Spotify"})

    if not_found:
        write_flagged(flagged)
        print(f"\n  ⚠ {len(not_found)} artists not found on Spotify (added to Flagged Items):")
        for n in not_found:
            print(f"    • {n}")

    if not to_follow:
        print("\n✓ You already follow all Wingman artists on Spotify.")
        return 0

    hr()
    print(f"\nWingman artists you're not following on Spotify ({len(to_follow)}):\n")
    for i, a in enumerate(to_follow, 1):
        print(f"  {i:2}. {a['name']:35} {a['spotify_url']}")

    ans = prompt("\nFollow which ones? [all] / numbers like 1,3,5 / [none]: ")

    if ans in ("none", "n", ""):
        print("No artists followed.")
        return 0

    if ans in ("all", "a"):
        selected = to_follow
    else:
        indices = []
        for part in ans.replace(",", " ").split():
            try:
                indices.append(int(part) - 1)
            except ValueError:
                pass
        selected = [to_follow[i] for i in indices if 0 <= i < len(to_follow)]

    # Spotify PUT allows up to 50 IDs at once
    ids = [a["spotify_id"] for a in selected]
    for chunk_start in range(0, len(ids), 50):
        chunk = ids[chunk_start:chunk_start+50]
        spotify_put("/me/following", token, {"type": "artist", "ids": ",".join(chunk)})
        time.sleep(0.2)

    print(f"\n✓ Followed {len(selected)} artists on Spotify:")
    for a in selected:
        print(f"  • {a['name']}")
    return len(selected)


# ── Phase 3 ───────────────────────────────────────────────────────────────────

def phase3(token: str, cfg: dict) -> tuple[int, int]:
    """Listening history suggestions. Returns (added, dismissed)."""
    hr()
    print("PHASE 3 — Listening history suggestions")
    print("Fetching your listening history...")

    follows = paginate_following(token)
    followed_lower = {a["name"].lower() for a in follows}
    wingman_lower = {k.lower() for k in cfg.get("artists", {}).keys()}
    dismissed = read_dismissed()
    today_str = date.today().isoformat()

    # Gather candidates with source tracking
    candidates: dict[str, dict] = {}

    for time_range in ("short_term", "medium_term", "long_term"):
        label = {"short_term": "recent (4 weeks)", "medium_term": "medium (6 months)", "long_term": "all-time"}[time_range]
        data = spotify_get("/me/top/artists", token, {"time_range": time_range, "limit": 50})
        for item in data.get("items", []):
            name = item["name"]
            if name.lower() in wingman_lower or name.lower() in followed_lower:
                continue
            if name in dismissed and dismissed[name]["resurface_after"] > today_str:
                continue
            if name not in candidates:
                candidates[name] = {"artist": item, "sources": []}
            candidates[name]["sources"].append(f"top artists ({label})")

    # Recently played
    data = spotify_get("/me/player/recently-played", token, {"limit": 50})
    seen_recent = set()
    for item in data.get("items", []):
        artist = item.get("track", {}).get("artists", [{}])[0]
        name = artist.get("name", "")
        if not name or name in seen_recent:
            continue
        seen_recent.add(name)
        if name.lower() in wingman_lower or name.lower() in followed_lower:
            continue
        if name in dismissed and dismissed[name]["resurface_after"] > today_str:
            continue
        if name not in candidates:
            # Need full artist data — search for it
            results = spotify_get("/search", token, {"q": name, "type": "artist", "limit": 1})
            items = results.get("artists", {}).get("items", [])
            if items:
                candidates[name] = {"artist": items[0], "sources": []}
        if name in candidates:
            candidates[name]["sources"].append("recently played")

    if not candidates:
        print("\n✓ No new suggestions from your listening history.")
        return 0, 0

    # Sort by number of sources (most relevant first)
    sorted_candidates = sorted(candidates.items(), key=lambda x: len(x[1]["sources"]), reverse=True)

    print(f"\nFound {len(sorted_candidates)} artists from your listening history.\n")

    added = 0
    dismissed_count = 0

    for name, info in sorted_candidates:
        artist = info["artist"]
        sources = info["sources"]
        genres = artist.get("genres", [])
        genre_label = map_genre(genres)
        spotify_url = artist.get("external_urls", {}).get("spotify", "")

        hr()
        print(f"🎵 {name}")
        print(f"  Why: {', '.join(sources)}")
        print(f"  Genres: {', '.join(genres[:3]) if genres else 'unknown'} → {genre_label}")
        print(f"  Spotify: {spotify_url}")

        ans = prompt("\nTrack in Wingman + follow on Spotify? [y]es / [n]o / [d]ismiss 6mo / [s]kip all: ")

        if ans in ("s", "skip"):
            print("Skipping remaining suggestions.")
            break
        elif ans in ("y", "yes"):
            print(f"\n  Searching for {name}'s official tour page...")
            tour_url = find_tour_url(name)
            cfg.setdefault("artists", {})[name] = {
                "url": tour_url,
                "genre": genre_label,
                "paused": False,
            }
            write_config(cfg)
            # Follow on Spotify
            spotify_put("/me/following", token, {"type": "artist", "ids": artist["id"]})
            print(f"  ✓ Added to Wingman + followed on Spotify")
            added += 1
        elif ans in ("d", "dismiss"):
            dismiss_artist(name, sources[0] if sources else "listening_history")
            print(f"  Dismissed {name} for 6 months.")
            dismissed_count += 1
        else:
            print("  Skipped.")

    return added, dismissed_count


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  WINGMAN — Spotify Sync")
    print("=" * 60)

    # Pre-flight
    if not TOKENS_FILE.exists():
        print("\n✗ Not connected to Spotify.")
        print("  Go to Settings → Spotify → Connect Spotify first.")
        sys.exit(1)

    cfg = read_config()
    client_id = cfg.get("spotify_client_id")
    client_secret = cfg.get("spotify_client_secret")
    if not client_id or not client_secret:
        print("\n✗ Spotify credentials not configured.")
        print("  Go to Settings → Spotify and save your Client ID and Secret.")
        sys.exit(1)

    token = get_valid_access_token(client_id, client_secret)
    if not token:
        print("\n✗ Could not get Spotify access token.")
        print("  Try reconnecting in Settings → Spotify.")
        sys.exit(1)

    me = spotify_get("/me", token)
    display_name = me.get("display_name") or me.get("id")
    print(f"\n✓ Connected as: {display_name}")
    print(f"  Wingman artists: {len(cfg.get('artists', {}))}")

    # Run phases
    p1_added, p1_dismissed = phase1(token, cfg)
    cfg = read_config()  # Reload in case Phase 1 wrote changes

    token = get_valid_access_token(client_id, client_secret)  # Refresh token between phases
    p2_followed = phase2(token, cfg)
    cfg = read_config()

    token = get_valid_access_token(client_id, client_secret)
    p3_added, p3_dismissed = phase3(token, cfg)

    # Summary
    hr()
    print("\n🎉 Spotify sync complete!\n")
    print(f"  Phase 1 — Added to Wingman:      {p1_added} artists")
    print(f"  Phase 2 — Followed on Spotify:   {p2_followed} artists")
    print(f"  Phase 3 — New suggestions added: {p3_added} artists")
    dismissed_total = p1_dismissed + p3_dismissed
    if dismissed_total:
        print(f"  Dismissed (resurface in 6mo):    {dismissed_total} artists")
    flagged = read_flagged()
    spotify_flags = [f for f in flagged if f.get("type") == "spotify_not_found"]
    if spotify_flags:
        print(f"  Not found on Spotify:            {len(spotify_flags)} artists")
        print("  → View in Configure → Flagged Items")
    print()


if __name__ == "__main__":
    main()
