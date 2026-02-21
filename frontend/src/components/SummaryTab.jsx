import { useState, useEffect } from 'react'

const GENRE_COLORS = {
  'Country / Americana':  'bg-amber-100 text-amber-800',
  'Indie / Alt-Rock':     'bg-blue-100  text-blue-800',
  'Electronic / Art-Rock':'bg-purple-100 text-purple-800',
  'Other':                'bg-slate-100 text-slate-700',
}

function genreColor(genre) {
  return GENRE_COLORS[genre] || GENRE_COLORS['Other']
}

// ── Artist card ───────────────────────────────────────────────────────────────
function ArtistCard({ name, genre, shows, paused }) {
  const [open, setOpen] = useState(false)
  const hasShows = shows && shows.length > 0

  return (
    <div className={`card transition-opacity ${paused ? 'opacity-50' : ''}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full p-4 text-left flex items-center gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-900 truncate">{name}</div>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            <span className={`badge-genre ${genreColor(genre)}`}>{genre}</span>
            {paused && <span className="badge-paused">Paused</span>}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`text-sm font-semibold ${hasShows ? 'text-emerald-600' : 'text-slate-400'}`}>
            {hasShows ? `${shows.length} show${shows.length !== 1 ? 's' : ''}` : 'None in range'}
          </span>
          <svg
            className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-50 px-4 pb-4">
          {hasShows ? (
            <ul className="mt-3 space-y-2">
              {shows.map((show, i) => (
                <li key={i} className="flex items-start justify-between gap-2 text-sm">
                  <div>
                    <span className="font-medium text-slate-800">{show.date}</span>
                    <span className="text-slate-400 mx-1">·</span>
                    <span className="text-slate-600">{show.venue}</span>
                    <span className="text-slate-400 mx-1">·</span>
                    <span className="text-slate-500">{show.city}</span>
                  </div>
                  {show.status === 'sold_out' && (
                    <span className="badge-sold-out flex-shrink-0">Sold Out</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-400 italic">No upcoming shows in range.</p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Venue card ────────────────────────────────────────────────────────────────
function VenueCard({ name, city, events, paused }) {
  const [open, setOpen] = useState(false)
  const tracked = events ? events.filter(e => e.tracked) : []

  return (
    <div className={`card transition-opacity ${paused ? 'opacity-50' : ''}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full p-4 text-left flex items-center gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-900 truncate">{name}</div>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            <span className="text-xs text-slate-500">{city}</span>
            {paused && <span className="badge-paused">Paused</span>}
            {tracked.length > 0 && (
              <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">
                {tracked.length} tracked
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-sm font-semibold text-slate-500">
            {events ? `${events.length} events` : '—'}
          </span>
          <svg
            className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {open && events && events.length > 0 && (
        <div className="border-t border-slate-50 px-4 pb-4">
          <ul className="mt-3 space-y-1.5">
            {events.map((ev, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                {ev.tracked && (
                  <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" title="Tracked artist" />
                )}
                {!ev.tracked && (
                  <span className="w-2 h-2 rounded-full bg-slate-200 flex-shrink-0" />
                )}
                <span className="font-medium text-slate-800">{ev.date}</span>
                <span className="text-slate-400">·</span>
                <span className={ev.tracked ? 'text-slate-800 font-medium' : 'text-slate-500'}>
                  {ev.artist}
                </span>
              </li>
            ))}
          </ul>
          {tracked.length > 0 && (
            <p className="mt-2 text-xs text-emerald-600">
              Green dot = tracked artist
            </p>
          )}
        </div>
      )}
      {open && (!events || events.length === 0) && (
        <div className="border-t border-slate-50 px-4 pb-4">
          <p className="mt-3 text-sm text-slate-400 italic">No events data yet.</p>
        </div>
      )}
    </div>
  )
}

// ── Section heading ───────────────────────────────────────────────────────────
function SectionHeading({ children, count }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <h2 className="text-base font-bold text-slate-700">{children}</h2>
      {count !== undefined && (
        <span className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full">{count}</span>
      )}
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function SummaryTab() {
  const [state, setState]   = useState(null)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)
  const [filter, setFilter] = useState('all') // 'all' | 'with-shows' | 'no-shows'

  useEffect(() => {
    Promise.all([
      fetch('/api/state').then(r => r.json()),
      fetch('/api/config').then(r => r.json()),
    ])
      .then(([st, cfg]) => { setState(st); setConfig(cfg) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner />
  if (error)   return <ErrorBox message={error} />

  const artistShows  = state?.artist_shows  || {}
  const venueShows   = state?.venue_shows   || {}
  const configArtists = config?.artists || {}
  const configVenues  = config?.venues  || {}

  // Build artist list, sorted: with shows first, then alpha
  const artistList = Object.entries(configArtists).map(([name, info]) => ({
    name,
    genre: info.genre || 'Other',
    paused: info.paused || false,
    shows: artistShows[name] || [],
  })).sort((a, b) => {
    if (b.shows.length !== a.shows.length) return b.shows.length - a.shows.length
    return a.name.localeCompare(b.name)
  })

  const filtered = filter === 'with-shows'
    ? artistList.filter(a => a.shows.length > 0)
    : filter === 'no-shows'
    ? artistList.filter(a => a.shows.length === 0)
    : artistList

  const localVenues  = Object.entries(configVenues).filter(([, v]) => v.is_local)
  const travelVenues = Object.entries(configVenues).filter(([, v]) => !v.is_local)

  const withShowsCount = artistList.filter(a => a.shows.length > 0).length

  return (
    <div className="space-y-8">
      {/* Meta */}
      <div className="card p-4 flex flex-wrap gap-4 text-sm text-slate-600">
        <div>
          <span className="font-semibold text-slate-800">Last run: </span>
          {state?.last_run || <span className="text-slate-400 italic">Never</span>}
        </div>
        <div>
          <span className="font-semibold text-slate-800">Center: </span>
          {state?.center || config?.center_city || '—'}
        </div>
        <div>
          <span className="font-semibold text-slate-800">Radius: </span>
          {state?.radius_miles || config?.radius_miles || '—'} miles
        </div>
        <div>
          <span className="font-semibold text-slate-800">Shows found: </span>
          {withShowsCount} / {artistList.length} artists
        </div>
      </div>

      {/* ── Artist Shows ── */}
      <section>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <SectionHeading count={artistList.length}>Artist Shows</SectionHeading>
          <div className="flex gap-1 text-xs">
            {[
              { id: 'all', label: 'All' },
              { id: 'with-shows', label: `With shows (${withShowsCount})` },
              { id: 'no-shows', label: 'None in range' },
            ].map(opt => (
              <button
                key={opt.id}
                onClick={() => setFilter(opt.id)}
                className={`px-2.5 py-1 rounded-full font-medium transition-colors ${
                  filter === opt.id
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-3">
          {filtered.map(a => (
            <ArtistCard key={a.name} {...a} />
          ))}
        </div>
      </section>

      {/* ── Local Venues ── */}
      <section>
        <SectionHeading count={localVenues.length}>Local Venues</SectionHeading>
        <div className="grid sm:grid-cols-2 gap-3">
          {localVenues.map(([name, info]) => (
            <VenueCard
              key={name}
              name={name}
              city={info.city}
              paused={info.paused}
              events={venueShows[name]}
            />
          ))}
        </div>
      </section>

      {/* ── Travel Venues ── */}
      <section>
        <SectionHeading count={travelVenues.length}>Travel Venues</SectionHeading>
        <div className="grid sm:grid-cols-2 gap-3">
          {travelVenues.map(([name, info]) => (
            <VenueCard
              key={name}
              name={name}
              city={info.city}
              paused={info.paused}
              events={venueShows[name]}
            />
          ))}
        </div>
      </section>
    </div>
  )
}

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
      <p className="text-slate-400 text-xs mt-2">Is the backend running?  <code className="bg-slate-100 px-1 rounded">uvicorn backend.main:app --port 8000</code></p>
    </div>
  )
}
