#!/usr/bin/env python3
"""
Wingman SMS Notification Script
================================
Compares docs/summary.json against docs/notification_baseline.json to detect:
  - New artist shows announced
  - New venue events
  - Shows with on-sale date within 48 hours

Sends an SMS via Twilio when changes are found, then updates the baseline.

Designed to run as a GitHub Action job, gated to schedule-only triggers.

Usage:
  python scripts/notify_changes.py

Environment variables (all required):
  TWILIO_ACCOUNT_SID  — Twilio account identifier
  TWILIO_AUTH_TOKEN   — Twilio API auth token
  TWILIO_FROM_NUMBER  — Sender phone number (e.g. +15551234567)
  TWILIO_TO_NUMBER    — Recipient phone number (e.g. +15559876543)
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request
from base64 import b64encode
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUMMARY_PATH = ROOT / "docs" / "summary.json"
BASELINE_PATH = ROOT / "docs" / "notification_baseline.json"

# Twilio long-SMS limit (concatenated segments, up to ~1600 chars reliably)
SMS_MAX_CHARS = 1500


def parse_show_date(date_str: str) -> datetime | None:
    """Parse display date like 'Mar 21, 2026' into a datetime."""
    try:
        return datetime.strptime(date_str, "%b %d, %Y")
    except (ValueError, TypeError):
        return None


def is_future_show(date_str: str, today: datetime) -> bool:
    """Return True if the show date is today or later."""
    dt = parse_show_date(date_str)
    if dt is None:
        return True  # Can't parse — keep it to be safe
    return dt.date() >= today.date()


def build_show_keys(summary: dict, today: datetime) -> tuple[set[str], set[str]]:
    """Extract artist and venue show keys from summary, filtering out past shows."""
    artist_keys: set[str] = set()
    for artist, shows in summary.get("artist_shows", {}).items():
        for show in shows:
            if is_future_show(show.get("date", ""), today):
                key = f"{artist}|{show.get('date', '')}|{show.get('venue', '')}"
                artist_keys.add(key)

    venue_keys: set[str] = set()
    for venue, shows in summary.get("venue_shows", {}).items():
        for show in shows:
            if is_future_show(show.get("date", ""), today):
                key = f"{venue}|{show.get('date', '')}|{show.get('artist', '')}"
                venue_keys.add(key)

    return artist_keys, venue_keys


def find_onsale_imminent(summary: dict, now: datetime) -> list[dict]:
    """Find coming_soon shows with on-sale within 48 hours."""
    imminent: list[dict] = []
    cutoff = now + timedelta(hours=48)

    for show in summary.get("coming_soon", []):
        onsale = show.get("onsale_datetime")
        if not onsale or show.get("onsale_tbd"):
            continue
        try:
            onsale_dt = datetime.fromisoformat(onsale.replace("Z", "+00:00"))
            if now <= onsale_dt <= cutoff:
                imminent.append(show)
        except (ValueError, TypeError):
            continue

    return imminent


def key_to_display(key: str, key_type: str) -> str:
    """Convert a pipe-delimited key back to a readable line."""
    parts = key.split("|", 2)
    if len(parts) != 3:
        return key

    if key_type == "artist":
        artist, date, venue = parts
        return f"{artist} @ {venue} — {date}"
    else:
        venue, date, artist = parts
        return f"{artist} @ {venue} — {date}"


def format_onsale_time(iso_str: str) -> str:
    """Format an ISO datetime to a readable on-sale time."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        # Convert to US Central (UTC-6 standard, UTC-5 daylight)
        # Use a simple offset — good enough for display
        central = dt + timedelta(hours=-6)
        return central.strftime("%b %d, %-I:%M %p") + " CT"
    except (ValueError, TypeError):
        return iso_str


def format_sms(
    new_artist_shows: list[str],
    new_venue_events: list[str],
    onsale_imminent: list[dict],
    today: datetime,
) -> str:
    """Format the SMS body, truncating if necessary."""
    date_str = today.strftime("%b %d")
    lines: list[str] = [f"Wingman — {date_str}", ""]

    sections: list[tuple[str, list[str]]] = []

    if new_artist_shows:
        items = [f"• {key_to_display(k, 'artist')}" for k in sorted(new_artist_shows)]
        sections.append(("NEW SHOWS:", items))

    if new_venue_events:
        items = [f"• {key_to_display(k, 'venue')}" for k in sorted(new_venue_events)]
        sections.append(("NEW AT VENUES:", items))

    if onsale_imminent:
        items = []
        for show in sorted(onsale_imminent, key=lambda s: s.get("onsale_datetime", "")):
            artist = show.get("artist", "Unknown")
            venue = show.get("venue", "")
            date = show.get("date", "")
            onsale = format_onsale_time(show["onsale_datetime"])
            items.append(f"• {artist} @ {venue} — {date}")
            items.append(f"  On sale: {onsale}")
        sections.append(("ON SALE SOON:", items))

    # Build message, truncating sections if too long
    for header, items in sections:
        lines.append(header)
        for item in items:
            candidate = "\n".join(lines + [item])
            if len(candidate) > SMS_MAX_CHARS - 50:  # Reserve space for overflow note
                remaining = sum(len(sect_items) for _, sect_items in sections) - len(
                    [l for l in lines if l.startswith("•")]
                )
                lines.append(f"(+{remaining} more)")
                return "\n".join(lines)
            lines.append(item)
        lines.append("")

    return "\n".join(lines).strip()


def send_twilio_sms(body: str) -> bool:
    """Send an SMS via Twilio REST API (no SDK dependency)."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_number = os.environ.get("TWILIO_FROM_NUMBER", "")
    to_number = os.environ.get("TWILIO_TO_NUMBER", "")

    if not all([account_sid, auth_token, from_number, to_number]):
        print("Error: Missing Twilio environment variables", file=sys.stderr)
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    data = urllib.parse.urlencode({
        "To": to_number,
        "From": from_number,
        "Body": body,
    }).encode("utf-8")

    credentials = b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print(f"SMS sent: SID={result.get('sid', 'unknown')}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"Twilio API error {e.code}: {error_body}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Failed to send SMS: {e}", file=sys.stderr)
        return False


def save_baseline(artist_keys: set[str], venue_keys: set[str]) -> None:
    """Write the notification baseline file."""
    baseline = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "artist_show_keys": sorted(artist_keys),
        "venue_show_keys": sorted(venue_keys),
    }
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2) + "\n")
    print(f"Updated baseline: {len(artist_keys)} artist keys, {len(venue_keys)} venue keys")


def main() -> None:
    now = datetime.now(timezone.utc)
    today = now

    # Load current summary
    if not SUMMARY_PATH.exists():
        print("No summary.json found — skipping notifications")
        return

    summary = json.loads(SUMMARY_PATH.read_text())

    # Build current show keys (future only)
    current_artist_keys, current_venue_keys = build_show_keys(summary, today)

    # Load baseline (previous snapshot)
    prev_artist_keys: set[str] = set()
    prev_venue_keys: set[str] = set()

    if BASELINE_PATH.exists():
        try:
            baseline = json.loads(BASELINE_PATH.read_text())
            prev_artist_keys = set(baseline.get("artist_show_keys", []))
            prev_venue_keys = set(baseline.get("venue_show_keys", []))
        except Exception as e:
            print(f"Warning: could not load baseline: {e}")

    # Also filter baseline keys to future-only (drop shows that are now in the past)
    prev_artist_keys = {
        k for k in prev_artist_keys
        if is_future_show(k.split("|", 2)[1] if "|" in k else "", today)
    }
    prev_venue_keys = {
        k for k in prev_venue_keys
        if is_future_show(k.split("|", 2)[1] if "|" in k else "", today)
    }

    # Detect changes
    new_artist_shows = current_artist_keys - prev_artist_keys
    new_venue_events = current_venue_keys - prev_venue_keys
    onsale_imminent = find_onsale_imminent(summary, now)

    total_changes = len(new_artist_shows) + len(new_venue_events) + len(onsale_imminent)

    print(f"Changes detected: {len(new_artist_shows)} new artist shows, "
          f"{len(new_venue_events)} new venue events, "
          f"{len(onsale_imminent)} on-sale imminent")

    if total_changes == 0:
        print("No changes — skipping SMS")
        # Still update baseline (keys may have shifted due to past-show filtering)
        save_baseline(current_artist_keys, current_venue_keys)
        return

    # Format and send SMS
    sms_body = format_sms(
        sorted(new_artist_shows),
        sorted(new_venue_events),
        onsale_imminent,
        today,
    )
    print(f"\n--- SMS Preview ({len(sms_body)} chars) ---")
    print(sms_body)
    print("---")

    if send_twilio_sms(sms_body):
        # Update baseline only after successful send
        save_baseline(current_artist_keys, current_venue_keys)
    else:
        print("SMS failed — baseline NOT updated (will retry next run)")
        sys.exit(1)


if __name__ == "__main__":
    main()
