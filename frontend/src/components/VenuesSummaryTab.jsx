import { useState, useEffect } from 'react'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

// ── Venue card ────────────────────────────────────────────────────────────────
function VenueCard({ name, url, city, events, paused }) {
  const [open, setOpen] = useState(false)
  const tracked = events ? events.filter(e => e.tracked) : []

  return (
    <div className={`card transition-all ${paused ? 'opacity-50' : ''}`}>
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
                {name}
              </a>
            ) : (
              <span className="font-semibold text-slate-900 truncate">{name}</span>
            )}
          </div>
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
            {events ? `${events.length} events` : '\u2014'}
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
                {ev.tracked ? (
                  <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" title="Tracked artist" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-slate-200 flex-shrink-0" />
                )}
                <span className="font-medium text-slate-800">{ev.date}</span>
                <span className="text-slate-400">&middot;</span>
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
export default function VenuesSummaryTab() {
  const [state, setState]   = useState(null)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    if (DEMO) {
      fetch(import.meta.env.BASE_URL + 'static-data.json')
        .then(r => r.json())
        .then(data => { setState(data.state); setConfig(data.config) })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    } else {
      Promise.all([
        fetch('/api/state').then(r => r.json()),
        fetch('/api/config').then(r => r.json()),
      ])
        .then(([st, cfg]) => { setState(st); setConfig(cfg) })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    }
  }, [])

  if (loading) return <LoadingSpinner />
  if (error)   return <ErrorBox message={error} />

  const venueShows   = state?.venue_shows || {}
  const configVenues = config?.venues     || {}

  const localVenues  = Object.entries(configVenues).filter(([, v]) => v.is_local)
  const travelVenues = Object.entries(configVenues).filter(([, v]) => !v.is_local)

  return (
    <div className="space-y-8">
      {/* ── Local Venues ── */}
      <section>
        <SectionHeading count={localVenues.length}>Local Venues</SectionHeading>
        <div className="grid sm:grid-cols-2 gap-3">
          {localVenues.map(([name, info]) => (
            <VenueCard
              key={name}
              name={name}
              url={info.url}
              city={info.city}
              paused={info.paused}
              events={venueShows[name]}
            />
          ))}
          {localVenues.length === 0 && (
            <div className="col-span-2 card p-6 text-center text-slate-400 text-sm italic">
              No local venues configured.
            </div>
          )}
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
              url={info.url}
              city={info.city}
              paused={info.paused}
              events={venueShows[name]}
            />
          ))}
          {travelVenues.length === 0 && (
            <div className="col-span-2 card p-6 text-center text-slate-400 text-sm italic">
              No travel venues configured.
            </div>
          )}
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
      <p className="text-slate-400 text-xs mt-2">Is the backend running? <code className="bg-slate-100 px-1 rounded">uvicorn backend.main:app --port 8000</code></p>
    </div>
  )
}
