# Spotify Sync Skill

Run this when the user asks to do a Spotify sync, sync Spotify, or check Spotify follows.

---

## Pre-flight checks

1. Verify Spotify is connected: `GET http://127.0.0.1:8000/api/spotify/status`
   - If `connected: false` → tell user to go to Settings → Spotify and click Connect Spotify first. Stop.
2. Read current Wingman config: `GET http://127.0.0.1:8000/api/config`
   - Extract `spotify_client_id` and `spotify_client_secret`
   - Extract current `artists` map (keys are artist names)
3. Get a valid Spotify access token using `backend/spotify.py`:
   - `from backend.spotify import get_valid_access_token`
   - `token = get_valid_access_token(client_id, client_secret)`
   - If None → tell user token refresh failed, ask them to reconnect. Stop.

---

## Phase 1 — Spotify follows not in Wingman

**Goal:** For each artist the user follows on Spotify that isn't tracked in Wingman, ask if they want to add it.

**Steps:**

1. Paginate through all Spotify followed artists:
   - `GET https://api.spotify.com/v1/me/following?type=artist&limit=50`
   - Follow `next` cursor until exhausted
   - Collect full list: `{id, name, genres[], popularity, external_urls.spotify}`

2. Diff against Wingman artists (case-insensitive name match):
   - `new_artists = [a for a in spotify_follows if a.name not in wingman_artists]`

3. If none: skip to Phase 2.

4. Tell user: "You follow **N** artists on Spotify that aren't in Wingman. I'll go through them."

5. For each new artist, present:
   ```
   ➕ [Artist Name]
   Genres: indie rock, alternative
   Spotify: https://open.spotify.com/artist/...

   Add to Wingman? (yes / no / skip all remaining)
   ```
   Wait for response before moving to next artist.

6. If user says **yes**:
   - Search for official tour page URL using web search:
     - First try: `[Artist Name] official tour dates site:artistname.com`
     - Look for the artist's own domain (not Ticketmaster, Songkick, etc.)
     - Target a `/tour`, `/shows`, `/tickets`, or `/dates` subpage if it exists
     - If no dedicated tour page found, use the artist's homepage
   - Add to Wingman: `POST http://127.0.0.1:8000/api/artists`
     ```json
     {"name": "[Artist Name]", "url": "[discovered URL]", "genre": "[primary genre]"}
     ```
   - Confirm: "Added [Artist] → [URL]"

7. If user says **no**:
   - Ask: "Dismiss for 6 months or just skip?"
   - If dismiss: `POST http://127.0.0.1:8000/api/dismissed-suggestions`
     ```json
     {"artist": "[name]", "reason": "user declined", "source": "spotify_follows"}
     ```

8. If user says **skip all remaining**: stop Phase 1, move to Phase 2.

---

## Phase 2 — Wingman artists not followed on Spotify

**Goal:** Show user all Wingman artists they're not following on Spotify as a batch checklist.

**Steps:**

1. For each artist in Wingman config (non-paused):
   - Search Spotify: `GET https://api.spotify.com/v1/search?q=[artist name]&type=artist&limit=5`
   - Find best match (exact or close name match, high popularity)
   - If found: add to `to_follow` list with `{name, spotify_id, spotify_url}`
   - If NOT found on Spotify: flag it:
     `POST http://127.0.0.1:8000/api/flagged-items`
     ```json
     {"type": "spotify_not_found", "name": "[artist name]", "note": "Not found on Spotify"}
     ```

2. If `to_follow` is empty: skip to Phase 3.

3. Present the full checklist at once:
   ```
   These Wingman artists aren't in your Spotify follows.
   Check the ones you want to follow:

   [ ] Tyler Childers  →  open.spotify.com/artist/...
   [ ] Hozier          →  open.spotify.com/artist/...
   [ ] Caamp           →  open.spotify.com/artist/...
   ...

   Reply with the numbers or names to follow (e.g. "1, 3, 5" or "all" or "none").
   ```

4. For each confirmed artist:
   - `PUT https://api.spotify.com/v1/me/following?type=artist&ids=[spotify_id]`
   - Confirm after all: "Followed N artists on Spotify."

---

## Phase 3 — Listening history suggestions

**Goal:** Surface artists from listening history not already tracked or followed.

**Steps:**

1. Fetch listening data:
   - `GET https://api.spotify.com/v1/me/top/artists?time_range=short_term&limit=50`
   - `GET https://api.spotify.com/v1/me/top/artists?time_range=medium_term&limit=50`
   - `GET https://api.spotify.com/v1/me/top/artists?time_range=long_term&limit=50`
   - `GET https://api.spotify.com/v1/me/player/recently-played?limit=50`
     (extract unique artists from tracks)

2. Build candidate list:
   - Deduplicate across all sources
   - Remove artists already in Wingman config
   - Remove artists already in Spotify follows
   - Remove dismissed artists (check `GET http://127.0.0.1:8000/api/dismissed-suggestions`
     where today < `resurface_after`)

3. If none: tell user "No new suggestions from your listening history." Done.

4. For each candidate, present with context:
   ```
   🎵 [Artist Name]
   Why: Appears in your top artists (medium-term) + recent plays
   Genres: americana, folk

   Track in Wingman + follow on Spotify? (yes / no / dismiss for 6 months)
   ```

5. If **yes**:
   - Search for tour URL (same as Phase 1 step 6)
   - `POST http://127.0.0.1:8000/api/artists` to add to Wingman
   - `PUT https://api.spotify.com/v1/me/following?type=artist&ids=[id]` to follow
   - Confirm both actions

6. If **no** → skip (no dismissal recorded)

7. If **dismiss**:
   - `POST http://127.0.0.1:8000/api/dismissed-suggestions`
     ```json
     {"artist": "[name]", "reason": "user declined", "source": "[time_range or recently_played]"}
     ```

---

## Wrap-up

After all three phases complete, summarize:

```
Spotify sync complete!

Phase 1 — Added to Wingman: N artists
Phase 2 — Followed on Spotify: N artists
Phase 3 — New suggestions added: N artists
Flagged (not on Spotify): N artists

View flagged items in Configure → Flagged Items.
```

---

## Notes

- All Spotify API calls must use `Authorization: Bearer [access_token]` header
- Token auto-refreshes via `get_valid_access_token()` — call it fresh before each phase
- Rate limits: Spotify allows ~180 requests/minute; no sleep needed for normal sync
- The `dismissed_suggestions.json` file is local-only and gitignored
- Genre mapping: use the first genre from Spotify's array; map to Wingman genre categories
  (Country/Americana, Indie/Alt-Rock, Folk/Singer-Songwriter, Electronic/Art-Rock, Other)
