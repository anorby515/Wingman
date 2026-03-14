# Festival Rethink — Implementation Plan

**Status:** Proposal (Step 6 in the roadmap)
**Date:** 2026-02-27

---

## Problem Statement

Festivals are currently second-class citizens in Wingman. The full data pipeline exists for artists and venues — TM fetch → summary.json → frontend display → notifications — but festivals fall off the map after the fetch step. Specifically:

1. **Festival shows are fetched but discarded.** `fetch_festival_shows()` runs as Phase 3 of every TM refresh, but `build_summary()` never writes `festival_shows` into `docs/summary.json`.
2. **No frontend display.** There's no tab or card view showing festival events from TM. The "Festivals" sub-tab under Configure only manages the tracking list (add/pause/delete).
3. **Keyword search is a blunt instrument.** Searching TM for "Hinterland Music Festival" returns any event with those words in the name. This works for uniquely-named festivals but can produce false positives for generic names.
4. **No festival data in notifications.** The notify script compares artist and venue show keys against the baseline, but festivals are absent from both.
5. **No festival shows on the map.** Artist shows get blue/orange pins, venue events get violet pins, but festival events have no map presence.

---

## Current Implementation (What Exists)

| Layer | Status | Details |
|-------|--------|---------|
| **Config** | Complete | `FestivalConfig` model (url + paused), CRUD endpoints, Configure > Festivals sub-tab |
| **tracked.json** | Complete | Festivals exported with name/url/paused for GH Action |
| **TM fetch** | Complete | `fetch_festival_shows()` in `ticketmaster.py`, called in `run_full_refresh()` Phase 3 |
| **summary.json** | Missing | `build_summary()` does not include `festival_shows` |
| **Frontend display** | Missing | No festival show cards, no festival map pins |
| **Notifications** | Missing | No festival show keys in baseline or diff logic |
| **Schema** | Partial | `ComingSoonFestivalEvent` model defined but unused; no `SummaryFestivalShow` in summary schema |

---

## The Core Question: What Do We Actually Want From Festival Tracking?

There are two fundamentally different things a user might mean by "track a festival":

### Option A: Track the Festival as a TM Event
- Search TM for events matching the festival name
- Show dates, venues, on-sale status — same as any other show
- Works well for festivals that list on Ticketmaster (Bonnaroo, Lollapalooza, etc.)
- **This is what the current code does.** It just doesn't surface the results.

### Option B: Track Which Tracked Artists Are Playing a Festival
- The user cares about "which of MY artists are on the Hinterland lineup?"
- This requires lineup data, which TM doesn't provide (TM lists the festival as one event, not per-artist)
- Would need a different data source (manual entry, web scraping, or a lineup API)

**Recommendation:** Option A is the pragmatic path. It completes the pipeline that's already 80% built. Option B is a future enhancement if/when a lineup data source becomes available.

---

## Proposed Implementation

### Phase 1: Complete the Pipeline (Festival Shows in Summary)

**Goal:** Festival shows flow through the full pipeline just like artist and venue shows.

#### 1a. Update `build_summary()` in `scripts/fetch_tm_data.py`

Add a `festival_shows` section to the summary output, structured as:

```json
{
  "festival_shows": {
    "Hinterland Music Festival": [
      {
        "date": "Aug 1, 2026",
        "venue": "Avenue of the Saints Amphitheater",
        "city": "Saint Charles, IA, US",
        "event_name": "Hinterland Music Festival 2026",
        "status": "on_sale",
        "lat": 41.28,
        "lon": -93.05,
        "is_new": true
      }
    ]
  },
  "festivals_not_found": ["Some Obscure Fest"]
}
```

Key fields:
- `event_name` — the actual TM event name (may differ from the tracked festival name)
- `status` — on_sale or coming_soon, same logic as artist shows
- `is_new` — diff detection against previous summary, same as artist shows

Also include festival coming-soon shows in the `coming_soon` array with a `"source": "festival"` field to distinguish them.

#### 1b. Update `schemas/summary.schema.json`

Add `festival_shows` and `festivals_not_found` to the schema with a new `SummaryFestivalShow` definition.

#### 1c. Update `backend/models.py`

Add a `SummaryFestivalShow` model if needed for validation. The existing `ComingSoonFestivalEvent` model can be cleaned up or replaced.

#### 1d. Update `scripts/export_static_data.py`

Ensure `festival_shows` and `festivals_not_found` are included when generating `static-data.json` for GitHub Pages.

---

### Phase 2: Frontend Display

**Goal:** Festival events appear in the UI alongside artist and venue shows.

#### 2a. Festival Cards in the "Concerts & Festivals" Tab

The `ArtistsSummaryTab` already renders three sections: Artists, Venues, and a "Festivals" heading. Currently the Festivals section only shows a static list of tracked festival names with links to their URLs.

**Change:** Replace the static list with TM-sourced festival show cards. Each card shows:
- Festival name (links to the festival URL from config)
- Event name (if different from festival name)
- Date, venue, city
- On-sale status badge (same styling as artist shows)

Group cards by festival name, sorted by date.

If a festival is in `festivals_not_found`, show it in a "Not found on TM" collapsed section (same pattern as artists not found).

#### 2b. Festival Pins on the Map

Add festival event pins to the Leaflet map:
- **Color:** Green (distinct from blue=on-sale artist, orange=coming-soon, violet=venue)
- **Tooltip:** Festival name, event name, date, venue
- **Behavior:** Clicking a festival card filters the map to that festival's pins (same as clicking an artist card)

#### 2c. Festival Shows in Coming Soon Tab

Festival coming-soon shows should appear in the Coming Soon tab alongside artist coming-soon shows. Add a "Festival" badge or label to distinguish them.

---

### Phase 3: Notifications

**Goal:** New festival events trigger push notifications.

#### 3a. Add Festival Keys to Notification Baseline

Extend `docs/notification_baseline.json`:

```json
{
  "updated_at": "...",
  "artist_show_keys": ["..."],
  "venue_show_keys": ["..."],
  "festival_show_keys": ["Hinterland Music Festival|Aug 1, 2026|Avenue of the Saints Amphitheater"]
}
```

#### 3b. Update `scripts/notify_changes.py`

Add festival diff detection:
- Compare fresh festival show keys against baseline
- New festival events appear in a "NEW FESTIVAL EVENTS:" section in the notification message

---

### Phase 4: Improve Festival Search Quality (Optional Enhancement)

The current `name_matches()` function does fuzzy substring matching. For festivals, this could be tightened:

- Require a higher match threshold for festival names (they tend to be more generic than artist names)
- Consider matching on TM's `classificationId` for festivals/music-festivals specifically
- Add a TM attraction ID field to `FestivalConfig` so the user can pin a festival to a specific TM entity (bypasses keyword search entirely)

This phase is optional and can be deferred until false positives become a real problem.

---

## What This Plan Does NOT Cover

- **Lineup discovery** — Determining which specific artists are playing a festival. TM lists festivals as single events, not per-artist lineups. This would require scraping festival websites or a dedicated lineup API, which conflicts with the "no web scraping" principle.
- **Bandsintown integration** — Deferred to Step 10.
- **Festival-specific artist cross-referencing** — e.g., "Highlight tracked artists who are playing Hinterland." This requires lineup data (see above).

---

## Implementation Order & Effort Estimates

| Phase | Scope | Files Changed |
|-------|-------|---------------|
| 1a | `build_summary()` adds festival_shows | `scripts/fetch_tm_data.py` |
| 1b | Schema update | `schemas/summary.schema.json` |
| 1c | Model update | `backend/models.py` |
| 1d | Static data export | `scripts/export_static_data.py` |
| 2a | Festival cards in main tab | `frontend/src/components/ArtistsSummaryTab.jsx` |
| 2b | Map pins | `frontend/src/components/ConcertMap.jsx` |
| 2c | Coming Soon integration | `frontend/src/components/ComingSoonTab.jsx` |
| 3a | Baseline schema | `docs/notification_baseline.json` |
| 3b | Notification diff | `scripts/notify_changes.py` |
| 4 | Search quality | `backend/ticketmaster.py` (optional) |

Tests to add/update:
- `tests/test_fetch_tm_data.py` — verify `build_summary()` includes `festival_shows`
- `tests/test_ticketmaster.py` — already covers `fetch_festival_shows()`
- `frontend/src/__tests__/` — test festival card rendering

---

## Decisions Made

1. **Green pins.** Green is the most visually distinct from the existing palette (blue, orange, violet, indigo). Adopted.
2. **Festivals as their own top-level tab.** Instead of a section within "Concerts & Festivals," festivals get a dedicated "Festivals" tab placed to the right of "On Sale Soon." This gives more UX flexibility and keeps the Concerts tab focused on artist/venue shows.
3. **Festival coming-soon inside the Festivals tab.** Festival coming-soon events live within each festival card on the Festivals tab, not in the shared "On Sale Soon" tab. This keeps all festival data in one place.
4. **TM attraction ID pinning deferred.** Only 3 festivals tracked, all with distinctive names. Will implement when false positives become a real problem.

## Implementation Status

**Completed.** All phases implemented:

- `build_summary()` now includes `festival_shows`, `festivals_not_found`, and `festival_coming_soon`
- `build_static_data()` passes festival data through to the demo frontend
- `schemas/summary.schema.json` updated with `SummaryFestivalShow` and `ComingSoonFestivalEvent` definitions
- `backend/models.py` updated with `SummaryFestivalShow` model; `Summary` model includes festival fields
- `scripts/export_static_data.py` includes festival data in static export
- New `FestivalsTab.jsx` component with festival cards, coming-soon sections, map, and not-found list
- `App.jsx` updated with Festivals tab (tab order: Concerts & Festivals > On Sale Soon > Festivals)
- `ConcertMap.jsx` supports green festival pins via new `festivalShows` prop
- `scripts/notify_changes.py` detects new festival events and includes them in push notifications
- Tests: 5 new festival tests in `test_fetch_tm_data.py`, all 103 backend + 7 frontend tests passing

### wingman-app Implementation (2026-03-14)

Festival support has been fully implemented in the `wingman-app` mobile app (Supabase + React Native):

- **Edge Functions:** Atomic `fetch-festivals` function with self-chaining batch processing, runs on pg_cron daily
- **Festival Detail Screen:** `app/festival/[id].tsx` — hero, info card, lineup grouped by day
- **Shows.Festivals:** Date-sorted festival list (soonest first), favorite toggle, Add Festival modal with TM search
- **Lineup Extraction:** `linkFestivalLineup()` extracts artists from TM's `_embedded.attractions` array, assigns day numbers from event dates, preserves TM listing order as `sort_order`
- **Data Quality Fixes:** Headliner badge removed (TM can't reliably detect headliners), festival name filtered from lineup (TM includes it as an attraction)

### TM Festival Data Quality Findings

Real-world testing revealed that TM's festival data has significant limitations:

1. **Headliner detection unreliable** — attraction array order doesn't indicate billing position
2. **Festival name pollutes lineup** — TM lists the festival itself as an attraction
3. **Day assignment unreliable** — festival-pass events list all artists on a single date

**Recommendation:** TM is adequate for festival discovery but not for lineup metadata. Bandsintown (free, `lineup` array in event responses) is the recommended supplementary source. See `wingman-app/FESTIVAL_API_RESEARCH.md` for full analysis.
