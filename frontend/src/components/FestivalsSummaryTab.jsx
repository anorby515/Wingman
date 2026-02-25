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

// ── Festival card ─────────────────────────────────────────────────────────────
function FestivalCard({ name, url, paused, lineup, tmShows, tmConfigured }) {
  const [open, setOpen] = useState(false)

  const hasLineup    = lineup && lineup.length > 0
  const trackedCount = hasLineup ? lineup.filter(e => e.tracked).length : 0
  const hasTm        = tmConfigured && tmShows && tmShows.length > 0

  return (
    <div className={`card transition-all ${paused ? 'opacity-50' : ''}`}>
      <div className="p-4 flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 min-w-0">
            {url ? (
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-slate-900 hover:text-indigo-600 hover:underline truncate"
              >
                {name}
              </a>
            ) : (
              <span className="font-semibold text-slate-900 truncate">{name}</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            {paused && <span className="badge-paused">Paused</span>}
            {hasTm && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                {tmShows.length} on Ticketmaster
              </span>
            )}
            {trackedCount > 0 && (
              <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">
                {trackedCount} tracked artists
              </span>
            )}
            {!hasTm && !hasLineup && !paused && (
              <span className="text-xs text-slate-400 italic">Lineup not yet scraped</span>
            )}
            {!hasTm && hasLineup && (
              <span className="text-xs text-slate-500">{lineup.length} artists in lineup</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={e => e.stopPropagation()}
              className="flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700"
              title="View lineup page"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          )}
          {(hasTm || hasLineup) && (
            <button onClick={() => setOpen(o => !o)}>
              <svg
                className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* ── TM shows (primary) ── */}
      {open && hasTm && (
        <div className="border-t border-slate-50 px-4 pb-4">
          <ul className="mt-3 space-y-2">
            {tmShows.map((ev, i) => (
              <li key={i} className={`text-sm ${ev.not_yet_on_sale ? 'bg-amber-50 -mx-2 px-2 py-1.5 rounded-lg' : ''}`}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="font-medium text-slate-800">{ev.date}</span>
                    <span className="text-slate-400 mx-1">&middot;</span>
                    <span className="text-slate-600">{ev.venue}</span>
                    <span className="text-slate-400 mx-1">&middot;</span>
                    <span className="text-slate-500">{ev.city}</span>
                  </div>
                  {ev.ticketmaster_url && (
                    <a
                      href={ev.ticketmaster_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-shrink-0 text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
                    >
                      TM &rarr;
                    </a>
                  )}
                </div>
                {ev.event_name && ev.event_name !== name && (
                  <p className="text-xs text-slate-400 mt-0.5 italic">{ev.event_name}</p>
                )}
                {ev.not_yet_on_sale && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                    <span className="text-xs text-amber-700 font-medium">
                      {ev.onsale_tbd
                        ? 'On-sale date TBD'
                        : ev.onsale_datetime
                        ? `On sale ${fmtOnsale(ev.onsale_datetime)}`
                        : 'On-sale date not announced'}
                    </span>
                  </div>
                )}
                {ev.presales && ev.presales.length > 0 && (
                  <ul className="mt-1 space-y-0.5">
                    {ev.presales.map((p, pi) => (
                      <li key={pi} className="flex items-center gap-1 text-xs text-slate-500">
                        <span className="w-1.5 h-1.5 rounded-full bg-violet-400 flex-shrink-0" />
                        <span className="font-medium text-slate-600">{p.name}</span>
                        {p.start_datetime && (
                          <span className="text-slate-400">— starts {fmtOnsale(p.start_datetime)}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
          {/* Scraped lineup section (supplementary) */}
          {hasLineup && (
            <div className="mt-4 pt-3 border-t border-slate-100">
              <p className="text-xs font-medium text-slate-500 mb-2">Scraped lineup:</p>
              <ul className="space-y-1">
                {lineup.map((entry, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    {entry.tracked ? (
                      <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" title="Tracked artist" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-slate-200 flex-shrink-0" />
                    )}
                    <span className={entry.tracked ? 'text-slate-800 font-medium' : 'text-slate-500'}>
                      {entry.artist}
                    </span>
                  </li>
                ))}
              </ul>
              {trackedCount > 0 && (
                <p className="mt-2 text-xs text-emerald-600">Green dot = tracked artist</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Scraped lineup only (fallback when TM not configured) ── */}
      {open && !hasTm && hasLineup && (
        <div className="border-t border-slate-50 px-4 pb-4">
          <ul className="mt-3 space-y-1.5">
            {lineup.map((entry, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                {entry.tracked ? (
                  <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" title="Tracked artist" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-slate-200 flex-shrink-0" />
                )}
                <span className={entry.tracked ? 'text-slate-800 font-medium' : 'text-slate-500'}>
                  {entry.artist}
                </span>
              </li>
            ))}
          </ul>
          {trackedCount > 0 && (
            <p className="mt-2 text-xs text-emerald-600">Green dot = tracked artist</p>
          )}
        </div>
      )}
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

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function FestivalsSummaryTab() {
  const [state, setState]     = useState(null)
  const [config, setConfig]   = useState(null)
  const [tmData, setTmData]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

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
        fetch('/api/tm-shows').then(r => r.json()).catch(() => null),
      ])
        .then(([st, cfg, tm]) => { setState(st); setConfig(cfg); setTmData(tm) })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    }
  }, [])

  if (loading) return <LoadingSpinner />
  if (error)   return <ErrorBox message={error} />

  const festivalShows   = state?.festival_shows  || {}
  const configFestivals = config?.festivals      || {}
  const tmConfigured    = tmData?.api_configured ?? false
  const tmFestivalShows = tmData?.festival_shows || {}
  const festivals       = Object.entries(configFestivals)

  return (
    <div className="space-y-3">
      {festivals.length === 0 ? (
        <div className="card p-8 text-center text-slate-400 text-sm italic">
          No festivals configured.
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          {festivals.map(([name, info]) => (
            <FestivalCard
              key={name}
              name={name}
              url={info.url}
              paused={info.paused}
              lineup={festivalShows[name]}
              tmShows={tmFestivalShows[name] ?? (tmConfigured ? [] : null)}
              tmConfigured={tmConfigured}
            />
          ))}
        </div>
      )}
    </div>
  )
}
