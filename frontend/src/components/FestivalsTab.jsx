import { useState, useEffect, useMemo, useCallback } from 'react'
import ConcertMap from './ConcertMap.jsx'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

function formatDayLabel(dateStr) {
  if (!dateStr) return null
  try {
    const d = new Date(dateStr + 'T12:00:00')
    return d.toLocaleDateString(undefined, {
      weekday: 'long', month: 'long', day: 'numeric',
    })
  } catch { return dateStr }
}

// ── Lineup day section ────────────────────────────────────────────────────────
function LineupDay({ day, trackedArtists }) {
  const label = day.date ? formatDayLabel(day.date) : day.label
  return (
    <div>
      <h5 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
        {label || day.label}
      </h5>
      <div className="flex flex-wrap gap-x-1.5 gap-y-1">
        {day.artists.map((artist, i) => {
          const isTracked = trackedArtists.has(artist.name)
          return (
            <span
              key={i}
              className={`inline-flex items-center text-sm px-2 py-0.5 rounded-full
                ${artist.headliner
                  ? isTracked
                    ? 'bg-green-100 text-green-800 font-semibold border border-green-300'
                    : 'bg-neutral-200 text-neutral-800 font-semibold'
                  : isTracked
                    ? 'bg-green-50 text-green-700 border border-green-200'
                    : 'bg-neutral-50 text-neutral-600'
                }`}
            >
              {isTracked && (
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5 flex-shrink-0" />
              )}
              {artist.name}
            </span>
          )
        })}
      </div>
    </div>
  )
}

// ── Festival card ─────────────────────────────────────────────────────────────
function FestivalCard({ festivalName, festivalUrl, shows, lineup, trackedArtists, isSelected, onSelect }) {
  const hasLineup = lineup && lineup.days && lineup.days.length > 0

  // Compute date range from shows or lineup
  const dateRange = useMemo(() => {
    const dates = []
    for (const s of shows) {
      if (s.raw_date) dates.push(s.raw_date)
    }
    if (hasLineup) {
      for (const d of lineup.days) {
        if (d.date) dates.push(d.date)
      }
    }
    if (dates.length === 0) return null
    dates.sort()
    const fmt = (d) => {
      try {
        return new Date(d + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      } catch { return d }
    }
    if (dates.length === 1) return fmt(dates[0])
    return `${fmt(dates[0])} – ${fmt(dates[dates.length - 1])}`
  }, [shows, lineup, hasLineup])

  // Venue/city from first show
  const location = shows[0]
    ? `${shows[0].venue}, ${shows[0].city}`
    : null

  function handleClick(e) {
    if (!onSelect) return
    if (e.target.closest('a')) return
    onSelect(festivalName)
  }

  return (
    <div className="card overflow-hidden">
      {/* Poster image banner */}
      {lineup?.image_url && (
        <a href={festivalUrl || lineup.lineup_url} target="_blank" rel="noopener noreferrer">
          <img
            src={lineup.image_url}
            alt={`${festivalName} lineup`}
            className="w-full h-48 object-cover object-top"
          />
        </a>
      )}

      {/* Header */}
      <div
        onClick={handleClick}
        className={`p-4 transition-colors
          ${onSelect ? 'cursor-pointer' : ''}
          ${isSelected
            ? 'bg-neutral-200 border-l-2 border-l-neutral-700'
            : 'hover:bg-neutral-50'
          }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {festivalUrl ? (
              <a href={festivalUrl} target="_blank" rel="noopener noreferrer"
                className="font-bold text-lg text-neutral-900 hover:text-neutral-600 hover:underline block">
                {festivalName}
              </a>
            ) : (
              <span className="font-bold text-lg text-neutral-900 block">{festivalName}</span>
            )}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-sm text-neutral-500">
              {dateRange && <span>{dateRange}</span>}
              {location && (
                <>
                  <span className="text-neutral-300">&middot;</span>
                  <span>{location}</span>
                </>
              )}
            </div>
            {hasLineup && (
              <div className="mt-1.5 text-xs text-neutral-400">
                {lineup.days.reduce((s, d) => s + d.artists.length, 0)} artists
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Lineup by day — horizontal columns */}
      {hasLineup && (
        <div className="border-t border-neutral-100 px-4 py-4">
          <h4 className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-3">Lineup</h4>
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${lineup.days.length}, minmax(0, 1fr))` }}>
            {lineup.days.map((day, i) => (
              <LineupDay key={i} day={day} trackedArtists={trackedArtists} />
            ))}
          </div>
          {lineup.last_updated && (
            <p className="text-[10px] text-neutral-300 mt-3">
              Lineup updated {lineup.last_updated}
            </p>
          )}
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

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function FestivalsTab() {
  const [data, setData] = useState(null)
  const [config, setConfig] = useState(null)
  const [lineups, setLineups] = useState({})
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
          })
          setConfig({
            ...d.config,
            center_lat: d.config?.center_lat ?? d.state?.center_lat,
            center_lon: d.config?.center_lon ?? d.state?.center_lon,
          })
          setLineups(d.festival_lineups || {})
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    } else {
      Promise.all([
        fetch('/api/shows').then(r => r.json()),
        fetch('/api/config').then(r => r.json()),
        fetch('/api/festival-lineups').then(r => r.json()),
      ])
        .then(([s, cfg, lu]) => {
          setData({
            festival_shows: s.festival_shows || {},
          })
          setConfig(cfg)
          setLineups(lu || {})
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    }
  }, [])

  const festivalShows = data?.festival_shows ?? {}
  const configFestivals = config?.festivals || {}
  const configArtists = config?.artists || {}

  // Build set of tracked artist names for highlighting
  const trackedArtists = useMemo(() => {
    return new Set(Object.keys(configArtists))
  }, [configArtists])

  // Merge festivals: those with shows + those with only lineups
  const allFestivals = useMemo(() => {
    const names = new Set([
      ...Object.keys(festivalShows),
      ...Object.keys(lineups),
    ])
    return [...names].sort().map(name => ({
      name,
      shows: festivalShows[name] || [],
      lineup: lineups[name] || null,
      url: configFestivals[name]?.url || lineups[name]?.lineup_url || null,
    }))
  }, [festivalShows, lineups, configFestivals])

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

  const totalArtists = allFestivals.reduce((sum, f) =>
    sum + (f.lineup?.days?.reduce((s, d) => s + d.artists.length, 0) || 0), 0)

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
      {allFestivals.length > 0 && (
        <div className="card p-4 flex flex-wrap gap-4 text-sm text-neutral-600">
          <div>
            <span className="font-semibold text-neutral-800">Festivals: </span>
            {allFestivals.length}
          </div>
          {totalArtists > 0 && (
            <div>
              <span className="font-semibold text-neutral-800">Artists: </span>
              {totalArtists}
            </div>
          )}
        </div>
      )}

      {/* Festival cards */}
      {allFestivals.length > 0 ? (
        <div className="space-y-4">
          {allFestivals.map(festival => (
            <FestivalCard
              key={festival.name}
              festivalName={festival.name}
              festivalUrl={festival.url}
              shows={festival.shows}
              lineup={festival.lineup}
              trackedArtists={trackedArtists}
              isSelected={selectedFestival === festival.name}
              onSelect={handleFestivalClick}
            />
          ))}
        </div>
      ) : (
        <div className="card p-8 text-center text-neutral-400 text-sm italic">
          No festivals tracked yet. Add festivals in the Configure tab.
        </div>
      )}

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
