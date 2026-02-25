import { useState, useEffect } from 'react'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

const GENRE_COLORS = {
  'Country / Americana':   'bg-amber-100 text-amber-800',
  'Indie / Alt-Rock':      'bg-blue-100  text-blue-800',
  'Electronic / Art-Rock': 'bg-purple-100 text-purple-800',
  'Other':                 'bg-slate-100 text-slate-700',
}

function genreColor(genre) {
  return GENRE_COLORS[genre] || GENRE_COLORS['Other']
}

// ── Format a UTC ISO datetime for display ─────────────────────────────────────
function formatDatetime(isoStr) {
  if (!isoStr) return null
  try {
    return new Date(isoStr).toLocaleString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
    })
  } catch {
    return isoStr
  }
}

// ── Presale badge list ────────────────────────────────────────────────────────
function PresaleList({ presales }) {
  if (!presales || presales.length === 0) return null
  return (
    <ul className="mt-1.5 space-y-1">
      {presales.map((p, i) => (
        <li key={i} className="flex items-start gap-1.5 text-xs text-slate-500">
          <span className="inline-block mt-0.5 w-1.5 h-1.5 rounded-full bg-violet-400 flex-shrink-0" />
          <span>
            <span className="font-medium text-slate-700">{p.name}</span>
            {p.start_datetime && (
              <span className="ml-1">— starts {formatDatetime(p.start_datetime)}</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  )
}

// ── Individual show row ───────────────────────────────────────────────────────
function ShowRow({ show }) {
  const onsaleLabel = show.onsale_tbd
    ? 'On-sale date TBD'
    : show.onsale_datetime
    ? `On sale ${formatDatetime(show.onsale_datetime)}`
    : 'On-sale date not announced'

  return (
    <li className="text-sm border-t border-slate-50 pt-2 mt-2 first:border-0 first:pt-0 first:mt-0">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-medium text-slate-800">{show.date}</span>
          <span className="text-slate-400 mx-1">&middot;</span>
          <span className="text-slate-600">{show.venue}</span>
          <span className="text-slate-400 mx-1">&middot;</span>
          <span className="text-slate-500">{show.city}</span>
        </div>
        {show.ticketmaster_url && (
          <a
            href={show.ticketmaster_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="flex-shrink-0 text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
          >
            TM &rarr;
          </a>
        )}
      </div>

      {/* On-sale info */}
      <div className="mt-1 flex items-center gap-1.5">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
        <span className="text-xs text-amber-700 font-medium">{onsaleLabel}</span>
      </div>

      {/* Presales */}
      <PresaleList presales={show.presales} />
    </li>
  )
}

// ── Venue event row (artist-first layout) ─────────────────────────────────────
function VenueEventRow({ event }) {
  const onsaleLabel = event.onsale_tbd
    ? 'On-sale date TBD'
    : event.onsale_datetime
    ? `On sale ${formatDatetime(event.onsale_datetime)}`
    : 'On-sale date not announced'

  return (
    <li className="text-sm border-t border-slate-50 pt-2 mt-2 first:border-0 first:pt-0 first:mt-0">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-medium text-slate-800">{event.artist}</span>
          <span className="text-slate-400 mx-1">&middot;</span>
          <span className="text-slate-600">{event.date}</span>
          <span className="text-slate-400 mx-1">&middot;</span>
          <span className="text-slate-500">{event.city}</span>
        </div>
        {event.ticketmaster_url && (
          <a
            href={event.ticketmaster_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="flex-shrink-0 text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
          >
            TM &rarr;
          </a>
        )}
      </div>
      <div className="mt-1 flex items-center gap-1.5">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
        <span className="text-xs text-amber-700 font-medium">{onsaleLabel}</span>
      </div>
      <PresaleList presales={event.presales} />
    </li>
  )
}

// ── Festival event row ────────────────────────────────────────────────────────
function FestivalEventRow({ event }) {
  const onsaleLabel = event.onsale_tbd
    ? 'On-sale date TBD'
    : event.onsale_datetime
    ? `On sale ${formatDatetime(event.onsale_datetime)}`
    : 'On-sale date not announced'

  return (
    <li className="text-sm border-t border-slate-50 pt-2 mt-2 first:border-0 first:pt-0 first:mt-0">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-medium text-slate-800">{event.date}</span>
          <span className="text-slate-400 mx-1">&middot;</span>
          <span className="text-slate-600">{event.venue}</span>
          <span className="text-slate-400 mx-1">&middot;</span>
          <span className="text-slate-500">{event.city}</span>
        </div>
        {event.ticketmaster_url && (
          <a
            href={event.ticketmaster_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="flex-shrink-0 text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
          >
            TM &rarr;
          </a>
        )}
      </div>
      {event.event_name !== event.tracked_festival && (
        <p className="text-xs text-slate-400 mt-0.5 italic">{event.event_name}</p>
      )}
      <div className="mt-1 flex items-center gap-1.5">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
        <span className="text-xs text-amber-700 font-medium">{onsaleLabel}</span>
      </div>
      <PresaleList presales={event.presales} />
    </li>
  )
}

// ── Per-venue card ────────────────────────────────────────────────────────────
function VenueEventCard({ venueName, venueUrl, events }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="card transition-all">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full p-4 text-left flex items-center gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 min-w-0">
            {venueUrl ? (
              <a
                href={venueUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className="font-semibold text-slate-900 hover:text-indigo-600 hover:underline truncate"
              >
                {venueName}
              </a>
            ) : (
              <span className="font-semibold text-slate-900 truncate">{venueName}</span>
            )}
          </div>
          <div className="mt-1">
            <span className="text-xs bg-violet-100 text-violet-800 px-2 py-0.5 rounded-full font-medium">
              {events.length} coming soon
            </span>
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-slate-50 px-4 pb-4">
          <ul className="mt-3">
            {events.map((ev, i) => (
              <VenueEventRow key={i} event={ev} />
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Per-festival card ─────────────────────────────────────────────────────────
function FestivalEventCard({ festivalName, festivalUrl, events }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="card transition-all">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full p-4 text-left flex items-center gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 min-w-0">
            {festivalUrl ? (
              <a
                href={festivalUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className="font-semibold text-slate-900 hover:text-indigo-600 hover:underline truncate"
              >
                {festivalName}
              </a>
            ) : (
              <span className="font-semibold text-slate-900 truncate">{festivalName}</span>
            )}
          </div>
          <div className="mt-1">
            <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-medium">
              {events.length} coming soon
            </span>
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-slate-50 px-4 pb-4">
          <ul className="mt-3">
            {events.map((ev, i) => (
              <FestivalEventRow key={i} event={ev} />
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Per-artist card ───────────────────────────────────────────────────────────
function ComingSoonCard({ artist, genre, url, shows }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="card transition-all">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full p-4 text-left flex items-center gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 min-w-0">
            {url ? (
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className="font-semibold text-slate-900 hover:text-indigo-600 hover:underline truncate"
              >
                {artist}
              </a>
            ) : (
              <span className="font-semibold text-slate-900 truncate">{artist}</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            <span className={`badge-genre ${genreColor(genre)}`}>{genre}</span>
            <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full font-medium">
              {shows.length} coming soon
            </span>
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-slate-50 px-4 pb-4">
          <ul className="mt-3">
            {shows.map((show, i) => (
              <ShowRow key={i} show={show} />
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Entities not found on Ticketmaster ───────────────────────────────────────
function NotFoundSection({ label, items, configItems, explanation }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="card">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full p-4 text-left flex items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-500">
            Not found on Ticketmaster — {label}
          </span>
          <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-medium">
            {items.length}
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-slate-50 px-4 pb-4">
          <p className="text-xs text-slate-400 mt-3 mb-3">{explanation}</p>
          <ul className="space-y-1.5">
            {items.map(name => (
              <li key={name} className="flex items-center gap-2 text-sm text-slate-600">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-300 flex-shrink-0" />
                {configItems[name]?.url ? (
                  <a
                    href={configItems[name].url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-indigo-600 hover:underline"
                  >
                    {name}
                  </a>
                ) : (
                  name
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Loading / error helpers ───────────────────────────────────────────────────
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
    </div>
  )
}

function ErrorBox({ message }) {
  return (
    <div className="card p-6 text-center">
      <p className="text-red-600 font-medium">Failed to load data</p>
      <p className="text-slate-500 text-sm mt-1">{message}</p>
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function ComingSoonTab() {
  const [data, setData]         = useState(null)
  const [config, setConfig]     = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  async function loadData() {
    if (DEMO) {
      const res  = await fetch(import.meta.env.BASE_URL + 'static-data.json')
      const json = await res.json()
      setData({
        api_configured:    true,
        shows:             json.coming_soon || [],
        venue_events:      [],
        festival_events:   [],
        last_fetched:      json.coming_soon_fetched || null,
      })
      setConfig(json.config || {})
    } else {
      const [apiData, cfg] = await Promise.all([
        fetch('/api/coming-soon').then(r => r.json()),
        fetch('/api/config').then(r => r.json()),
      ])
      setData(apiData)
      setConfig(cfg)
    }
  }

  useEffect(() => {
    loadData()
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleRefresh() {
    setRefreshing(true)
    try {
      const res = await fetch('/api/coming-soon?force=true')
      setData(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setRefreshing(false)
    }
  }

  if (loading)  return <LoadingSpinner />
  if (error)    return <ErrorBox message={error} />

  // Not configured
  if (!data?.api_configured) {
    return (
      <div className="card p-8 text-center space-y-3">
        <div className="text-3xl">🎟</div>
        <p className="font-semibold text-slate-800">Ticketmaster API not configured</p>
        <p className="text-sm text-slate-500 max-w-xs mx-auto">
          Add your free Discovery API key in the Settings tab to see upcoming on-sale dates and presale windows for your tracked artists, venues, and festivals.
        </p>
        <a
          href="https://developer.ticketmaster.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-sm text-indigo-600 hover:underline"
        >
          Get a free API key &rarr;
        </a>
      </div>
    )
  }

  const shows            = data.shows || []
  const artistsNotFound  = data.artists_not_found || []
  const venueEvents      = data.venue_events || []
  const venuesNotFound   = data.venues_not_found || []
  const festivalEvents   = data.festival_events || []
  const festivalsNotFound = data.festivals_not_found || []
  const configArtists    = config?.artists || {}
  const configVenues     = config?.venues || {}
  const configFestivals  = config?.festivals || {}

  // Group artist shows by artist (most shows first)
  const byArtist = {}
  for (const show of shows) {
    if (!byArtist[show.artist]) {
      byArtist[show.artist] = { genre: show.genre, shows: [] }
    }
    byArtist[show.artist].shows.push(show)
  }
  const artistGroups = Object.entries(byArtist).sort(
    ([, a], [, b]) => b.shows.length - a.shows.length
  )

  // Group venue events by tracked venue
  const byVenue = {}
  for (const ev of venueEvents) {
    if (!byVenue[ev.tracked_venue]) byVenue[ev.tracked_venue] = []
    byVenue[ev.tracked_venue].push(ev)
  }
  const venueGroups = Object.entries(byVenue).sort(
    ([, a], [, b]) => b.length - a.length
  )

  // Group festival events by tracked festival
  const byFestival = {}
  for (const ev of festivalEvents) {
    if (!byFestival[ev.tracked_festival]) byFestival[ev.tracked_festival] = []
    byFestival[ev.tracked_festival].push(ev)
  }
  const festivalGroups = Object.entries(byFestival).sort(
    ([, a], [, b]) => b.length - a.length
  )

  const totalNotYetOnSale = shows.length + venueEvents.length + festivalEvents.length

  return (
    <div className="space-y-6">
      {/* ── Meta bar ── */}
      <div className="card p-4 flex flex-wrap gap-4 text-sm text-slate-600">
        <div>
          <span className="font-semibold text-slate-800">Not yet on sale: </span>
          {totalNotYetOnSale} show{totalNotYetOnSale !== 1 ? 's' : ''}
        </div>
        <div>
          <span className="font-semibold text-slate-800">Artists: </span>
          {artistGroups.length}
        </div>
        {venueGroups.length > 0 && (
          <div>
            <span className="font-semibold text-slate-800">Venues: </span>
            {venueGroups.length}
          </div>
        )}
        {festivalGroups.length > 0 && (
          <div>
            <span className="font-semibold text-slate-800">Festivals: </span>
            {festivalGroups.length}
          </div>
        )}
        {data.last_fetched && (
          <div>
            <span className="font-semibold text-slate-800">Last checked: </span>
            {new Date(data.last_fetched).toLocaleString(undefined, {
              month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
            })}
          </div>
        )}
        {!DEMO && (
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="ml-auto btn-ghost text-xs border border-slate-200 flex items-center gap-1.5"
          >
            {refreshing ? (
              <>
                <span className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                Refreshing…
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </>
            )}
          </button>
        )}
      </div>

      {/* ── Explainer ── */}
      <div className="flex items-start gap-2 text-xs text-slate-400 px-1">
        <span className="inline-block mt-0.5 w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
        <span>
          Shows listed here are <strong className="text-slate-500">announced but not yet on public sale</strong>.
          Presale windows (violet dots) may allow early access.
          {!DEMO && <span className="ml-1">Data refreshes every 6 hours.</span>}
        </span>
      </div>

      {/* ── Artists section ── */}
      {artistGroups.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-400 px-1">Artists</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {artistGroups.map(([artist, { genre, shows: artistShows }]) => (
              <ComingSoonCard
                key={artist}
                artist={artist}
                genre={genre}
                url={configArtists[artist]?.url || null}
                shows={artistShows}
              />
            ))}
          </div>
        </div>
      )}

      {artistGroups.length === 0 && venueGroups.length === 0 && festivalGroups.length === 0 && (
        <div className="card p-8 text-center text-slate-400 text-sm italic">
          No upcoming shows with future on-sale dates found for your tracked artists, venues, or festivals.
        </div>
      )}

      {/* ── Venues section ── */}
      {venueGroups.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-400 px-1">Venues</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {venueGroups.map(([venueName, events]) => (
              <VenueEventCard
                key={venueName}
                venueName={venueName}
                venueUrl={configVenues[venueName]?.url || null}
                events={events}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Festivals section ── */}
      {festivalGroups.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-400 px-1">Festivals</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {festivalGroups.map(([festivalName, events]) => (
              <FestivalEventCard
                key={festivalName}
                festivalName={festivalName}
                festivalUrl={configFestivals[festivalName]?.url || null}
                events={events}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Not found on Ticketmaster ── */}
      {!DEMO && artistsNotFound.length > 0 && (
        <NotFoundSection
          label="Artists"
          items={artistsNotFound}
          configItems={configArtists}
          explanation="These tracked artists returned no results on Ticketmaster. They may tour under a different name, not list shows on Ticketmaster, or not have upcoming North America dates."
        />
      )}
      {!DEMO && venuesNotFound.length > 0 && (
        <NotFoundSection
          label="Venues"
          items={venuesNotFound}
          configItems={configVenues}
          explanation="These tracked venues returned no matching results on Ticketmaster. The venue may use a different name on Ticketmaster, or may have no upcoming shows with future on-sale dates."
        />
      )}
      {!DEMO && festivalsNotFound.length > 0 && (
        <NotFoundSection
          label="Festivals"
          items={festivalsNotFound}
          configItems={configFestivals}
          explanation="These tracked festivals returned no matching results on Ticketmaster. The festival may not yet be listed on Ticketmaster, or tickets may already be on sale."
        />
      )}
    </div>
  )
}
