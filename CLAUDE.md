# Wingman — Workflow Contract

This document defines the contract between **Claude Code** (codebase maintainer),
**Claude Cowork** (runtime workflow executor), and **GitHub Actions** (build/deploy pipeline).

---

## Roles

| Actor | Responsibility |
|-------|---------------|
| **Claude Code** | Maintains codebase, schemas, models, frontend, backend. Commits and pushes code changes. |
| **Claude Cowork** | Executes weekly scrape (Chrome skills), Spotify sync (interactive), Gmail digest. Writes data files per schemas below. |
| **GitHub Actions** | Triggered by push. Builds frontend in demo mode, deploys to GitHub Pages. Does NOT run the scraper. |
| **Local UI** | Flask/FastAPI backend + React frontend. Manages artists, venues, settings. Displays last summary + link to GitHub Pages. |

---

## Workflow: Weekly Concert Scrape

**Trigger:** Scheduled Cowork session (weekly) OR manual Cowork session.

**Sequence:**
1. Read `wingman_config.json` for artists, venues, festivals, settings
2. For each active artist: Chrome skill navigates to tour page, Claude extracts structured show data
   - **Include:** shows in the United States, Canada, and Mexico
   - **Exclude:** shows in Europe, UK, Australia, Asia, South America, or any other non-North-America territory
   - If country is ambiguous, check city/state — US state abbreviations or Canadian province abbreviations confirm inclusion
3. For each active venue: Chrome skill navigates to calendar page, Claude extracts event data
   - **Standard venues:** read page text directly after load
   - **Lazy-load / "Load More" venues** (e.g. ACL Live): use the JS interval pattern to auto-click the button until it disappears, then extract:
     ```javascript
     // Fire-and-forget repeated clicks every 2s until button gone
     window._loadInterval = setInterval(() => {
       const btn = [...document.querySelectorAll('button')]
         .find(b => b.textContent.trim() === 'Load More Events');
       if (btn) { btn.click(); }
       else { clearInterval(window._loadInterval); window._loadDone = true; }
     }, 2000);
     ```
     Wait ~30–60s, check `window._loadDone`, then extract `document.body.innerText` in chunks.
   - **Venues flagged as lazy-load** (see table below): always use the scroll/load-more pattern
3a. For each active festival: Chrome skill navigates to lineup URL, Claude extracts the artist lineup
   - Read the page and extract every performing artist or act listed on the lineup page
   - For each extracted artist, check whether their name (case-insensitive) appears in `wingman_config.json` artists → set `tracked: true` if matched, `false` otherwise
   - Store results as a `FestivalLineupEntry` array under `festival_shows[festival_name]` in `concert_state.json`
   - **Standard lineup pages:** read page text directly after load (see Festival Scraping Behavior table below)
4. For each extracted show: geocode the venue location
   - Check `geocode_cache.json` first
   - If cache miss: query Nominatim API (1 req/sec rate limit)
   - Store result in `geocode_cache.json`
5. Include all North America shows (no distance filtering)
   - Do **NOT** calculate or write `distance_miles` — that field has been removed from the Show schema
   - Write `radius_miles: null` in `concert_state.json` (field is deprecated but kept for backward compat)
   - Write `center: "Des Moines, IA"` in `concert_state.json` (used as map home position, not a filter)
6. Diff new results against previous `concert_state.json`
7. Write updated `concert_state.json` (MUST validate against schema)
8. Fetch Ticketmaster Coming Soon data for `docs/summary.json`:
   - Call `GET http://localhost:8000/api/coming-soon` (the local backend handles TM API + caching)
   - If the response has `api_configured: true`, include `coming_soon` and `coming_soon_fetched` in `docs/summary.json`
   - If `api_configured: false` (no API key set), write `coming_soon: []` and `coming_soon_fetched: null`
   - Do **NOT** call the Ticketmaster API directly — always go through the backend endpoint
9. Write `docs/summary.json` (MUST validate against schema — includes `coming_soon` array)
10. Copy current snapshot to `docs/history/YYYY-MM-DD.json`
11. Run `python scripts/validate_state.py` to verify data integrity
12. Commit and push: `concert_state.json`, `docs/summary.json`, `docs/history/*.json`
13. Send Gmail digest via Chrome skill (send even if no changes)

**Commit message format:** `Weekly update: YYYY-MM-DD - X new, Y removed`

---

## Workflow: Spotify Sync

**Trigger:** Manual only — user clicks "Sync Spotify" button in local UI, then starts Cowork session.

**Sequence:**
1. Read `wingman_config.json` for current artist list
2. Authenticate with Spotify using locally stored OAuth tokens (`spotify_tokens.json`)
3. **Phase 1 — Spotify follows not in Wingman:**
   - `GET /me/following?type=artist` to get followed artists
   - For each followed artist NOT in `wingman_config.json`:
     - Ask user interactively: "Add [Artist] to Wingman?"
     - If yes: Chrome skill searches Google for official website + tour/shows URL
     - Add artist to `wingman_config.json` with discovered URL
4. **Phase 2 — Wingman artists not followed on Spotify:**
   - For each artist in `wingman_config.json` NOT in Spotify follows:
     - Search Spotify for the artist
     - If found: ask user "Follow [Artist] on Spotify?"
       - If yes: `PUT /me/following?type=artist&ids=[id]`
     - If NOT found on Spotify: flag in `flagged_items.json` for local UI display
5. **Phase 3 — Listening history suggestions:**
   - `GET /me/top/artists` for time_range: short_term, medium_term, long_term
   - `GET /me/player/recently-played` for recent tracks (extract unique artists)
   - For each discovered artist not already followed or tracked:
     - Check `dismissed_suggestions.json` — skip if dismissed < 6 months ago
     - Ask user: "[Artist] appears in your listening history. Track and follow?"
     - If yes: add to Wingman + follow on Spotify
     - If dismissed: write to `dismissed_suggestions.json` with timestamp

**Required Spotify OAuth scopes:**
- `user-follow-read`
- `user-follow-modify`
- `user-top-read`
- `user-read-recently-played`

---

## Workflow: Email Digest

**Method:** Claude Cowork sends via Gmail Chrome skill (no code infrastructure).

**When:** End of every weekly scrape session, regardless of whether changes were found.

**Format:**
```
Subject: Wingman Weekly — YYYY-MM-DD

X new shows found, Y shows removed, Z newly sold out.
(or: No changes this week.)

View full report: [GitHub Pages URL]
```

---

## Ticketmaster Integration

Wingman uses the [Ticketmaster Discovery API v2](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/) to surface **announced-but-not-yet-on-sale** shows for tracked artists.

### How it works

- **API key:** Stored in `wingman_config.json` under `ticketmaster_api_key`. The user enters it via Settings > Ticketmaster in the local UI.
- **Backend endpoint:** `GET /api/coming-soon` — the FastAPI backend queries TM, filters results, and caches the response in `ticketmaster_cache.json` (6-hour TTL). Pass `?force=true` to bypass the cache.
- **Cowork role:** Cowork does **NOT** call the TM API directly. During the weekly scrape, Cowork calls `GET http://localhost:8000/api/coming-soon` and copies the result into `docs/summary.json` so GitHub Pages can display Coming Soon data.

### What the API returns

For each tracked (non-paused) artist, the backend:
1. Searches TM by `keyword=<artist_name>` with `classificationName=music`
2. Filters to North America only (`countryCode` in `US`, `CA`, `MX`)
3. Matches events against the artist name via attraction names (fuzzy substring match to avoid tribute bands)
4. Keeps only shows where `sales.public.startDateTime` is **in the future** (i.e., not yet on sale) OR `sales.public.startTBD` is true
5. Extracts presale windows (`sales.presales[]`)

### Artists not found

If an artist returns zero matching North America events on TM (after name filtering), they are included in the `artists_not_found` list in the API response. This is displayed as a collapsible section in the Coming Soon tab of the local UI. Common reasons an artist is not found:
- They tour under a different name than what is stored in Wingman
- They don't list shows on Ticketmaster
- They have no upcoming North America dates at all

**Note:** A network/API error during a fetch does NOT add an artist to `artists_not_found` — only a genuine zero-results response does.

### Cache behavior

- Cache file: `ticketmaster_cache.json` (gitignored, local only)
- TTL: 6 hours. The backend serves cached data within that window.
- Cache is cleared automatically when the API key changes in Settings.
- Cowork should call the endpoint at the start of each weekly scrape (before writing `summary.json`) to get fresh data. If the cache is still valid, the backend returns it immediately; if not, it fetches fresh from TM.

### `docs/summary.json` — Coming Soon fields

The `Summary` schema includes two TM-specific fields:
- `coming_soon` — array of `ComingSoonShow` objects (see `schemas/summary.schema.json`)
- `coming_soon_fetched` — ISO 8601 datetime string of when data was last fetched from TM

These are written by Cowork during the weekly scrape (step 8 above) and consumed by the GitHub Pages frontend to display the Coming Soon tab in demo mode.

---

## File Ownership

| File | Written By | Read By | Pushed to GitHub? |
|------|-----------|---------|-------------------|
| `wingman_config.json` | Local UI (backend API) | Cowork, backend | No |
| `concert_state.json` | Cowork | Code, frontend, Cowork | **Yes** |
| `geocode_cache.json` | Cowork (geocoding step) | Cowork, backend API | No |
| `ticketmaster_cache.json` | Backend (`/api/coming-soon`) | Backend | **Never** (.gitignored) |
| `dismissed_suggestions.json` | Cowork (Spotify sync) | Cowork, backend | No |
| `flagged_items.json` | Cowork (Spotify sync) | Backend (local UI) | No |
| `spotify_tokens.json` | Backend (OAuth flow) | Cowork | **Never** (.gitignored) |
| `docs/summary.json` | Cowork | GitHub Pages frontend | **Yes** |
| `docs/history/YYYY-MM-DD.json` | Cowork | GitHub Pages frontend | **Yes** |
| `schemas/*.schema.json` | Claude Code | Cowork (validation) | Yes |
| `backend/models.py` | Claude Code | Backend (validation) | Yes |

---

## Data Schemas

All shared data files MUST conform to the JSON schemas in `schemas/`.

### concert_state.json

Top-level structure:
- `last_run` (string, date format YYYY-MM-DD)
- `center` (string, e.g. "Des Moines, IA") — map home city
- `radius_miles` (number | null) — deprecated, kept for backward compat
- `artist_shows` (object: artist name -> array of Show objects)
- `venue_shows` (object: venue name -> array of VenueShow objects)
- `festival_shows` (object: festival name -> array of FestivalLineupEntry objects)

**Show object:**
- `date` (string) — display format, e.g. "Mar 15, 2026"
- `venue` (string) — venue name
- `city` (string) — "City, ST" format (or "City, Province, CA" for Canada)
- `status` (enum: "on_sale" | "sold_out")
- `lat` (number | null) — venue latitude (from geocode_cache.json)
- `lon` (number | null) — venue longitude (from geocode_cache.json)

**Note:** `distance_miles` has been removed. Do NOT write this field.

**VenueShow object:**
- `date` (string) — display format
- `artist` (string) — artist/event name
- `tracked` (boolean) — true if artist is in the tracked artists list

**FestivalLineupEntry object:**
- `artist` (string) — artist or act name as it appears on the lineup page
- `tracked` (boolean) — true if artist name matches an entry in `wingman_config.json` artists (case-insensitive)

### Venue Scraping Behavior

| Venue | Load Pattern | Notes |
|-------|-------------|-------|
| Hoyt Sherman Place | Standard page load | |
| First Fleet Concerts | Standard page load | Covers Wooly's + Val Air |
| Iowa Events Center | Standard page load | |
| Starlight Theatre | Standard page load | |
| The Waiting Room | Standard page load | |
| Ryman Auditorium | Standard page load | |
| **ACL Live** | **Lazy-load / "Load More" button** | Use JS interval pattern; ~8–10 clicks to reach full calendar |
| The Salt Shed | Standard page load | |

### Festival Scraping Behavior

| Festival | Load Pattern | Notes |
|----------|-------------|-------|
| Minnesota Yacht Club Festival | Standard page load | Extract all artists from lineup page |
| Hinterland Music Festival | Standard page load | Extract all artists from lineup page |

### wingman_config.json

See `schemas/wingman_config.schema.json` for full definition.

### docs/summary.json

See `schemas/summary.schema.json` for full definition. Includes:
- Metadata (run date, center/home city)
- All North America shows with lat/lon coordinates
- Diff from previous run (added, removed, sold_out)
- Map data (center coordinates, show pin coordinates)

### geocode_cache.json

Simple key-value: location string -> `{"lat": number, "lon": number}`

### dismissed_suggestions.json

Artist name -> `{"dismissed_at": "YYYY-MM-DD", "resurface_after": "YYYY-MM-DD", "reason": string, "source": string}`

---

## Validation

Before committing data, Cowork MUST run:
```bash
python scripts/validate_state.py
```

This validates `concert_state.json` against the Pydantic models in `backend/models.py`.
If validation fails, fix the data before committing.

---

## GitHub Pages

The public site is deployed from `frontend/dist` built in demo mode.

- **Local UI** includes a link to the GitHub Pages URL (opens in new tab)
- The GitHub Pages site does NOT link back to the local UI
- GitHub Pages shows: summary table, Leaflet map with show + venue pins, "new this week" highlights
- Historical snapshots are accessible via `docs/history/`

---

## Geocoding Rules

- **Provider:** OpenStreetMap Nominatim (free, no API key)
- **Rate limit:** 1 request per second (enforced by caller)
- **Cache:** `geocode_cache.json` — geocode once, reuse forever unless venue changes
- **Scope:** All North America shows (no distance filtering)
- **Center city** is geocoded once and cached (used as map home position)
- **Build-up approach:** First run geocodes all venues; subsequent runs only geocode new ones

---

## Git Conventions

- **Branch:** Cowork pushes data to `main`
- **Commit messages:** `Weekly update: YYYY-MM-DD - X new, Y removed`
- **Files committed by Cowork:** `concert_state.json`, `docs/summary.json`, `docs/history/*.json`
- **Files NEVER committed:** `spotify_tokens.json`, `geocode_cache.json`, `dismissed_suggestions.json`, `flagged_items.json`

## Frontend Build Requirement

`frontend/dist` is gitignored and **never committed**. The local FastAPI server serves directly from this directory, so it must be rebuilt whenever frontend source files change.

**Claude Code MUST run a local build after every PR that touches any file under `frontend/src/`, `frontend/index.html`, `frontend/vite.config.*`, or `frontend/tailwind.config.*`:**

```bash
cd /home/user/Wingman/frontend && npm install && npx vite build
```

This applies whether creating a new PR or pushing additional commits to an existing one. Do not skip this step — without it, the locally running server will serve stale code and the user will not see the changes.

---

## Development Status

### Completed
- Full local UI: React frontend + FastAPI backend, served from `frontend/dist`
- Artist management (add, edit, pause, delete) with genre badges
- Venue management (local vs. travel, add, edit, pause, delete)
- Festival management (add, pause, delete) — Configure > Festivals sub-tab
- Settings panel (map home city, GitHub Pages URL)
- Schedule panel (next run display, cron config)
- Flagged Items panel (Spotify sync flags surfaced in UI)
- Artists tab: artist cards (names link to tour pages) + interactive Leaflet map with viewport filtering
- Venues tab: venue cards (names link to calendars), split local/travel/festivals; no map
- Festivals section in Venues tab: cards linking to lineup pages; expandable with tracked artists when `festival_shows` data available
- Map tooltips show all shows (no "+N more" truncation)
- Leaflet map with artist show pins (green=new, red=sold out, blue=on sale, orange=coming soon) + venue pins (violet)
- Interactive map filtering: click artist card to filter map pins; map viewport filters visible cards
- Hover tooltips on map pins showing all artist/date/venue details
- Configure tab: combined management with sub-tabs for Artists, Venues, Festivals
- Backend geocoding via Nominatim with `geocode_cache.json` cache
- `/api/config` returns `center_lat`/`center_lon` for map + venue lat/lon for venue pins
- All North America shows scraped (no distance/radius filtering)
- GitHub Pages demo build (VITE_DEMO_MODE=true) + GitHub Actions deploy workflow
- JSON schemas + Pydantic validation (`scripts/validate_state.py`)
- **Ticketmaster integration:** Coming Soon tab (announced but not-yet-on-sale shows + presale windows); TM data merged natively into Artist cards; orange map pins for coming-soon shows; "Not found on Ticketmaster" collapsible list; API key stored in `wingman_config.json`; 6-hour cache in `ticketmaster_cache.json`; `docs/summary.json` includes `coming_soon` array for GitHub Pages

### Known Local Setup Gotcha
`geocode_cache.json` is gitignored and won't exist on a fresh clone. On first run,
the backend tries Nominatim to geocode the center city — if that call fails (network,
firewall, etc.), the map won't render. Fix: create the file manually:
```bash
echo '{"Des Moines, IA": {"lat": 41.5868, "lon": -93.625}}' > ~/Wingman/geocode_cache.json
```
After a Cowork scrape, this file will be populated automatically going forward.

### Next: Spotify OAuth (Task #3)
Build the Spotify Connect flow in the local UI:
- Spotify Developer App credentials stored in `wingman_config.json` (client_id, client_secret, redirect_uri)
- Backend OAuth endpoints: `GET /api/spotify/auth` (redirect to Spotify) + `GET /api/spotify/callback` (exchange code for tokens, save to `spotify_tokens.json`)
- Frontend: "Connect Spotify" button in Settings tab → shows connection status (connected/disconnected) + disconnect option
- `spotify_tokens.json` is NEVER committed (already in .gitignore)
- Required scopes: `user-follow-read user-follow-modify user-top-read user-read-recently-played`
- Prerequisite: user must create a Spotify Developer App at developer.spotify.com and have client_id + client_secret ready
