import { useState, useEffect, useMemo, useCallback } from 'react'
import ConcertMap from './ConcertMap.jsx'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

function fmtOnsale(isoStr) {
  if (!isoStr) return null
  try {
    return new Date(isoStr).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    })
  } catch { return null }
}

const GENRE_COLORS = {
  'Country / Americana':  'bg-amber-100 text-amber-800',
  'Indie / Alt-Rock':     'bg-blue-100  text-blue-800',
  'Electronic / Art-Rock':'bg-purple-100 text-purple-800',
  'Other':                'bg-slate-100 text-slate-700',
}

function genreColor(genre) {
  return GENRE_COLORS[genre] || GENRE_COLORS['Other']
}

function isInBounds(lat, lon, bounds) {
  if (!bounds) return true
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  return lat >= sw.lat && lat <= ne.lat && lon >= sw.lng && lon <= ne.lng
}

// ── Artist card ───────────────────────────────────────────────────────────────
function ArtistCard({ name, url, genre, shows, paused, isSelected, onSelect }) {
  const [manualOpen, setManualOpen] = useState(false)
  const open = isSelected || manualOpen

  function handleClick() {
    if (isSelected) {
      onSelect(null)
      setManualOpen(false)
    } else {
      onSelect({ type: 'artist', name })
    }
  }

  const onSale   = shows.filter(s => !s.not_yet_on_sale)
  const preSale  = shows.filter(s => s.not_yet_on_sale)

  const mergedRows = useMemo(() => {
    const rows = [
      ...onSale.map(s => ({ ...s, _src: 'on-sale' })),
      ...preSale.map(s => ({ ...s, _src: 'presale' })),
    ]
    rows.sort((a, b) => {
      const da = new Date(a.date), db = new Date(b.date)
      return (!isNaN(da) && !isNaN(db)) ? da - db : 0
    })
    return rows
  }, [shows])

  return (
    <div className={`card transition-all ${paused ? 'opacity-50' : ''} ${isSelected ? 'ring-2 ring-indigo-400' : ''}`}>
      <button
        onClick={handleClick}
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
            <span className={`badge-genre ${genreColor(genre)}`}>{genre}</span>
            {paused && <span className="badge-paused">Paused</span>}
            {isSelected && (
              <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
                Filtered
              </span>
            )}
          </div>
        </div>

        {/* Count badges */}
        <div className="flex flex-col items-end gap-0.5 flex-shrink-0">
          {onSale.length > 0 && (
            <span className="text-sm font-semibold text-emerald-600">
              {onSale.length} on sale
            </span>
          )}
          {preSale.length > 0 && (
            <span className="text-xs font-semibold text-amber-600">
              {preSale.length} coming soon
            </span>
          )}
          {shows.length === 0 && (
            <span className="text-sm font-semibold text-slate-400">No shows</span>
          )}
          <svg
            className={`w-4 h-4 text-slate-400 transition-transform mt-0.5 ${open ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-50 px-4 pb-4">
          {mergedRows.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {mergedRows.map((show, i) =>
                show._src === 'presale' ? (
                  // ── Not-yet-on-sale show ──
                  <li key={i} className="bg-amber-50 -mx-2 px-2 py-1.5 rounded-lg text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <div>
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
                    <div className="flex items-center gap-1 mt-0.5">
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                      <span className="text-xs text-amber-700 font-medium">
                        {show.onsale_tbd
                          ? 'On-sale date TBD'
                          : show.onsale_datetime
                          ? `On sale ${fmtOnsale(show.onsale_datetime)}`
                          : 'On-sale date not announced'}
                      </span>
                    </div>
                    {show.presales && show.presales.length > 0 && (
                      <ul className="mt-1 space-y-0.5">
                        {show.presales.map((p, pi) => (
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
                ) : (
                  // ── On-sale show ──
                  <li key={i} className="flex items-start justify-between gap-2 text-sm">
                    <div>
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
                  </li>
                )
              )}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-400 italic">No upcoming shows found.</p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Section heading ───────────────────────────────────────────────────────────
function SectionHeading({ children, count, total }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <h2 className="text-base font-bold text-slate-700">{children}</h2>
      {count !== undefined && total !== undefined ? (
        <span className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full">
          {count} / {total} in view
        </span>
      ) : count !== undefined ? (
        <span className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full">{count}</span>
      ) : null}
    </div>
  )
}

// ── Map legend ────────────────────────────────────────────────────────────────
function MapLegend({ mapFilter, onClearFilter }) {
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-2 px-1">
      <span className="flex items-center gap-1">
        <span className="w-3 h-3 rounded-full bg-blue-500 inline-block" /> On Sale
      </span>
      <span className="flex items-center gap-1">
        <span className="w-3 h-3 rounded-full bg-orange-500 inline-block" /> Coming Soon
      </span>
      <span className="flex items-center gap-1">
        <span className="w-3 h-3 rounded-full bg-purple-500 inline-block" /> Venue
      </span>
      <span className="flex items-center gap-1">
        <span className="w-3 h-3 rounded-full bg-indigo-500 inline-block" /> Home
      </span>
      {mapFilter && (
        <button
          onClick={onClearFilter}
          className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium hover:bg-indigo-200 transition-colors"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Clear filter: {mapFilter.name}
        </button>
      )}
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function ArtistsSummaryTab() {
  const [shows, setShows]             = useState(null)
  const [config, setConfig]           = useState(null)
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [mapFilter, setMapFilter]     = useState(null)
  const [mapBounds, setMapBounds]     = useState(null)
  const [hideNoShows, setHideNoShows] = useState(false)

  useEffect(() => {
    if (DEMO) {
      fetch(import.meta.env.BASE_URL + 'static-data.json')
        .then(r => r.json())
        .then(data => {
          setShows({
            api_configured: true,
            artist_shows: data.state?.artist_shows || {},
            last_refreshed: data.coming_soon_fetched || null,
          })
          setConfig(data.config)
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    } else {
      Promise.all([
        fetch('/api/shows').then(r => r.json()),
        fetch('/api/config').then(r => r.json()),
      ])
        .then(([s, cfg]) => { setShows(s); setConfig(cfg) })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    }
  }, [])

  const handleBoundsChange = useCallback((bounds) => { setMapBounds(bounds) }, [])

  const artistShows = shows?.artist_shows ?? {}

  // Map pin data
  const allArtistShows = useMemo(() => {
    const arr = []
    for (const [artist, artistShowList] of Object.entries(artistShows)) {
      for (const show of artistShowList) {
        arr.push({
          ...show,
          artist,
          status: 'on_sale',
          source: show.not_yet_on_sale ? 'tm' : undefined,
        })
      }
    }
    return arr
  }, [artistShows])

  const allVenueShows = useMemo(() => {
    if (!config?.venues) return []
    return Object.entries(config.venues)
      .map(([venueName, venueConfig]) => {
        if (!venueConfig) return null
        return { venueName, lat: venueConfig.lat || null, lon: venueConfig.lon || null, city: venueConfig.city, events: [] }
      })
      .filter(Boolean)
  }, [config])

  const centerLat = config?.center_lat ?? null
  const centerLon = config?.center_lon ?? null

  if (loading) return <LoadingSpinner />
  if (error)   return <ErrorBox message={error} />

  const configArtists = config?.artists || {}

  const artistList = Object.entries(configArtists).map(([name, info]) => {
    const showList = artistShows[name] || []
    return { name, url: info.url || null, genre: info.genre || 'Other', paused: info.paused || false, shows: showList, totalCount: showList.length }
  }).sort((a, b) => {
    if (b.totalCount !== a.totalCount) return b.totalCount - a.totalCount
    return a.name.localeCompare(b.name)
  })

  const visibleArtists = artistList.filter(a => {
    if (hideNoShows && a.totalCount === 0) return false
    if (mapFilter?.type === 'artist' && mapFilter.name === a.name) return true
    if (!mapBounds) return true
    return a.shows.some(s => s.lat != null && s.lon != null && isInBounds(s.lat, s.lon, mapBounds))
  })

  const withShowsCount = artistList.filter(a => a.totalCount > 0).length
  const totalShows     = Object.values(artistShows).reduce((n, arr) => n + arr.length, 0)

  return (
    <div className="space-y-8">
      {/* Meta */}
      <div className="card p-4 flex flex-wrap gap-4 text-sm text-slate-600">
        <div>
          <span className="font-semibold text-slate-800">Home: </span>
          {config?.center_city || '\u2014'}
        </div>
        <div>
          <span className="font-semibold text-slate-800">Artists: </span>
          {withShowsCount} / {artistList.length} with shows
        </div>
        <div>
          <span className="font-semibold text-slate-800">Total shows: </span>
          {totalShows}
        </div>
        {shows?.stale && (
          <div><span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">Data may be stale — click Refresh Data</span></div>
        )}
      </div>

      {/* ── Map ── */}
      <section>
        <SectionHeading>Concert Map</SectionHeading>
        <ConcertMap
          centerLat={centerLat}
          centerLon={centerLon}
          artistShows={allArtistShows}
          venueShows={allVenueShows}
          mapFilter={mapFilter}
          onBoundsChange={handleBoundsChange}
        />
        <MapLegend mapFilter={mapFilter} onClearFilter={() => setMapFilter(null)} />
      </section>

      {/* ── Artist Shows ── */}
      <section>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <SectionHeading count={visibleArtists.length} total={artistList.length}>
            Artist Shows
          </SectionHeading>
          <div className="flex items-center gap-3">
            {mapBounds && visibleArtists.length < artistList.length && (
              <span className="text-xs text-slate-400 italic">Zoom out or pan to see more artists</span>
            )}
            <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer">
              <input
                type="checkbox"
                checked={hideNoShows}
                onChange={e => setHideNoShows(e.target.checked)}
                className="rounded border-slate-300"
              />
              Hide artists not on tour
            </label>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-3">
          {visibleArtists.map(a => (
            <ArtistCard
              key={a.name}
              {...a}
              isSelected={mapFilter?.type === 'artist' && mapFilter.name === a.name}
              onSelect={setMapFilter}
            />
          ))}
          {visibleArtists.length === 0 && (
            <div className="col-span-2 card p-6 text-center text-slate-400 text-sm italic">
              No artists with shows in the current map view. Zoom out to see more.
            </div>
          )}
        </div>
      </section>

      {/* ── Flagged Items (local mode only) ── */}
      {!DEMO && <FlaggedItems />}
    </div>
  )
}

// ── Flagged Items ─────────────────────────────────────────────────────────────
function FlaggedItems() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/flagged-items')
      .then(r => r.json())
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function dismiss(index) {
    try {
      await fetch(`/api/flagged-items/${index}`, { method: 'DELETE' })
      setItems(prev => prev.filter((_, i) => i !== index))
    } catch {}
  }

  if (loading || items.length === 0) return null

  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-base font-bold text-slate-700">Flagged Items</h2>
        <span className="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full">{items.length}</span>
      </div>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="card p-3 flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800">{item.title || item.artist || 'Unknown'}</p>
              <p className="text-xs text-slate-500 mt-0.5">{item.message || item.reason || ''}</p>
              {item.source && (
                <span className="text-xs text-slate-400">{item.source}</span>
              )}
            </div>
            <button
              onClick={() => dismiss(i)}
              className="text-slate-400 hover:text-red-500 transition-colors flex-shrink-0"
              title="Dismiss"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </section>
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
