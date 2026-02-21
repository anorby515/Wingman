#!/usr/bin/env python3
"""
Concert Weekly Watcher
======================
Scrapes artist tour pages and venue calendars, diffs against last week's
state, and produces a PDF showing only what changed.

Run manually:  python concert_weekly.py
Scheduled:     automatically via Claude schedule skill (weekly, Saturdays 9 AM)

State file:    concert_state.json  (same directory as this script)
Output PDF:    Concert_Changes_YYYY-MM-DD.pdf  (same directory)
"""

import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

# ── Dependencies ────────────────────────────────────────────────────────────
def install(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg,
                           "--break-system-packages", "-q"])

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    install("playwright")
    from playwright.sync_api import sync_playwright

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    HRFlowable, KeepTogether)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
except ImportError:
    install("reportlab")
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    HRFlowable, KeepTogether)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER

# ── Configuration ──────────────────────────────────────────────────────────
HERE = Path(__file__).parent
STATE_FILE = HERE / "concert_state.json"

CENTER_CITY = "Des Moines, IA"
RADIUS_MILES = 200

# Cities within ~200 direct-line miles of Des Moines, IA
CITIES_IN_RANGE = [
    "Des Moines", "Ames", "Iowa City", "Cedar Rapids", "Davenport",
    "Sioux City", "Waterloo", "Dubuque",           # Iowa
    "Omaha", "Lincoln",                             # Nebraska
    "Kansas City", "St. Joseph", "Columbia",        # Missouri (closer ones)
]
STATES_IN_RANGE = ["IA", "NE"]   # whole-state shortlist for quick checks

ARTIST_URLS = {
    # ── Country / Americana ────────────────────────────────────────────────
    "Luke Combs":          "https://www.lukecombs.com/tour-dates/",
    "Morgan Wallen":       "https://morganwallen.com/",
    "Eric Church":         "https://www.ericchurch.com/tours",
    "Zach Bryan":          "https://www.zachbryan.com/tour",
    "Zac Brown Band":      "https://zacbrownband.com/pages/tour",
    "Jason Isbell":        "https://www.jasonisbell.com/shows",
    "Sturgill Simpson":    "https://sturgillsimpson.com/",
    "CAAMP":               "https://www.caamptheband.com/caamp-tour-dates",
    "Tyler Childers":      "https://tylerchildersmusic.com/pages/tour-dates",
    "Chris Stapleton":     "https://chrisstapleton.com/",
    "Dierks Bentley":      "https://dierks.com/",
    "Lainey Wilson":       "https://www.laineywilson.com/",
    "Colter Wall":         "http://www.ColterWall.com",
    "The Red Clay Strays": "https://musicrow.com/2026/02/the-red-clay-strays-add-additional-tour-dates/",
    "Billy Strings":       "https://www.billystrings.com/",
    "Wyatt Flores":        "https://www.wyattfloresmusic.com/",
    "Dylan Gossett":       "https://www.dylangossett.com/",
    "Johnny Blue Skies":   "https://liveforlivemusic.com/news/johnny-blue-skies-sturgill-simpson-refutes-dan-auerbach/",
    # ── Indie / Alt-Rock ───────────────────────────────────────────────────
    "The Lumineers":       "https://www.thelumineers.com/tour",
    "American Mary":       "https://www.americanmary.com/#tour",
    "Bon Iver":            "https://boniver.org/tour/",
    "The War on Drugs":    "https://www.thewarondrugs.net/tour",
    "Vampire Weekend":     "https://www.vampireweekend.com/#tour",
    "Phoebe Bridgers":     "https://phoebefuckingbridgers.com/",
    "Rostam":              "https://officialrostam.com/#dates",
    "Pearl Jam":           "https://pearljam.com/tour",
    "The Black Keys":      "https://www.theblackkeys.com/",
    "Foo Fighters":        "https://www.foofighters.com/tour-dates",
    "Jack White":          "https://jackwhiteiii.com/tour-dates/",
    "LCD Soundsystem":     "https://lcdsoundsystem.com/",
    "The Strokes":         "https://www.thestrokes.com/",
    "The 1975":            "https://the1975.com/",
    "The Smile":           "https://www.thesmiletheband.com/",
    "Noah Kahan":          "https://noahkahan.com/",
    "Mt. Joy":             "https://www.mtjoyband.com/",
    "Lord Huron":          "https://www.lordhuron.com/",
    "Royel Otis":          "https://www.royelotis.com/",
    # ── Electronic / Art-rock ─────────────────────────────────────────────
    "Massive Attack":      "https://www.massiveattack.co.uk/",
    "Radiohead":           "https://www.radiohead.com/",
    "The XX":              "https://thexx.info/",
    "Alabama Shakes":      "https://www.alabamashakes.com/",
    "Tame Impala":         "https://interscope.com/products/tame-impala-the-complete-vinyl-collection",
}

VENUE_URLS = {
    # key: (location, is_local, url)
    # is_local=True  → within 200-mile radius (Des Moines metro)
    # is_local=False → travel venue (tracked for artist cross-reference only)

    # ── Local venues (Des Moines area) ────────────────────────────────────
    "Hoyt Sherman Place":     ("Des Moines, IA",  True,  "https://hoytsherman.org/events/"),
    "First Fleet Concerts":   ("Des Moines, IA",  True,  "https://www.firstfleetconcerts.com/events"),
    # ↑ Covers Vibrant Music Hall, Wooly's, and Val Air Ballroom
    "Iowa Events Center":     ("Des Moines, IA",  True,  "https://www.iowaeventscenter.com/events"),

    # ── Travel venues ─────────────────────────────────────────────────────
    "Starlight Theatre":      ("Kansas City, MO", False, "https://www.kcstarlight.com/events"),
    "The Waiting Room":       ("Omaha, NE",        False, "https://waitingroomlounge.com/events/"),
    "Ryman Auditorium":       ("Nashville, TN",    False, "https://www.ryman.com/events"),
    "ACL Live":               ("Austin, TX",       False, "https://www.acllive.com/calendar"),
    "The Salt Shed":          ("Chicago, IL",      False, "https://www.saltshedchicago.com/home#shows"),
}

TRACKED_ARTISTS = set(ARTIST_URLS.keys())

# ── Helpers ────────────────────────────────────────────────────────────────
def city_in_range(text: str) -> bool:
    """Return True if text contains a city/state within the 200-mile radius."""
    t = text.upper()
    for city in CITIES_IN_RANGE:
        if city.upper() in t:
            return True
    for st in STATES_IN_RANGE:
        # Match ", IA" / "- NE" etc.
        if re.search(r'\b' + st + r'\b', t):
            return True
    return False


def extract_jsonld_events(page_text: str) -> list[dict]:
    """Pull schema.org MusicEvent objects from raw page text (JSON-LD)."""
    events = []
    for m in re.finditer(r'(\[?\s*\{[^<]{20,}\}[\]\s]*)', page_text, re.DOTALL):
        chunk = m.group(1).strip()
        try:
            data = json.loads(chunk)
            if not isinstance(data, list):
                data = [data]
            for item in data:
                if isinstance(item, dict) and item.get("@type") in ("MusicEvent", "Event"):
                    loc = item.get("location", {})
                    addr = loc.get("address", {})
                    city_state = (addr.get("addressLocality", "") + " " +
                                  addr.get("addressRegion", "")).strip()
                    events.append({
                        "date":  item.get("startDate", "")[:10],
                        "venue": loc.get("name", ""),
                        "city":  city_state,
                        "name":  item.get("name", ""),
                    })
        except Exception:
            pass
    return events


def fetch_page(browser, url: str, wait: int = 3) -> str:
    """Load a URL with a headless browser and return innerText."""
    try:
        page = browser.new_page()
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        time.sleep(wait)
        text = page.inner_text("body")
        html = page.content()
        page.close()
        return text + "\n\n" + html
    except Exception as e:
        print(f"  ⚠  Failed to load {url}: {e}")
        return ""


def normalise_show(date_str: str, venue: str, city: str, status: str = "on_sale") -> dict:
    return {"date": date_str.strip(), "venue": venue.strip(),
            "city": city.strip(), "status": status}


def shows_key(show: dict) -> str:
    return f"{show['date']}|{show['venue']}|{show['city']}"


# ── Artist scraper ─────────────────────────────────────────────────────────
def scrape_artist(browser, name: str, url: str) -> list[dict]:
    """Return list of shows within 200 miles of Des Moines."""
    print(f"  Scraping {name}…")
    raw = fetch_page(browser, url)
    if not raw:
        return []

    shows = []

    # 1) Try JSON-LD first (most reliable)
    for ev in extract_jsonld_events(raw):
        loc = f"{ev['city']} {ev['venue']}"
        if city_in_range(loc):
            # Parse ISO date to readable
            try:
                d = datetime.strptime(ev["date"], "%Y-%m-%d")
                date_str = d.strftime("%b %-d, %Y")
            except Exception:
                date_str = ev["date"]
            sold = "sold_out" if "sold" in ev["name"].lower() else "on_sale"
            shows.append(normalise_show(date_str, ev["venue"], ev["city"], sold))

    # 2) Fallback: text-based heuristic
    if not shows:
        # Look for date + city patterns
        date_pat = re.compile(
            r'(?P<date>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{4})',
            re.IGNORECASE
        )
        lines = raw.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            dm = date_pat.search(line)
            if dm:
                # Look ahead a few lines for city/venue
                context = " ".join(lines[i:i+6])
                if city_in_range(context):
                    sold = "sold_out" if "sold out" in context.lower() else "on_sale"
                    # Try to pull venue name (line after date)
                    venue = lines[i+1].strip() if i+1 < len(lines) else ""
                    city_match = next((c for c in CITIES_IN_RANGE if c in context), "")
                    shows.append(normalise_show(dm.group("date"), venue, city_match, sold))
            i += 1

    return shows


# ── Venue scraper ──────────────────────────────────────────────────────────
def scrape_venue(browser, name: str, location: str, url: str) -> list[dict]:
    """Return list of (date, artist, tracked) dicts for a venue."""
    print(f"  Scraping {name}…")
    raw = fetch_page(browser, url)
    if not raw:
        return []

    found = []
    lines = [l.strip() for l in raw.split("\n") if l.strip()]

    date_pat = re.compile(
        r'(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[,\s]+)?'
        r'(?P<date>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{4}'
        r'|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2})',
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        dm = date_pat.search(line)
        if dm:
            # Grab the next non-trivial line as the artist name
            artist = ""
            for j in range(i+1, min(i+5, len(lines))):
                candidate = lines[j]
                if (len(candidate) > 3 and
                        not re.match(r'^(GET TICKET|BUY TICKET|RSVP|MORE INFO|SOLD OUT|\d)', candidate, re.I)):
                    artist = candidate
                    break
            if not artist:
                continue

            # Check if artist matches any tracked name
            upper = artist.upper()
            is_tracked = any(t.upper() in upper for t in TRACKED_ARTISTS)

            date_str = dm.group("date").strip()
            found.append({
                "date": date_str,
                "artist": artist,
                "tracked": is_tracked,
            })

    return found


# ── Diff logic ─────────────────────────────────────────────────────────────
def diff_artists(old: dict, new: dict) -> dict:
    """Compare old/new artist→shows dicts. Return {artist: {added, removed, sold_out}}."""
    changes = {}
    all_artists = set(old) | set(new)
    today = date.today()

    for artist in sorted(all_artists):
        old_shows = {shows_key(s): s for s in old.get(artist, [])}
        new_shows = {shows_key(s): s for s in new.get(artist, [])}

        added   = [new_shows[k] for k in new_shows if k not in old_shows]
        removed = [old_shows[k] for k in old_shows if k not in new_shows]
        # Sold-out changes
        newly_sold = []
        for k in new_shows:
            if k in old_shows:
                if (old_shows[k].get("status") != "sold_out" and
                        new_shows[k].get("status") == "sold_out"):
                    newly_sold.append(new_shows[k])

        # Filter out past shows from 'removed' (they just expired)
        def is_past(show):
            try:
                # Try a few date formats
                for fmt in ("%b %d, %Y", "%b %-d, %Y", "%B %d, %Y"):
                    try:
                        return datetime.strptime(show["date"], fmt).date() < today
                    except ValueError:
                        pass
            except Exception:
                pass
            return False

        removed = [s for s in removed if not is_past(s)]

        if added or removed or newly_sold:
            changes[artist] = {
                "added":      added,
                "removed":    removed,
                "newly_sold": newly_sold,
            }

    return changes


def diff_venues(old: dict, new: dict) -> dict:
    """Compare old/new venue event dicts. Return {venue: {added, removed}}."""
    changes = {}
    all_venues = set(old) | set(new)
    today = date.today()

    for venue in sorted(all_venues):
        def key(ev):
            return f"{ev['date']}|{ev['artist']}"

        old_ev = {key(e): e for e in old.get(venue, [])}
        new_ev = {key(e): e for e in new.get(venue, [])}

        added   = [new_ev[k] for k in new_ev if k not in old_ev]
        removed = [old_ev[k] for k in old_ev if k not in new_ev]

        def is_past_v(ev):
            try:
                for fmt in ("%b %d, %Y", "%b %-d, %Y", "%B %d, %Y"):
                    try:
                        return datetime.strptime(ev["date"], fmt).date() < today
                    except ValueError:
                        pass
            except Exception:
                pass
            return False

        removed = [e for e in removed if not is_past_v(e)]

        if added or removed:
            changes[venue] = {"added": added, "removed": removed}

    return changes


# ── PDF builder ────────────────────────────────────────────────────────────
def build_diff_pdf(artist_changes: dict, venue_changes: dict,
                   run_date: str) -> Path | None:
    """Generate a changes-only PDF. Returns None if nothing changed."""
    if not artist_changes and not venue_changes:
        return None

    out_path = HERE / f"Concert_Changes_{run_date}.pdf"

    doc = SimpleDocTemplate(str(out_path), pagesize=letter,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)

    styles = getSampleStyleSheet()
    RED    = colors.HexColor('#c0392b')
    GREEN  = colors.HexColor('#27ae60')
    DARK   = colors.HexColor('#1a1a2e')
    GREY   = colors.HexColor('#555555')

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    title_sty    = sty('T', fontSize=20, textColor=DARK, spaceAfter=4, alignment=TA_CENTER)
    sub_sty      = sty('S', fontSize=10, textColor=GREY, spaceAfter=14, alignment=TA_CENTER)
    sec_sty      = sty('Sec', fontSize=14, textColor=colors.white, backColor=DARK,
                        spaceBefore=12, spaceAfter=6, leading=18,
                        leftIndent=-4, rightIndent=-4, borderPad=5)
    artist_sty   = sty('Art', fontSize=11, textColor=DARK, spaceBefore=10,
                        spaceAfter=2, fontName='Helvetica-Bold')
    added_sty    = sty('Add', fontSize=10, textColor=GREEN, leftIndent=16, spaceAfter=2)
    removed_sty  = sty('Rem', fontSize=10, textColor=RED, leftIndent=16, spaceAfter=2)
    sold_sty     = sty('Sol', fontSize=10, textColor=colors.HexColor('#e67e22'),
                        leftIndent=16, spaceAfter=2)
    note_sty     = sty('N', fontSize=9, textColor=GREY, spaceAfter=14, alignment=TA_CENTER,
                        fontName='Helvetica-Oblique')

    story = []

    story.append(Paragraph("&#127925; Concert Finder — Weekly Changes", title_sty))
    story.append(Paragraph(
        f"Week of {run_date} &nbsp;|&nbsp; 200-mile radius from {CENTER_CITY} &nbsp;|&nbsp; "
        "&#9650; New &nbsp; &#9660; Removed &nbsp; &#9679; Sold Out",
        sub_sty))
    story.append(HRFlowable(width="100%", thickness=2, color=DARK, spaceAfter=10))

    # ── Artist changes ──
    if artist_changes:
        story.append(Paragraph("  ARTIST TOUR UPDATES", sec_sty))
        story.append(Spacer(1, 4))

        for artist, ch in sorted(artist_changes.items()):
            block = [Paragraph(artist, artist_sty)]
            for show in sorted(ch["added"], key=lambda s: s["date"]):
                loc = f"{show['venue']}, {show['city']}"
                block.append(Paragraph(
                    f"&#9650; NEW &nbsp; <b>{show['date']}</b> — {loc}", added_sty))
            for show in sorted(ch["removed"], key=lambda s: s["date"]):
                loc = f"{show['venue']}, {show['city']}"
                block.append(Paragraph(
                    f"&#9660; REMOVED &nbsp; <b>{show['date']}</b> — {loc}", removed_sty))
            for show in sorted(ch["newly_sold"], key=lambda s: s["date"]):
                loc = f"{show['venue']}, {show['city']}"
                block.append(Paragraph(
                    f"&#9679; SOLD OUT &nbsp; <b>{show['date']}</b> — {loc}", sold_sty))
            story.append(KeepTogether(block))
    else:
        story.append(Paragraph("  ARTIST TOUR UPDATES", sec_sty))
        story.append(Paragraph("No changes to tracked artist tour dates this week.", note_sty))

    # ── Venue changes ──
    story.append(Spacer(1, 8))
    if venue_changes:
        story.append(Paragraph("  VENUE CALENDAR UPDATES", sec_sty))
        story.append(Spacer(1, 4))

        for venue, ch in sorted(venue_changes.items()):
            tracked_added   = [e for e in ch["added"]   if e.get("tracked")]
            untracked_added = [e for e in ch["added"]   if not e.get("tracked")]
            tracked_removed = [e for e in ch["removed"] if e.get("tracked")]

            block = [Paragraph(venue, artist_sty)]
            for ev in sorted(tracked_added, key=lambda e: e["date"]):
                block.append(Paragraph(
                    f"&#9650; NEW (TRACKED) &nbsp; <b>{ev['date']}</b> — {ev['artist']}",
                    added_sty))
            for ev in sorted(tracked_removed, key=lambda e: e["date"]):
                block.append(Paragraph(
                    f"&#9660; REMOVED (TRACKED) &nbsp; <b>{ev['date']}</b> — {ev['artist']}",
                    removed_sty))
            for ev in sorted(untracked_added, key=lambda e: e["date"]):
                block.append(Paragraph(
                    f"&#9650; New &nbsp; <b>{ev['date']}</b> — {ev['artist']}",
                    sty('ua', fontSize=9, textColor=GREEN, leftIndent=16, spaceAfter=1)))
            story.append(KeepTogether(block))
    else:
        story.append(Paragraph("  VENUE CALENDAR UPDATES", sec_sty))
        story.append(Paragraph("No new venue events this week.", note_sty))

    # Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph(
        "Data sourced from official artist and venue websites. "
        "Always verify at source before purchasing tickets.",
        sty('foot', fontSize=8, textColor=colors.HexColor('#aaaaaa'), alignment=TA_CENTER)
    ))

    doc.build(story)
    return out_path


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    run_date = date.today().strftime("%Y-%m-%d")
    print(f"\n=== Concert Weekly Watcher — {run_date} ===\n")

    # Install Playwright browsers if needed
    import subprocess
    try:
        subprocess.run(["playwright", "install", "chromium", "--with-deps"],
                       capture_output=True, check=True)
    except Exception:
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                           capture_output=True)
        except Exception as e:
            print(f"playwright install warning: {e}")

    # Load previous state
    prev_state = {"artist_shows": {}, "venue_shows": {}}
    if STATE_FILE.exists():
        try:
            prev_state = json.loads(STATE_FILE.read_text())
            print(f"Loaded previous state from {prev_state.get('last_run', 'unknown date')}\n")
        except Exception as e:
            print(f"Warning: could not load state file ({e}). Starting fresh.\n")

    new_artist_shows = {}
    new_venue_shows  = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # ── Scrape artists ──
        print("── Scraping artist tour pages ──")
        for artist, url in ARTIST_URLS.items():
            try:
                shows = scrape_artist(browser, artist, url)
                new_artist_shows[artist] = shows
                if shows:
                    print(f"    {artist}: {len(shows)} show(s) in range")
            except Exception as e:
                print(f"    {artist}: ERROR — {e}")
                new_artist_shows[artist] = prev_state["artist_shows"].get(artist, [])

        # ── Scrape venues ──
        print("\n── Scraping venue calendars ──")
        for venue_name, (location, in_range, url) in VENUE_URLS.items():
            try:
                events = scrape_venue(browser, venue_name, location, url)
                new_venue_shows[venue_name] = events
                tracked = [e for e in events if e.get("tracked")]
                print(f"    {venue_name}: {len(events)} events, "
                      f"{len(tracked)} match tracked artists")
            except Exception as e:
                print(f"    {venue_name}: ERROR — {e}")
                new_venue_shows[venue_name] = prev_state["venue_shows"].get(venue_name, [])

        browser.close()

    # ── Diff ──
    print("\n── Computing changes ──")
    artist_ch = diff_artists(prev_state.get("artist_shows", {}), new_artist_shows)
    venue_ch  = diff_venues (prev_state.get("venue_shows",  {}), new_venue_shows)

    total_changes = (sum(len(v["added"]) + len(v["removed"]) + len(v["newly_sold"])
                         for v in artist_ch.values()) +
                     sum(len(v["added"]) + len(v["removed"])
                         for v in venue_ch.values()))
    print(f"Found {total_changes} change(s) across "
          f"{len(artist_ch)} artist(s) and {len(venue_ch)} venue(s).")

    # ── Build PDF ──
    pdf_path = build_diff_pdf(artist_ch, venue_ch, run_date)
    if pdf_path:
        print(f"\n✅ Diff PDF saved: {pdf_path}")
    else:
        print("\n✅ No changes this week — no PDF generated.")

    # ── Save new state ──
    new_state = {
        "last_run":     run_date,
        "center":       CENTER_CITY,
        "radius_miles": RADIUS_MILES,
        "artist_shows": new_artist_shows,
        "venue_shows":  new_venue_shows,
    }
    STATE_FILE.write_text(json.dumps(new_state, indent=2))
    print(f"State saved → {STATE_FILE}\n")


if __name__ == "__main__":
    main()
