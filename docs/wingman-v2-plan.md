# Wingman v2 — Multi-User iOS App

## Context

Wingman is currently a single-user personal concert tracker with file-based storage (`wingman_config.json`, `docs/summary.json`), a FastAPI backend, React frontend, and GitHub Actions for daily Ticketmaster data fetching. The architecture is fundamentally single-user: one config file, one set of OAuth tokens, one notification topic, hardcoded center city.

The goal is to evolve Wingman into a **multi-user product** where each user can:
- Track their own artists/venues from an iOS app (and eventually web)
- Connect their Spotify account for artist discovery
- Receive personalized push notifications for new shows and on-sale alerts
- Benefit from a **shared pool** of concert data (one TM query per artist, not per user)

The current Wingman repo stays as-is for personal use. A **new repo** will house the v2 product.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Mobile | React Native + Expo |
| Web | Deferred — iOS first |
| Backend/DB | Supabase (Postgres + Auth + Edge Functions + RLS) |
| Auth | Supabase Auth — email OTP, invite codes |
| Data Source | Ticketmaster Discovery API v2 (shared pool) |
| Data Pipeline | Supabase Edge Function (Deno) on daily cron |
| Notifications | Expo Push Notifications (APNs) |
| Spotify | In-app OAuth via Expo AuthSession, tokens in Supabase |
| Geocoding | Nominatim OSM (cached in venues table) |
| Monorepo | Turborepo |

---

## Project Structure (New Repo: `wingman-app`)

```
wingman-app/
├── apps/
│   ├── mobile/                    # Expo React Native app
│   │   ├── app/                   # Expo Router (file-based routing)
│   │   │   ├── (auth)/            # Auth screens (login, invite code)
│   │   │   ├── (tabs)/            # Main tab navigator
│   │   │   │   ├── feed.tsx       # Upcoming shows feed
│   │   │   │   ├── artists.tsx    # Artist management + Spotify sync
│   │   │   │   ├── map.tsx        # Concert map
│   │   │   │   └── settings.tsx   # Preferences, Spotify, account
│   │   │   └── _layout.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── app.json
│   │   └── package.json
│   └── web/                       # Future: deferred (iOS first)
├── packages/
│   ├── shared/                    # Shared types, constants, utilities
│   │   ├── src/
│   │   │   ├── types.ts           # TypeScript types for DB schema
│   │   │   ├── constants.ts       # Shared constants
│   │   │   └── utils.ts           # Date formatting, show key logic
│   │   └── package.json
│   └── supabase-client/           # Typed Supabase client wrapper
│       ├── src/
│       │   ├── client.ts
│       │   └── hooks.ts           # React hooks for Supabase queries
│       └── package.json
├── supabase/
│   ├── migrations/                # SQL migrations (schema)
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_rls_policies.sql
│   │   └── 003_seed_data.sql
│   ├── functions/                 # Edge Functions (Deno)
│   │   ├── fetch-concerts/        # Daily TM data pipeline
│   │   │   └── index.ts
│   │   ├── sync-spotify/          # Spotify artist sync
│   │   │   └── index.ts
│   │   └── send-notifications/    # Push notification delivery
│   │       └── index.ts
│   └── config.toml
├── turbo.json
├── package.json
└── README.md
```

---

## Database Schema

### Core Tables

```sql
-- Users are managed by Supabase Auth (auth.users)
-- This table extends the auth user with app-specific profile data
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  display_name text,
  center_city text default 'Des Moines, IA',
  center_lat double precision,
  center_lon double precision,
  notifications_enabled boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Invite codes for controlled access
create table invite_codes (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  created_by uuid references profiles(id),
  max_uses integer default 1,
  times_used integer default 0,
  expires_at timestamptz,
  created_at timestamptz default now()
);

-- Track which invite code a user redeemed
create table invite_redemptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  invite_code_id uuid references invite_codes(id),
  redeemed_at timestamptz default now()
);

-- Shared artist pool (all users contribute)
create table artists (
  id uuid primary key default gen_random_uuid(),
  name text unique not null,
  tm_attraction_id text,          -- Ticketmaster attraction ID (for precise matching)
  spotify_id text,
  genre text,
  tour_url text,
  image_url text,
  last_tm_fetch timestamptz,
  created_at timestamptz default now()
);

-- Shared venue pool
create table venues (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  city text,
  state text,
  country text default 'US',
  lat double precision,
  lon double precision,
  tm_venue_id text unique,
  created_at timestamptz default now()
);

-- Shared concert/event pool (from TM API)
create table events (
  id uuid primary key default gen_random_uuid(),
  tm_event_id text unique not null,
  artist_id uuid references artists(id) on delete cascade,
  venue_id uuid references venues(id),
  event_name text not null,
  event_date date,
  event_time time,
  event_datetime timestamptz,
  on_sale boolean default true,
  sale_start timestamptz,          -- public on-sale datetime
  start_tbd boolean default false,
  presales jsonb default '[]',     -- array of {name, start, end}
  price_min numeric,
  price_max numeric,
  ticket_url text,
  raw_tm_data jsonb,               -- full TM event object for reference
  first_seen_at timestamptz default now(),
  last_seen_at timestamptz default now(),
  removed_at timestamptz           -- null = still on TM; set when no longer returned
);

-- User's artist subscriptions
create table user_artists (
  user_id uuid references profiles(id) on delete cascade,
  artist_id uuid references artists(id) on delete cascade,
  paused boolean default false,
  added_at timestamptz default now(),
  primary key (user_id, artist_id)
);

-- User's venue subscriptions
create table user_venues (
  user_id uuid references profiles(id) on delete cascade,
  venue_id uuid references venues(id) on delete cascade,
  is_local boolean default false,
  paused boolean default false,
  added_at timestamptz default now(),
  primary key (user_id, venue_id)
);

-- Spotify tokens per user (encrypted at rest via Supabase Vault)
create table spotify_connections (
  user_id uuid primary key references profiles(id) on delete cascade,
  access_token text not null,
  refresh_token text not null,
  expires_at timestamptz not null,
  scope text,
  connected_at timestamptz default now()
);

-- Push notification tokens (one per device)
create table push_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  expo_push_token text unique not null,
  device_name text,
  platform text,                    -- 'ios' or 'android'
  created_at timestamptz default now()
);

-- Notification log (what was sent, for dedup and history)
create table notification_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  event_id uuid references events(id),
  notification_type text not null,  -- 'new_show', 'on_sale_soon', 'venue_event'
  sent_at timestamptz default now(),
  message_preview text
);

-- Dismissed Spotify suggestions per user
create table dismissed_suggestions (
  user_id uuid references profiles(id) on delete cascade,
  artist_name text not null,
  spotify_id text,
  dismissed_at timestamptz default now(),
  resurface_after timestamptz,
  primary key (user_id, artist_name)
);
```

### Row-Level Security (RLS) Policies

```sql
-- Profiles: users can only read/update their own
alter table profiles enable row level security;
create policy "Users read own profile" on profiles for select using (auth.uid() = id);
create policy "Users update own profile" on profiles for update using (auth.uid() = id);

-- Artists & Venues & Events: readable by all authenticated users
alter table artists enable row level security;
create policy "Authenticated read artists" on artists for select using (auth.role() = 'authenticated');
create policy "Authenticated insert artists" on artists for insert with check (auth.role() = 'authenticated');

alter table venues enable row level security;
create policy "Authenticated read venues" on venues for select using (auth.role() = 'authenticated');

alter table events enable row level security;
create policy "Authenticated read events" on events for select using (auth.role() = 'authenticated');

-- User subscriptions: users manage their own
alter table user_artists enable row level security;
create policy "Users manage own artist subs" on user_artists for all using (auth.uid() = user_id);

alter table user_venues enable row level security;
create policy "Users manage own venue subs" on user_venues for all using (auth.uid() = user_id);

-- Spotify & push tokens: users manage their own
alter table spotify_connections enable row level security;
create policy "Users manage own spotify" on spotify_connections for all using (auth.uid() = user_id);

alter table push_tokens enable row level security;
create policy "Users manage own tokens" on push_tokens for all using (auth.uid() = user_id);

-- Service role (Edge Functions) bypasses RLS for data pipeline operations
```

---

## Edge Functions

### 1. `fetch-concerts` (Daily Cron)

**Trigger:** Supabase cron (pg_cron) — daily at 10:00 UTC

**Logic (ported from current `backend/ticketmaster.py` + `scripts/fetch_tm_data.py`):**
1. Query `artists` table for all unique artists (across all users)
2. For each artist, call TM Discovery API: `GET /events?keyword={name}&classificationName=music`
3. Filter to North America (US, CA, MX)
4. Match by attraction name (fuzzy substring, same logic as current `ticketmaster.py`)
5. Upsert into `events` table (dedup by `tm_event_id`)
6. Mark events not returned by TM as `removed_at = now()` (soft delete)
7. Geocode new venues via Nominatim → upsert into `venues` table
8. Update `artists.last_tm_fetch` timestamp
9. Trigger `send-notifications` function after completion

**Reusable from current codebase:**
- TM event parsing logic from `backend/ticketmaster.py` (lines 50-180): attraction matching, presale extraction, on-sale classification
- Geocoding approach from `backend/ticketmaster.py` (Nominatim with 1 req/sec rate limit)
- North America filtering logic

### 2. `send-notifications` (After Fetch)

**Trigger:** Called by `fetch-concerts` after successful data pipeline run

**Logic:**
1. Query `events` where `first_seen_at` is within last 24 hours (new events)
2. Query `events` where `sale_start` is within next 48 hours (on-sale imminent)
3. For each user with `notifications_enabled = true`:
   a. Filter new events to those matching user's subscribed artists/venues
   b. Filter on-sale-imminent to user's subscribed artists
   c. Skip events already in `notification_log` for this user
   d. Format personalized message
   e. Send via Expo Push API to all user's registered `push_tokens`
   f. Log sent notifications to `notification_log`

### 3. `sync-spotify` (On-Demand)

**Trigger:** Called from app when user taps "Sync Spotify"

**Logic:**
1. Read user's Spotify tokens from `spotify_connections`
2. Refresh access token if expired
3. Fetch followed artists from Spotify API
4. Compare against user's `user_artists` subscriptions
5. Return diff: { `on_spotify_not_wingman`: [...], `on_wingman_not_spotify`: [...] }
6. User picks which to add/follow in the app UI
7. Subsequent API calls from the app handle the actual adds/follows

---

## React Native App (Expo)

### Auth Flow
1. User opens app → sees login screen
2. First-time: enters invite code → validated against `invite_codes` table
3. Enters email → Supabase sends OTP
4. Enters OTP → authenticated, profile created
5. Subsequent opens: auto-authenticated via Supabase session

### Tab Structure
| Tab | Content |
|-----|---------|
| **Feed** | Chronological list of upcoming shows for subscribed artists. Cards show artist, venue, date, on-sale status. Tap for ticket link. |
| **Artists** | List of subscribed artists with genre badges. Add artist (search), remove, pause. "Sync with Spotify" button. |
| **Map** | react-native-maps with pins for upcoming shows. Blue = on sale, orange = coming soon. Centered on user's center city. |
| **Settings** | Center city, notification preferences, Spotify connection, invite codes (to share), account/logout. |

### Key Dependencies
```json
{
  "expo": "~52.x",
  "expo-router": "~4.x",
  "expo-notifications": "~0.x",
  "expo-auth-session": "~6.x",
  "@supabase/supabase-js": "^2.x",
  "react-native-maps": "1.x",
  "@expo/vector-icons": "*",
  "zustand": "^5.x"
}
```

---

## What Gets Reused from Current Wingman

| Current File | Reuse | How |
|-------------|-------|-----|
| `backend/ticketmaster.py` | **Core TM parsing logic** | Port attraction matching, presale extraction, on-sale classification to TypeScript for Edge Function |
| `scripts/notify_changes.py` | **Notification diffing pattern** | Same concept (baseline vs. fresh), but per-user and via Expo Push instead of ntfy.sh |
| `backend/spotify.py` | **Spotify API patterns** | Port OAuth token refresh, API call patterns to TypeScript |
| `frontend/src/components/ArtistsSummaryTab.jsx` | **UI patterns** | Card layout, genre badges, show grouping — adapt for React Native |
| `frontend/src/components/ConcertMap.jsx` | **Map pin logic** | Pin coloring (blue/orange), tooltip format — adapt for react-native-maps |
| `schemas/*.schema.json` | **Data shape reference** | Inform Postgres schema design (already done above) |

---

## Decisions

- **MVP scope:** Artists + Venues (no festivals for v2 MVP)
- **TM API key:** Single shared key, managed centrally as a Supabase secret
- **Web:** Deferred — iOS first, web later
- **Current Wingman:** Stays as personal instance, no migration

---

## Implementation Phases

### Phase 1: Foundation
**Deliverables:** New repo, Supabase project, auth working in Expo app

- [ ] Create `wingman-app` repo with Turborepo structure
- [ ] Set up Supabase project (free tier)
- [ ] Run SQL migrations (schema + RLS policies)
- [ ] Create Expo app with expo-router
- [ ] Implement invite code validation screen
- [ ] Implement email OTP login via Supabase Auth
- [ ] Create profile on first login (center city prompt)
- [ ] Basic navigation shell (4 tabs with placeholder screens)

### Phase 2: Artist + Venue Management + Concert Data
**Deliverables:** Users can add artists/venues, daily TM data flows in

- [ ] Artist search + add screen (search by name, creates in shared `artists` table + adds `user_artists` subscription)
- [ ] Artist list screen (view subscribed artists, pause/remove)
- [ ] Venue search + add screen (search by name, add to `user_venues`)
- [ ] Venue list screen (local vs. travel toggle)
- [ ] Port TM fetch logic to Edge Function (`fetch-concerts`) — TypeScript/Deno port of `ticketmaster.py`
- [ ] Set up pg_cron for daily fetch (TM API key stored as Supabase secret)
- [ ] Concert feed screen (list events for subscribed artists/venues, sorted by date)
- [ ] Event detail (date, venue, on-sale status, ticket link)

### Phase 3: Map + Coming Soon
**Deliverables:** Interactive map, on-sale tracking

- [ ] Map screen with react-native-maps
- [ ] Show pins (blue = on sale, orange = coming soon) centered on user's center city
- [ ] Venue pins (violet) for subscribed venues
- [ ] Pin tap → event detail
- [ ] Coming Soon section in feed (not-yet-on-sale, presale windows)

### Phase 4: Spotify Integration
**Deliverables:** In-app Spotify connect + artist sync

- [ ] Spotify OAuth via Expo AuthSession (redirect back to app)
- [ ] Store tokens in `spotify_connections` (per user, encrypted via Supabase Vault)
- [ ] "Sync Spotify" button → fetches followed artists → shows diff
- [ ] Add from Spotify / Follow from Wingman flows
- [ ] Dismissed suggestions (6-month resurface)
- [ ] Listening history suggestions (top artists, recently played)

### Phase 5: Push Notifications
**Deliverables:** Personalized daily push alerts

- [ ] Register Expo push token on app launch → store in `push_tokens`
- [ ] `send-notifications` Edge Function: per-user filtering of new events, Expo Push API
- [ ] Notification types: new show, new venue event, on-sale within 48 hours
- [ ] Notification preferences in Settings (enable/disable, per-type toggles)
- [ ] Notification history / activity feed

### Phase 6: Polish + TestFlight Beta
**Deliverables:** Invite system, TestFlight distribution

- [ ] Invite code generation (admin via Supabase dashboard initially)
- [ ] Users can view their invite code in Settings and share it
- [ ] App icon, splash screen, App Store screenshots
- [ ] TestFlight build + distribution to beta testers
- [ ] Error handling, loading states, pull-to-refresh, empty states
- [ ] Offline support (cache last-fetched data locally)
- [ ] Rate limiting on Edge Functions

---

## Verification Plan

After each phase, verify:

1. **Phase 1:** Can create account with invite code + OTP, see empty tab shell
2. **Phase 2:** Can add artist/venue, see concert data appear after Edge Function runs (trigger manually via Supabase dashboard)
3. **Phase 3:** Map shows pins for subscribed artists' events + venue pins
4. **Phase 4:** Can connect Spotify, see suggestion list, add artists from Spotify
5. **Phase 5:** Receive push notification on physical device when new show is detected
6. **Phase 6:** Full flow: invite code → signup → add artists → get notifications → share invite with friend

---

## Open Questions for Future Discussion

1. **Festivals** — Defer to post-MVP. Current Wingman's festival approach (keyword search on TM) is limited. May need a different discovery model.
2. **Data retention** — How long to keep old events? Recommendation: soft-delete with `removed_at`, purge after 90 days.
3. **Web interface** — Can add later using React Native Web (shared components) or a separate Vite + React app pulling from the same Supabase backend.
4. **Scaling TM quota** — With shared pool, 200 unique artists = 200 calls/day. At ~1000 unique artists, we'd need a second TM API key or smarter batching. Cross that bridge when we get there.
5. **App Store submission** — TestFlight is straightforward, but App Store review requires Apple Developer Program ($99/yr). Plan for this before Phase 6.
