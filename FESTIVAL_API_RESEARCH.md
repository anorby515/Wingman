# Festival API Research — Vibes.live
**Research Date:** March 2026
**Status:** Research complete, pending product decision

---

## Executive Summary

There is **no single API** that perfectly solves the "festival lineup" problem. The best approach is a **multi-source strategy**, combining the Ticketmaster Discovery API already in use with supplementary sources. **Bandsintown** is the top recommendation for a complementary free data source due to its `lineup` array in event responses. **MusicBrainz** is the best open/free option for cross-referencing artist IDs. **Songkick** has the richest festival data but costs $500+/month.

---

## Tier 1: Strong Candidates

### 1. Ticketmaster Discovery API (Already In Use)
- **Data:** Dates, venues, ticket links, and an `_embedded.attractions` array listing multiple performers for festival events (with billing order). Has classification data for filtering (`classificationName=Festival`).
- **Auth:** API key (query parameter)
- **Rate Limits:** 5,000 requests/day, 2-5 requests/second (free tier)
- **Pricing:** Free
- **Festival Lineup Quality:** **Moderate.** TM-promoted festivals tend to have complete attraction arrays. Non-TM festivals may be sparse or absent.
- **Cross-reference:** Can query by attraction (artist) ID to check if tracked artists appear in festival events.
- **Recommendation:** Already in use. Maximize by filtering events with `classificationName=Festival` and extracting the attractions array for lineup data.

### 2. Bandsintown API — RECOMMENDED ADDITION
- **Data:** Artist events with dates, venue name/location, ticket links, and a **`lineup` array** listing all artists at multi-artist events. Also returns `tracker_count`, artist images, and event page links.
- **Auth:** `app_id` query parameter (requires written consent from Bandsintown)
- **Rate Limits:** Not publicly specified; they recommend caching 404s for 24 hours.
- **Pricing:** Free for artists/representatives. Commercial use requires explicit written approval.
- **Festival Lineup Quality:** **Good.** The lineup array in event responses is the closest thing to a proper festival lineup endpoint among free APIs.
- **Cross-reference:** API is artist-centric (query by artist name). Natural workflow: for each tracked artist, fetch events, group by shared venue/date to identify festivals.
- **Key Limitation:** No "search all festivals in region X" endpoint. Must query artist-by-artist and aggregate.

### 3. Songkick API
- **Data:** Events (concerts + festivals), artists, venues. Festival events include a **`performance` array** with artist name, ID, and billing info (headliner vs support). Supports `type=festival` filtering.
- **Auth:** API key
- **Pricing:** **$500/month minimum.** No longer approving hobbyist/educational requests.
- **Festival Lineup Quality:** **Best available.** Largest live music database (6M+ events) with dedicated festival type and billing index.
- **Cross-reference:** Query upcoming events for an artist, filter by type=festival.
- **Key Limitation:** Cost ($500/mo ongoing).

---

## Tier 2: Viable With Trade-offs

### 4. JamBase Data API
- **Data:** 400K+ artists, 170K+ venues, 100K+ upcoming events. Auto-matches with MusicBrainz, Ticketmaster, Spotify IDs. Schema.org compliant.
- **Auth:** OAuth 2.0 / API keys
- **Pricing:** Custom pricing (enterprise model). Trial access for evaluation only.
- **Festival Lineup Quality:** **Very good.** Deep festival coverage, especially jam band/indie/electronic scenes.
- **Cross-reference:** Built-in cross-platform ID matching (Spotify, MusicBrainz, Ticketmaster).
- **Key Limitation:** Unknown cost, enterprise positioning.

### 5. MusicBrainz API — Best Free/Open Option
- **Data:** 12 core entities including `event` (concerts + festivals). Events linked to artists via `artist-rels` and to venues/places via `place-rels`. All data is CC0 public domain.
- **Auth:** None required (user-agent string recommended)
- **Rate Limits:** 1 request per second
- **Pricing:** Completely free (CC0)
- **Festival Lineup Quality:** **Variable.** Community-maintained. Major festivals well-documented, smaller festivals sparse.
- **Cross-reference:** MusicBrainz IDs are widely used as canonical identifiers. Excellent for normalizing artist identities across platforms.
- **Key Limitation:** Slow rate limits (1 req/sec), data may lag behind announcements.

### 6. PredictHQ API
- **Data:** 20M+ events across 30K cities. Music festivals as a specific category. Geolocation, impact scores, predicted attendance.
- **Auth:** OAuth 2.0
- **Pricing:** 14-day free trial, then limited Free Plan. Paid plans custom-quoted.
- **Festival Lineup Quality:** **Poor for lineups.** Designed for demand forecasting, not music discovery. No artist/performer data.
- **Useful For:** "Is there a major festival happening near [location] on [date]?" but not lineup data.

---

## Tier 3: Not Useful for This Use Case

| API | Why Not |
|-----|---------|
| **Spotify Web API** | No concert or event data whatsoever (sources in-app data from Bandsintown/Songkick) |
| **Setlist.fm API** | No festival endpoints at all. Useful for post-show setlists only. |
| **DICE (Festicket)** | No public API. Partners-only GraphQL endpoint. |
| **Eventbrite API** | Poor music festival coverage, no structured lineup/performer field. |
| **Music Festival Wizard** | No API. Website only (1,700+ festivals, 22M pageviews). Scraping-only option. |

---

## Open Data Sources

### Wikidata
- Fully free (CC0). Major festivals (Coachella, Glastonbury, Lollapalooza) reasonably well-documented with annual editions, performer lists, and location data.
- Links to MusicBrainz, Spotify, Discogs IDs for cross-referencing.
- Inconsistent coverage for smaller festivals (~33% of performers at mid-tier festivals have Wikidata items).

### RSS Feeds
- News/announcement feeds, not structured data. Low utility for programmatic use.

---

## Cross-Reference Analysis

The core question: "Which of my tracked artists are playing at festival X?"

| Approach | How It Works | Feasibility |
|----------|-------------|-------------|
| **Ticketmaster** | Query festival-type events, extract `attractions` array, match against tracked artist IDs | Good — already in your stack |
| **Bandsintown** | For each tracked artist, query events, flag multi-artist `lineup` matches | Good but N API calls (one per artist) |
| **Songkick** | Query festivals by area, get `performance` array, match artist IDs | Best UX but $500/mo |
| **MusicBrainz** | Query event entity with `artist-rels`, match MusicBrainz IDs | Free but slow (1 req/sec), data may lag |
| **JamBase** | Cross-ID matching (Spotify, MusicBrainz, TM) built in | Excellent if cost works |

---

## Summary Table

| API | Public? | Festival Lineups? | Free? | Commercial OK? | Best For |
|-----|---------|-------------------|-------|----------------|----------|
| **Ticketmaster** | Yes | Moderate (attractions array) | Yes (5K/day) | Yes | Primary source (in use) |
| **Bandsintown** | Yes (approval) | Good (lineup array) | Yes | Needs approval | Best free complement to TM |
| **Songkick** | Restricted | Excellent (performance array) | No ($500/mo) | With license | Best data if budget allows |
| **JamBase** | Contact sales | Very good | Trial only | With agreement | Enterprise-grade |
| **MusicBrainz** | Yes | Variable (community) | Yes (CC0) | Yes | Free ID normalization |
| **PredictHQ** | Yes | No lineups | Trial + free | Yes | Event intelligence only |
| **Setlist.fm** | Yes | No festival endpoints | Yes | Unclear | Post-show setlists only |
| **Eventbrite** | Yes | No structured lineups | Yes (500/day) | Yes | Not useful |
| **Spotify** | Yes | No event data | Yes | Yes | Artist metadata only |

---

## Recommended Strategy for Vibes.live

### Phase 1: Maximize Ticketmaster (No Additional Cost)
- Filter Discovery API results for festival-type events using `classificationName=Festival`
- Extract `_embedded.attractions` array from festival events for lineup data
- For each tracked artist's TM attraction ID, check if they appear in any festival's attractions list
- This leverages the existing pipeline with minimal changes

### Phase 2: Add Bandsintown (Free, Requires Approval)
- Apply for a Bandsintown `app_id` with commercial use case
- For each tracked artist, query upcoming events
- Festival events have multi-artist `lineup` arrays
- Merge with TM data to fill coverage gaps (Bandsintown covers many indie/international festivals TM does not)
- Cache aggressively to stay within rate limits

### Phase 3: Add MusicBrainz for ID Normalization (Free)
- Use MusicBrainz as a canonical ID layer to match artists across TM, Bandsintown, Spotify
- Query MusicBrainz event entities for additional festival data
- Rate limit: 1 req/sec — use for batch enrichment, not real-time

### Phase 4 (If Revenue Supports It): Songkick or JamBase
- **Songkick** ($500+/mo): Best lineup quality, dedicated festival filter, performance array with billing info
- **JamBase** (custom): Deepest historical data, built-in cross-platform ID matching

### What NOT to Pursue
- Spotify API (no event data), Setlist.fm (no festival endpoints), DICE/Festicket (no public API), Eventbrite (poor festival coverage), PredictHQ (no lineup data), Music Festival Wizard (no API)

---

## Action Items

1. **Immediate:** Test TM Discovery API festival classification filtering and attractions array extraction against known festivals
2. **Short-term:** Apply for Bandsintown `app_id` (written consent process)
3. **Design decision:** Given the "Add Festival" flow in Phase I2 — should users search TM/Bandsintown, or manually enter festival details with a "suggest" flow, or both?
4. **Architecture decision:** Where does festival lineup enrichment run? Edge Function on cron? On-demand when viewing a festival?
