import { useState, useEffect, useMemo, useCallback } from 'react'
import ConcertMap from './ConcertMap.jsx'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

function formatDatetime(isoStr) {
  if (!isoStr) return null
  try {
    return new Date(isoStr).toLocaleString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
    })
  } catch { return isoStr }
}

function PresaleList({ presales }) {
  if (!presales || presales.length === 0) return null
  return (
    <ul className="mt-1.5 space-y-1">
      {presales.map((p, i) => (
        <li key={i} className="flex items-start gap-1.5 text-xs text-neutral-400">
          <span className="inline-block mt-0.5 w-1.5 h-1.5 rounded-full bg-neutral-300 flex-shrink-0" />
          <span>
            <span className="font-medium text-neutral-500">{p.name}</span>
            {p.start_datetime && (
              <span className="ml-1">— starts {formatDatetime(p.start_datetime)}</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  )
}

// ── Festival show row ─────────────────────────────────────────────────────────
function FestivalShowRow({ show, festivalName }) {
  const dateObj = new Date(show.date)
  const month = !isNaN(dateObj) ? dateObj.toLocaleString(undefined, { month: 'short' }).toUpperCase() : '???'
  const day = !isNaN(dateObj) ? dateObj.getDate() : '--'

  return (
    <div className="flex items-center gap-3 px-3 py-2.5 border-b border-neutral-100 last:border-b-0 hover:bg-neutral-50/50 transition-colors">
      {/* Date block */}
      <div className="flex-shrink-0 w-11 text-center">
        <div className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider leading-none">{month}</div>
        <div className="text-xl font-bold text-neutral-800 leading-tight">{day}</div>
      </div>

      {/* Divider */}
      <div className="w-px h-9 bg-neutral-200 flex-shrink-0" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        {show.event_name && show.event_name !== festivalName && (
          <div className="text-sm font-medium text-neutral-700 truncate">{show.event_name}</div>
        )}
        <div className="text-xs text-neutral-500 truncate">
          {show.venue}
          <span className="text-neutral-300 mx-1">&middot;</span>
          {show.city}
        </div>
      </div>

      {/* Status badge */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {show.is_new && (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200">
            New
          </span>
        )}
      </div>
    </div>
  )
}

// ── Coming soon event row (inside festival card) ──────────────────────────────
function ComingSoonEventRow({ event }) {
  const onsaleLabel = event.onsale_tbd
    ? 'On-sale date TBD'
    : event.onsale_datetime
    ? `On sale ${formatDatetime(event.onsale_datetime)}`
    : 'On-sale date not announced'

  return (
    <li className="text-sm border-t border-neutral-100 pt-2 mt-2 first:border-0 first:pt-0 first:mt-0">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-medium text-neutral-800">{event.date}</span>
          <span className="text-neutral-300 mx-1">&middot;</span>
          <span className="text-neutral-600">{event.venue}</span>
          <span className="text-neutral-300 mx-1">&middot;</span>
          <span className="text-neutral-400">{event.city}</span>
        </div>
        {event.ticketmaster_url && (
          <a
            href={event.ticketmaster_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 text-xs text-neutral-500 hover:text-neutral-800 hover:underline"
          >
            TM &rarr;
          </a>
        )}
      </div>
      {event.event_name && event.event_name !== event.tracked_festival && (
        <p className="text-xs text-neutral-400 mt-0.5 italic">{event.event_name}</p>
      )}
      <div className="mt-1 flex items-center gap-1.5">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-orange-400 flex-shrink-0" />
        <span className="text-xs text-neutral-500 font-medium">{onsaleLabel}</span>
      </div>
      <PresaleList presales={event.presales} />
    </li>
  )
}

// ── Festival card ─────────────────────────────────────────────────────────────
function FestivalCard({ festivalName, festivalUrl, shows, comingSoonEvents, isSelected, onSelect }) {
  const onSaleCount = shows.length
  const comingSoonCount = comingSoonEvents.length

  function handleClick(e) {
    if (!onSelect) return
    if (e.target.closest('a')) return
    onSelect(festivalName)
  }

  return (
    <div className="card overflow-hidden">
      <div
        onClick={handleClick}
        className={`p-4 flex items-center gap-3 transition-colors
          ${onSelect ? 'cursor-pointer' : ''}
          ${isSelected
            ? 'bg-neutral-200 border-l-2 border-l-neutral-700'
            : 'hover:bg-neutral-50'
          }`}
      >
        <div className="flex-1 min-w-0">
          {festivalUrl ? (
            <a href={festivalUrl} target="_blank" rel="noopener noreferrer"
              className="font-semibold text-neutral-900 hover:text-neutral-600 hover:underline truncate block">
              {festivalName}
            </a>
          ) : (
            <span className="font-semibold text-neutral-900 truncate block">{festivalName}</span>
          )}
          <div className="flex items-center gap-2 mt-1 text-xs text-neutral-400">
            {onSaleCount > 0 && <span>{onSaleCount} event{onSaleCount !== 1 ? 's' : ''}</span>}
            {comingSoonCount > 0 && (
              <span className="text-orange-500">{comingSoonCount} coming soon</span>
            )}
          </div>
        </div>
      </div>

      {/* On-sale events */}
      {onSaleCount > 0 && (
        <div className="border-t border-neutral-100">
          {shows.map((show, i) => (
            <FestivalShowRow key={i} show={show} festivalName={festivalName} />
          ))}
        </div>
      )}

      {/* Coming-soon events */}
      {comingSoonCount > 0 && (
        <div className="border-t border-neutral-200 px-4 pb-4">
          <h4 className="text-[10px] font-semibold text-orange-500 uppercase tracking-wider mt-3 mb-2">On Sale Soon</h4>
          <ul>
            {comingSoonEvents.map((ev, i) => <ComingSoonEventRow key={i} event={ev} />)}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Map legend ───────────────────────────────────────────────────────────────
function MapLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-400 mt-2 px-1">
      <span className="flex items-center gap-1">
        <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block" /> Festival
      </span>
    </div>
  )
}

// ── Not found section ─────────────────────────────────────────────────────────
function NotFoundSection({ items, configFestivals }) {
  const [open, setOpen] = useState(false)
  if (!items || items.length === 0) return null

  return (
    <div className="card">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full p-4 text-left flex items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm text-neutral-500">Not found on Ticketmaster</span>
          <span className="text-xs text-neutral-400">{items.length}</span>
        </div>
        <span className="text-neutral-400 text-xs flex-shrink-0">{open ? '\u2212' : '+'}</span>
      </button>
      {open && (
        <div className="border-t border-neutral-100 px-4 pb-4">
          <p className="text-xs text-neutral-400 mt-3 mb-3">
            These tracked festivals returned no matching results on Ticketmaster.
            The festival may not yet be listed, or tickets may already be on sale under a different name.
          </p>
          <ul className="space-y-1.5">
            {items.map(name => (
              <li key={name} className="flex items-center gap-2 text-sm text-neutral-600">
                <span className="w-1.5 h-1.5 rounded-full bg-neutral-200 flex-shrink-0" />
                {configFestivals[name]?.url ? (
                  <a href={configFestivals[name].url} target="_blank" rel="noopener noreferrer"
                    className="hover:text-neutral-900 hover:underline">
                    {name}
                  </a>
                ) : name}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function FestivalsTab() {
  const [data, setData] = useState(null)
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedFestival, setSelectedFestival] = useState(null)

  useEffect(() => {
    if (DEMO) {
      fetch(import.meta.env.BASE_URL + 'static-data.json')
        .then(r => r.json())
        .then(d => {
          setData({
            festival_shows: d.state?.festival_shows || {},
            festivals_not_found: d.state?.festivals_not_found || [],
            festival_coming_soon: d.festival_coming_soon || [],
          })
          setConfig({
            ...d.config,
            center_lat: d.config?.center_lat ?? d.state?.center_lat,
            center_lon: d.config?.center_lon ?? d.state?.center_lon,
          })
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    } else {
      Promise.all([
        fetch('/api/shows').then(r => r.json()),
        fetch('/api/config').then(r => r.json()),
      ])
        .then(([s, cfg]) => {
          setData({
            festival_shows: s.festival_shows || {},
            festivals_not_found: s.festivals_not_found || [],
            festival_coming_soon: s.festival_coming_soon || [],
          })
          setConfig(cfg)
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    }
  }, [])

  const festivalShows = data?.festival_shows ?? {}
  const festivalsNotFound = data?.festivals_not_found ?? []
  const festivalComingSoon = data?.festival_coming_soon ?? []
  const configFestivals = config?.festivals || {}

  // Group coming-soon by tracked_festival
  const comingSoonByFestival = useMemo(() => {
    const map = {}
    for (const ev of festivalComingSoon) {
      const name = ev.tracked_festival
      if (!map[name]) map[name] = []
      map[name].push(ev)
    }
    return map
  }, [festivalComingSoon])

  // Merge festivals: those with shows + those with only coming-soon + config-only
  const allFestivals = useMemo(() => {
    const names = new Set([
      ...Object.keys(festivalShows),
      ...Object.keys(comingSoonByFestival),
    ])
    return [...names].sort().map(name => ({
      name,
      shows: festivalShows[name] || [],
      comingSoon: comingSoonByFestival[name] || [],
      url: configFestivals[name]?.url || null,
    }))
  }, [festivalShows, comingSoonByFestival, configFestivals])

  // Build map pin data for festival shows
  const mapFestivalShows = useMemo(() => {
    const pins = []
    for (const festival of allFestivals) {
      if (selectedFestival && festival.name !== selectedFestival) continue
      for (const show of festival.shows) {
        if (show.lat != null && show.lon != null) {
          pins.push({
            lat: show.lat,
            lon: show.lon,
            festivalName: festival.name,
            event_name: show.event_name,
            date: show.date,
            venue: show.venue,
            city: show.city,
            is_new: show.is_new,
          })
        }
      }
    }
    return pins
  }, [allFestivals, selectedFestival])

  const handleFestivalClick = useCallback((name) => {
    setSelectedFestival(prev => prev === name ? null : name)
  }, [])

  const centerLat = config?.center_lat ?? null
  const centerLon = config?.center_lon ?? null

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorBox message={error} />

  const totalEvents = allFestivals.reduce((sum, f) => sum + f.shows.length, 0)
  const totalComingSoon = allFestivals.reduce((sum, f) => sum + f.comingSoon.length, 0)

  return (
    <div className="space-y-4">
      {/* Map */}
      <section>
        <ConcertMap
          centerLat={centerLat}
          centerLon={centerLon}
          artistShows={[]}
          venueShows={[]}
          festivalShows={mapFestivalShows}
          mapFilter={null}
          onBoundsChange={() => {}}
        />
        <MapLegend />
      </section>

      {/* Stats bar */}
      {(allFestivals.length > 0 || festivalsNotFound.length > 0) && (
        <div className="card p-4 flex flex-wrap gap-4 text-sm text-neutral-600">
          <div>
            <span className="font-semibold text-neutral-800">Festivals: </span>
            {allFestivals.length}
          </div>
          {totalEvents > 0 && (
            <div>
              <span className="font-semibold text-neutral-800">Events: </span>
              {totalEvents}
            </div>
          )}
          {totalComingSoon > 0 && (
            <div>
              <span className="font-semibold text-neutral-800">Coming Soon: </span>
              {totalComingSoon}
            </div>
          )}
        </div>
      )}

      {/* Festival cards */}
      {allFestivals.length > 0 ? (
        <div className="space-y-3">
          {allFestivals.map(festival => (
            <FestivalCard
              key={festival.name}
              festivalName={festival.name}
              festivalUrl={festival.url}
              shows={festival.shows}
              comingSoonEvents={festival.comingSoon}
              isSelected={selectedFestival === festival.name}
              onSelect={handleFestivalClick}
            />
          ))}
        </div>
      ) : festivalsNotFound.length === 0 ? (
        <div className="card p-8 text-center text-neutral-400 text-sm italic">
          No festivals tracked yet. Add festivals in the Configure tab.
        </div>
      ) : null}

      {/* Not found */}
      <NotFoundSection items={festivalsNotFound} configFestivals={configFestivals} />
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
    </div>
  )
}
