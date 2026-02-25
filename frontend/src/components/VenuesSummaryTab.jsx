import { useState, useEffect } from 'react'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

function fmtOnsale(isoStr) {
  if (!isoStr) return null
  try {
    return new Date(isoStr).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    })
  } catch { return null }
}

// ── Venue card ────────────────────────────────────────────────────────────────
function VenueCard({ name, url, city, shows, paused }) {
  const [open, setOpen] = useState(false)
  const hasShows = shows && shows.length > 0

  const countLabel = hasShows
    ? `${shows.length} event${shows.length !== 1 ? 's' : ''}`
    : '\u2014'

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
                className="font-semibold text-neutral-900 hover:text-neutral-600 hover:underline truncate"
              >
                {name}
              </a>
            ) : (
              <span className="font-semibold text-neutral-900 truncate">{name}</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            <span className="text-xs text-neutral-400">{city}</span>
            {paused && <span className="badge-paused">Paused</span>}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-sm text-neutral-500">{countLabel}</span>
          <span className="text-neutral-400 text-xs">{open ? '−' : '+'}</span>
        </div>
      </button>

      {open && hasShows && (
        <div className="border-t border-neutral-100 px-4 pb-4">
          <ul className="mt-3 space-y-1.5">
            {shows.map((ev, i) => (
              <li key={i} className={`flex items-center justify-between gap-2 text-sm ${ev.not_yet_on_sale ? 'bg-neutral-50 -mx-2 px-2 py-1' : ''}`}>
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${ev.not_yet_on_sale ? 'bg-neutral-400' : 'bg-neutral-200'}`} />
                  <span className="font-medium text-neutral-800">{ev.date}</span>
                  <span className="text-neutral-300">&middot;</span>
                  <span className="text-neutral-600 truncate">{ev.artist}</span>
                </div>
                {ev.ticketmaster_url && (
                  <a
                    href={ev.ticketmaster_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 text-xs text-neutral-500 hover:text-neutral-800 hover:underline"
                  >
                    TM →
                  </a>
                )}
              </li>
            ))}
          </ul>
          {shows.some(s => s.not_yet_on_sale) && (
            <p className="mt-2 text-xs text-neutral-400">
              Filled dot = not yet on public sale
            </p>
          )}
        </div>
      )}

      {open && !hasShows && (
        <div className="border-t border-neutral-100 px-4 pb-4">
          <p className="mt-3 text-sm text-neutral-400 italic">No events data yet.</p>
        </div>
      )}
    </div>
  )
}

// ── Section heading ───────────────────────────────────────────────────────────
function SectionHeading({ children, count }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <h2 className="text-base font-bold text-neutral-800">{children}</h2>
      {count !== undefined && (
        <span className="text-xs text-neutral-400">{count}</span>
      )}
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function VenuesSummaryTab() {
  const [showsData, setShowsData] = useState(null)
  const [config, setConfig]       = useState(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)

  useEffect(() => {
    if (DEMO) {
      fetch(import.meta.env.BASE_URL + 'static-data.json')
        .then(r => r.json())
        .then(data => {
          setShowsData({ venue_shows: data.state?.venue_shows || {} })
          setConfig(data.config)
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    } else {
      Promise.all([
        fetch('/api/shows').then(r => r.json()),
        fetch('/api/config').then(r => r.json()),
      ])
        .then(([s, cfg]) => { setShowsData(s); setConfig(cfg) })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    }
  }, [])

  if (loading) return <LoadingSpinner />
  if (error)   return <ErrorBox message={error} />

  const venueShows   = showsData?.venue_shows || {}
  const configVenues = config?.venues || {}

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
              shows={venueShows[name] || []}
            />
          ))}
          {localVenues.length === 0 && (
            <div className="col-span-2 card p-6 text-center text-neutral-400 text-sm italic">
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
              shows={venueShows[name] || []}
            />
          ))}
          {travelVenues.length === 0 && (
            <div className="col-span-2 card p-6 text-center text-neutral-400 text-sm italic">
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
      <div className="w-8 h-8 border-2 border-neutral-200 border-t-neutral-700 rounded-full animate-spin" />
    </div>
  )
}

function ErrorBox({ message }) {
  return (
    <div className="card p-6 text-center">
      <p className="text-neutral-800 font-medium">Failed to load data</p>
      <p className="text-neutral-500 text-sm mt-1">{message}</p>
      <p className="text-neutral-400 text-xs mt-2">Is the backend running? <code className="bg-neutral-100 px-1">uvicorn backend.main:app --port 8000</code></p>
    </div>
  )
}
