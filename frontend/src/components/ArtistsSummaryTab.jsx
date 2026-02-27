import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
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

function isInBounds(lat, lon, bounds) {
  if (!bounds) return true
  if (lat == null || lon == null) return false
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  return lat >= sw.lat && lat <= ne.lat && lon >= sw.lng && lon <= ne.lng
}

// ── Multi-select filter dropdown ─────────────────────────────────────────────
function FilterDropdown({ label, options, selected, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const toggle = (val) => {
    if (selected.includes(val)) {
      onChange(selected.filter(s => s !== val))
    } else {
      onChange([...selected, val])
    }
  }

  const activeCount = selected.length

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`px-2.5 py-1 text-xs rounded-full transition-colors whitespace-nowrap
          ${activeCount > 0
            ? 'bg-neutral-800 text-white'
            : 'text-neutral-500 hover:bg-neutral-100 border border-neutral-200'
          }`}
      >
        {label}{activeCount > 0 ? ` (${activeCount})` : ''}
        <span className="ml-1 text-[10px]">{open ? '\u25B4' : '\u25BE'}</span>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 bg-white border border-neutral-200 rounded-sm shadow-lg z-50 max-h-60 overflow-y-auto min-w-[200px]">
          {selected.length > 0 && (
            <button
              onClick={() => onChange([])}
              className="w-full px-3 py-1.5 text-xs text-neutral-500 hover:bg-neutral-50 text-left border-b border-neutral-100"
            >
              Clear {label.toLowerCase()}
            </button>
          )}
          {options.map(opt => (
            <label
              key={opt}
              className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-neutral-50 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selected.includes(opt)}
                onChange={() => toggle(opt)}
                className="rounded border-neutral-300 text-neutral-800 focus:ring-neutral-400"
              />
              <span className="truncate text-neutral-700">{opt}</span>
            </label>
          ))}
          {options.length === 0 && (
            <div className="px-3 py-2 text-xs text-neutral-400 italic">No options</div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Show row (date-sorted flat list) ─────────────────────────────────────────
function ShowRow({ show, showArtist = true, isHighlighted = false, onArtistClick }) {
  const dateObj = new Date(show.raw_date || show.date)
  const month = !isNaN(dateObj) ? dateObj.toLocaleString(undefined, { month: 'short' }).toUpperCase() : '???'
  const day = !isNaN(dateObj) ? dateObj.getDate() : '--'
  const isComingSoon = show.status === 'coming_soon'
  const artistUrl = show._artistUrl

  function handleRowClick(e) {
    if (!onArtistClick) return
    // Don't intercept clicks on links
    if (e.target.closest('a')) return
    onArtistClick(show._artist)
  }

  return (
    <div
      onClick={handleRowClick}
      className={`flex items-center gap-3 px-3 py-2.5 border-b border-neutral-100 last:border-b-0 transition-colors
        ${onArtistClick ? 'cursor-pointer' : ''}
        ${isHighlighted
          ? 'bg-neutral-100 border-l-2 border-l-neutral-700'
          : 'hover:bg-neutral-50/50'
        }`}
    >
      {/* Date block */}
      <div className="flex-shrink-0 w-11 text-center">
        <div className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider leading-none">{month}</div>
        <div className="text-xl font-bold text-neutral-800 leading-tight">{day}</div>
      </div>

      {/* Divider */}
      <div className="w-px h-9 bg-neutral-200 flex-shrink-0" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        {showArtist && (
          <div className="flex items-center gap-1.5">
            {artistUrl ? (
              <a
                href={artistUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-sm text-neutral-900 hover:text-neutral-600 hover:underline truncate"
              >
                {show._artist}
              </a>
            ) : (
              <span className="font-semibold text-sm text-neutral-900 truncate">{show._artist}</span>
            )}
            {show._isFavorite && <span className="text-amber-400 text-xs" title="Favorite">{'\u2605'}</span>}
          </div>
        )}
        <div className="text-xs text-neutral-500 truncate">
          {show.venue}
          <span className="text-neutral-300 mx-1">&middot;</span>
          {show.city}
        </div>
        {isComingSoon && (
          <div className="text-[10px] text-orange-600 mt-0.5">
            {show.onsale_tbd
              ? 'On-sale date TBD'
              : show.onsale_datetime
              ? `On sale ${fmtOnsale(show.onsale_datetime)}`
              : 'On-sale date not announced'}
          </div>
        )}
      </div>

      {/* Status + TM link */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className={`hidden sm:inline text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
          isComingSoon
            ? 'bg-orange-50 text-orange-600 border border-orange-200'
            : 'bg-blue-50 text-blue-600 border border-blue-200'
        }`}>
          {isComingSoon ? 'Soon' : 'On Sale'}
        </span>
        {/* Mobile status dot */}
        <span className={`sm:hidden w-2 h-2 rounded-full flex-shrink-0 ${
          isComingSoon ? 'bg-orange-400' : 'bg-blue-400'
        }`} />
        {show.ticketmaster_url && (
          <a
            href={show.ticketmaster_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-neutral-400 hover:text-neutral-700 transition-colors whitespace-nowrap"
            title="Buy on Ticketmaster"
          >
            TM&nbsp;&rarr;
          </a>
        )}
      </div>
    </div>
  )
}

// ── Artist group header (for grouped-by-artist mode) ─────────────────────────
function ArtistGroupHeader({ artist, url, genre, isFavorite, showCount, isSelected, onSelect }) {
  function handleClick(e) {
    if (!onSelect) return
    // Don't intercept clicks on the artist URL link
    if (e.target.closest('a')) return
    onSelect(artist)
  }

  return (
    <div
      onClick={handleClick}
      className={`px-3 py-2 border-b border-neutral-200 flex items-center gap-2 sticky top-0 z-10 transition-colors
        ${onSelect ? 'cursor-pointer' : ''}
        ${isSelected
          ? 'bg-neutral-200 border-l-2 border-l-neutral-700'
          : 'bg-neutral-50 hover:bg-neutral-100'
        }`}
    >
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-sm text-neutral-800 hover:text-neutral-600 hover:underline"
        >
          {artist}
        </a>
      ) : (
        <span className="font-semibold text-sm text-neutral-800">{artist}</span>
      )}
      {isFavorite && <span className="text-amber-400 text-xs" title="Favorite">{'\u2605'}</span>}
      {genre && <span className="text-[10px] text-neutral-400">{genre}</span>}
      <span className="text-xs text-neutral-400 ml-auto">{showCount}</span>
    </div>
  )
}

// ── Map legend ───────────────────────────────────────────────────────────────
function MapLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-400 mt-2 px-1">
      <span className="flex items-center gap-1">
        <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" /> On Sale
      </span>
      <span className="flex items-center gap-1">
        <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block" /> Coming Soon
      </span>
      <span className="flex items-center gap-1">
        <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block" /> Favorite
      </span>
      <span className="flex items-center gap-1">
        <span className="w-2.5 h-2.5 rounded-full bg-purple-500 inline-block" /> Venue
      </span>
      <span className="flex items-center gap-1">
        <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 inline-block" /> Home
      </span>
    </div>
  )
}

// ── Main tab ─────────────────────────────────────────────────────────────────
export default function ArtistsSummaryTab() {
  const [shows, setShows]             = useState(null)
  const [config, setConfig]           = useState(null)
  const [comingSoon, setComingSoon]   = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)

  // Sort: 'date' (default) or 'artist' (grouped)
  const [sortMode, setSortMode] = useState('date')

  // Dropdown filters
  const [filterArtists, setFilterArtists] = useState([])
  const [filterGenres, setFilterGenres] = useState([])

  // Filter toggles (AND logic when multiple active)
  const [quickLocal, setQuickLocal]           = useState(false)
  const [quickTravel, setQuickTravel]         = useState(false)
  const [quickFavorite, setQuickFavorite]     = useState(false)
  const [quickComingSoon, setQuickComingSoon] = useState(false)
  const [quickMapArea, setQuickMapArea]       = useState(true)

  // Map viewport bounds (Leaflet LatLngBounds object)
  const [mapBounds, setMapBounds] = useState(null)

  useEffect(() => {
    if (DEMO) {
      fetch(import.meta.env.BASE_URL + 'static-data.json')
        .then(r => r.json())
        .then(data => {
          setShows({
            api_configured: true,
            artist_shows: data.state?.artist_shows || {},
            venue_shows: data.state?.venue_shows || {},
            last_refreshed: data.coming_soon_fetched || null,
          })
          setComingSoon(data.coming_soon || [])
          setConfig({
            ...data.config,
            center_lat: data.config?.center_lat ?? data.state?.center_lat,
            center_lon: data.config?.center_lon ?? data.state?.center_lon,
          })
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    } else {
      Promise.all([
        fetch('/api/shows').then(r => r.json()),
        fetch('/api/config').then(r => r.json()),
      ])
        .then(([s, cfg]) => { setShows(s); setConfig(cfg); setComingSoon(s.coming_soon || []) })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false))
    }
  }, [])

  const artistShows = shows?.artist_shows ?? {}
  const venueShowsData = shows?.venue_shows ?? {}
  const configArtists = config?.artists || {}
  const configVenues = config?.venues || {}

  // Build coming-soon key set from the coming_soon array (same source as On Sale Soon tab)
  const comingSoonKeys = useMemo(() => {
    const keys = new Set()
    for (const cs of comingSoon) {
      keys.add(`${cs.artist}|${cs.date}|${cs.venue}`)
    }
    return keys
  }, [comingSoon])

  // Build venue lookup: lowercase venue name → config
  const venueLookup = useMemo(() => {
    const map = {}
    for (const [name, cfg] of Object.entries(configVenues)) {
      if (cfg) map[name.toLowerCase()] = cfg
    }
    return map
  }, [configVenues])

  // ── Aggregate artist shows + venue shows into a flat list ──
  const allShows = useMemo(() => {
    const arr = []
    const seen = new Set()

    function venueFlags(venueName) {
      const cfg = venueLookup[venueName?.toLowerCase()]
      return {
        _isLocalVenue: cfg?.is_local === true,
        _isTravelVenue: cfg?.is_local === false,
      }
    }

    // Artist shows
    for (const [artist, showList] of Object.entries(artistShows)) {
      const info = configArtists[artist] || {}
      for (const show of showList) {
        const key = `${artist}|${show.raw_date}|${show.venue}`
        seen.add(key)
        // Tag coming-soon shows using the coming_soon array (same source as On Sale Soon tab)
        const csKey = `${artist}|${show.date}|${show.venue}`
        const isCS = show.status === 'coming_soon' || comingSoonKeys.has(csKey)
        arr.push({
          ...show,
          _artist: artist,
          _artistUrl: info.url || null,
          _genre: info.genre || 'Other',
          _isFavorite: info.favorite === true,
          status: isCS ? 'coming_soon' : (show.status || 'on_sale'),
          ...venueFlags(show.venue),
        })
      }
    }

    // Venue shows: merge in, dedup against artist shows
    for (const [trackedVenue, showList] of Object.entries(venueShowsData)) {
      for (const show of showList) {
        const artist = show.artist || trackedVenue
        const key = `${artist}|${show.raw_date}|${show.venue}`
        if (seen.has(key)) continue
        seen.add(key)
        const info = configArtists[artist] || {}
        arr.push({
          ...show,
          _artist: artist,
          _artistUrl: info.url || null,
          _genre: info.genre || 'Other',
          _isFavorite: info.favorite === true,
          _source: 'venue',
          _trackedVenue: trackedVenue,
          ...venueFlags(show.venue),
        })
      }
    }

    return arr
  }, [artistShows, venueShowsData, configArtists, venueLookup, comingSoonKeys])

  // ── Genre filter options (from visible shows) ──
  const genreFilterOptions = useMemo(() => {
    const genres = new Set()
    for (const show of allShows) {
      if (show._genre) genres.add(show._genre)
    }
    return [...genres].sort()
  }, [allShows])

  // ── Artist filter options (tracked artists only, not venue-sourced) ──
  const artistFilterOptions = useMemo(() => {
    const trackedNames = new Set(Object.keys(configArtists))
    const visible = new Set()
    for (const show of allShows) {
      if (!trackedNames.has(show._artist)) continue
      if (filterGenres.length > 0 && !filterGenres.includes(show._genre)) continue
      if (quickLocal && !show._isLocalVenue) continue
      if (quickTravel && !show._isTravelVenue) continue
      if (quickFavorite && !show._isFavorite) continue
      if (quickComingSoon && show.status !== 'coming_soon') continue
      if (quickMapArea && !isInBounds(show.lat, show.lon, mapBounds)) continue
      visible.add(show._artist)
    }
    return [...visible].sort()
  }, [allShows, configArtists, filterGenres, quickLocal, quickTravel, quickFavorite, quickComingSoon, quickMapArea, mapBounds])

  // ── Apply all filters (AND logic) ──
  const filteredShows = useMemo(() => {
    return allShows.filter(show => {
      if (filterArtists.length > 0 && !filterArtists.includes(show._artist)) return false
      if (filterGenres.length > 0 && !filterGenres.includes(show._genre)) return false
      if (quickLocal    && !show._isLocalVenue)  return false
      if (quickTravel && !show._isTravelVenue) return false
      if (quickFavorite && !show._isFavorite) return false
      if (quickComingSoon && show.status !== 'coming_soon') return false
      if (quickMapArea && !isInBounds(show.lat, show.lon, mapBounds)) return false
      return true
    })
  }, [allShows, filterArtists, filterGenres, quickLocal, quickTravel, quickFavorite, quickComingSoon, quickMapArea, mapBounds])

  // ── Sort ──
  const sortedShows = useMemo(() => {
    const sorted = [...filteredShows]
    if (sortMode === 'date') {
      sorted.sort((a, b) => {
        const da = new Date(a.raw_date || a.date)
        const db = new Date(b.raw_date || b.date)
        return (!isNaN(da) && !isNaN(db)) ? da - db : 0
      })
    } else {
      sorted.sort((a, b) => {
        const cmp = a._artist.localeCompare(b._artist)
        if (cmp !== 0) return cmp
        const da = new Date(a.raw_date || a.date)
        const db = new Date(b.raw_date || b.date)
        return (!isNaN(da) && !isNaN(db)) ? da - db : 0
      })
    }
    return sorted
  }, [filteredShows, sortMode])

  // ── Group by artist (for artist sort mode) ──
  const groupedByArtist = useMemo(() => {
    if (sortMode !== 'artist') return null
    const groups = {}
    for (const show of sortedShows) {
      if (!groups[show._artist]) groups[show._artist] = []
      groups[show._artist].push(show)
    }
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  }, [sortedShows, sortMode])

  // ── Map pin data (filtered) ──
  const mapArtistShows = useMemo(() => {
    return filteredShows.map(show => ({
      ...show,
      artist: show._artist,
      status: 'on_sale',
      source: show.status === 'coming_soon' ? 'tm' : undefined,
    }))
  }, [filteredShows])

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

  const hasActiveFilters = filterArtists.length > 0 || filterGenres.length > 0
    || quickLocal || quickTravel || quickFavorite || quickComingSoon || quickMapArea

  const clearAllFilters = () => {
    setFilterArtists([])
    setFilterGenres([])
    setQuickLocal(false)
    setQuickTravel(false)
    setQuickFavorite(false)
    setQuickComingSoon(false)
    setQuickMapArea(false)
  }

  // Click row/header to toggle artist filter
  const handleArtistClick = useCallback((artist) => {
    setFilterArtists(prev =>
      prev.length === 1 && prev[0] === artist ? [] : [artist]
    )
  }, [])

  // Track map viewport bounds for "Map Area" quick filter
  const handleBoundsChange = useCallback((bounds) => {
    setMapBounds(bounds)
  }, [])

  if (loading) return <LoadingSpinner />
  if (error)   return <ErrorBox message={error} />

  return (
    <div className="space-y-4">
      {shows?.stale && (
        <div className="px-3 py-1.5 border border-neutral-200 text-xs text-neutral-500 italic rounded-sm">
          Data may be stale — click Refresh
        </div>
      )}

      {/* ── Map ── */}
      <section>
        <ConcertMap
          centerLat={centerLat}
          centerLon={centerLon}
          artistShows={mapArtistShows}
          venueShows={allVenueShows}
          mapFilter={null}
          onBoundsChange={handleBoundsChange}
        />
        <MapLegend />
      </section>

      {/* ── Filters + Sort ── */}
      <div className="flex items-center justify-between px-1 relative z-10">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Filters</span>
          <div className="flex items-center gap-1 text-xs flex-wrap">
            <button
              onClick={() => setQuickMapArea(v => !v)}
              className={`px-2.5 py-1 rounded-full transition-colors ${
                quickMapArea
                  ? 'bg-indigo-600 text-white'
                  : 'text-neutral-500 hover:bg-neutral-100 border border-neutral-200'
              }`}
            >
              Map Area
            </button>
            <button
              onClick={() => setQuickComingSoon(v => !v)}
              className={`px-2.5 py-1 rounded-full transition-colors ${
                quickComingSoon
                  ? 'bg-orange-600 text-white'
                  : 'text-neutral-500 hover:bg-neutral-100 border border-neutral-200'
              }`}
            >
              On Sale Soon
            </button>
            <button
              onClick={() => setQuickFavorite(v => !v)}
              className={`px-2.5 py-1 rounded-full transition-colors ${
                quickFavorite
                  ? 'bg-amber-500 text-white'
                  : 'text-neutral-500 hover:bg-neutral-100 border border-neutral-200'
              }`}
            >
              {'\u2605'} Favorites
            </button>
            <button
              onClick={() => { setQuickLocal(v => !v); setQuickTravel(false) }}
              className={`px-2.5 py-1 rounded-full transition-colors ${
                quickLocal
                  ? 'bg-neutral-700 text-white'
                  : 'text-neutral-500 hover:bg-neutral-100 border border-neutral-200'
              }`}
            >
              Local
            </button>
            <button
              onClick={() => { setQuickTravel(v => !v); setQuickLocal(false) }}
              className={`px-2.5 py-1 rounded-full transition-colors ${
                quickTravel
                  ? 'bg-neutral-700 text-white'
                  : 'text-neutral-500 hover:bg-neutral-100 border border-neutral-200'
              }`}
            >
              Travel Venues
            </button>
            <FilterDropdown label="Genre" options={genreFilterOptions} selected={filterGenres} onChange={setFilterGenres} />
            <FilterDropdown label="Artist" options={artistFilterOptions} selected={filterArtists} onChange={setFilterArtists} />
          </div>
          {hasActiveFilters && (
            <button onClick={clearAllFilters} className="text-xs text-neutral-500 hover:text-neutral-800 underline">
              Clear all
            </button>
          )}
        </div>
        <div className="flex items-center gap-1 text-xs flex-shrink-0">
          <span className="text-neutral-400 mr-1">Sort:</span>
          <button
            onClick={() => setSortMode('date')}
            className={`px-2.5 py-1 rounded-full transition-colors ${
              sortMode === 'date'
                ? 'bg-neutral-800 text-white'
                : 'text-neutral-500 hover:bg-neutral-100 border border-neutral-200'
            }`}
          >
            Date
          </button>
          <button
            onClick={() => setSortMode('artist')}
            className={`px-2.5 py-1 rounded-full transition-colors ${
              sortMode === 'artist'
                ? 'bg-neutral-800 text-white'
                : 'text-neutral-500 hover:bg-neutral-100 border border-neutral-200'
            }`}
          >
            Artist
          </button>
        </div>
      </div>

      {/* ── Show count ── */}
      <div className="px-1">
        <span className="text-xs text-neutral-500">
          {filteredShows.length} show{filteredShows.length !== 1 ? 's' : ''}
          {hasActiveFilters && <span className="text-neutral-400"> of {allShows.length}</span>}
        </span>
      </div>

      {/* ── Show list ── */}
      <section className="card overflow-hidden">
        {sortMode === 'artist' && groupedByArtist ? (
          // ── Grouped by artist ──
          groupedByArtist.length > 0 ? (
            groupedByArtist.map(([artist, shows]) => {
              const info = configArtists[artist] || {}
              const selected = filterArtists.length === 1 && filterArtists[0] === artist
              return (
                <div key={artist}>
                  <ArtistGroupHeader
                    artist={artist}
                    url={info.url || null}
                    genre={info.genre}
                    isFavorite={info.favorite === true}
                    showCount={`${shows.length} show${shows.length !== 1 ? 's' : ''}`}
                    isSelected={selected}
                    onSelect={handleArtistClick}
                  />
                  {shows.map((show, i) => (
                    <ShowRow key={i} show={show} showArtist={false} />
                  ))}
                </div>
              )
            })
          ) : (
            <EmptyState hasFilters={hasActiveFilters} />
          )
        ) : (
          // ── Flat date-sorted list ──
          sortedShows.length > 0 ? (
            sortedShows.map((show, i) => (
              <ShowRow
                key={i}
                show={show}
                showArtist={true}
                isHighlighted={filterArtists.length === 1 && filterArtists[0] === show._artist}
                onArtistClick={handleArtistClick}
              />
            ))
          ) : (
            <EmptyState hasFilters={hasActiveFilters} />
          )
        )}
      </section>

      {/* ── Flagged Items (local mode only) ── */}
      {!DEMO && <FlaggedItems />}
    </div>
  )
}

// ── Empty state ──────────────────────────────────────────────────────────────
function EmptyState({ hasFilters }) {
  return (
    <div className="p-8 text-center text-neutral-400 text-sm italic">
      {hasFilters
        ? 'No shows match the current filters.'
        : 'No shows found. Data is updated daily via GitHub Actions.'}
    </div>
  )
}

// ── Flagged Items ────────────────────────────────────────────────────────────
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
            <div className="w-2 h-2 rounded-full bg-neutral-400 mt-1.5 flex-shrink-0" />
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

