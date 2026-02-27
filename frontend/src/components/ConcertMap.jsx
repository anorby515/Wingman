import { useMemo, useEffect } from 'react'
import { MapContainer, TileLayer, Circle, Marker, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet default marker icon issue with bundlers
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const NEW_ICON = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const DEFAULT_ICON = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const SOLD_OUT_ICON = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const VENUE_ICON = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-violet.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const COMING_SOON_ICON = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-orange.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const FESTIVAL_ICON = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

/**
 * Child component that tracks map viewport changes and reports bounds.
 */
function MapEvents({ onBoundsChange }) {
  const map = useMapEvents({
    moveend() {
      onBoundsChange(map.getBounds())
    },
  })

  // Report initial bounds after map is ready
  useEffect(() => {
    // Small delay ensures map tiles have loaded and bounds are accurate
    const timer = setTimeout(() => {
      onBoundsChange(map.getBounds())
    }, 200)
    return () => clearTimeout(timer)
  }, [map, onBoundsChange])

  return null
}

/**
 * Concert Map — shows a Leaflet map with:
 * - A small marker for the home city (Des Moines)
 * - Pins for artist shows (green=new, red=sold out, blue=on sale)
 * - Pins for tracked venues (violet)
 * - Hover tooltips showing event details
 * - Viewport-based filtering reported via onBoundsChange
 * - Pin filtering by mapFilter (selected artist or venue)
 *
 * Props:
 *   centerLat, centerLon — home city coordinates (map starting position)
 *   artistShows — array of { artist, date, venue, city, lat, lon, status, is_new }
 *   venueShows — array of { venueName, lat, lon, events: [{ date, artist, tracked }] }
 *   festivalShows — array of { festivalName, date, venue, city, lat, lon, event_name, is_new }
 *   mapFilter — { type: 'artist'|'venue', name: string } | null
 *   onBoundsChange — callback(LatLngBounds) when the viewport changes
 */
export default function ConcertMap({ centerLat, centerLon, artistShows, venueShows, festivalShows, mapFilter, onBoundsChange }) {
  // Filter artist shows based on mapFilter
  const filteredArtistShows = useMemo(() => {
    if (!artistShows) return []
    if (!mapFilter) return artistShows
    if (mapFilter.type === 'artist') return artistShows.filter(s => s.artist === mapFilter.name)
    if (mapFilter.type === 'venue') return [] // hide artist pins when venue is selected
    return artistShows
  }, [artistShows, mapFilter])

  // Filter venue shows based on mapFilter
  const filteredVenueShows = useMemo(() => {
    if (!venueShows) return []
    if (!mapFilter) return venueShows
    if (mapFilter.type === 'venue') return venueShows.filter(v => v.venueName === mapFilter.name)
    if (mapFilter.type === 'artist') return [] // hide venue pins when artist is selected
    return venueShows
  }, [venueShows, mapFilter])

  // Group artist shows by lat/lon (multiple shows at same venue)
  const artistPins = useMemo(() => {
    const byLocation = {}
    for (const show of filteredArtistShows) {
      if (show.lat == null || show.lon == null) continue
      const key = `${show.lat.toFixed(4)},${show.lon.toFixed(4)}`
      if (!byLocation[key]) {
        byLocation[key] = { lat: show.lat, lon: show.lon, shows: [] }
      }
      byLocation[key].shows.push(show)
    }
    return Object.values(byLocation)
  }, [filteredArtistShows])

  // Venue pins (each venue is a single point with its events)
  const venuePins = useMemo(() => {
    if (!filteredVenueShows) return []
    return filteredVenueShows.filter(v => v.lat != null && v.lon != null)
  }, [filteredVenueShows])

  // Festival pins (group by lat/lon like artist pins)
  const festivalPins = useMemo(() => {
    if (!festivalShows || festivalShows.length === 0) return []
    const byLocation = {}
    for (const show of festivalShows) {
      if (show.lat == null || show.lon == null) continue
      const key = `${show.lat.toFixed(4)},${show.lon.toFixed(4)}`
      if (!byLocation[key]) {
        byLocation[key] = { lat: show.lat, lon: show.lon, shows: [] }
      }
      byLocation[key].shows.push(show)
    }
    return Object.values(byLocation)
  }, [festivalShows])

  if (centerLat == null || centerLon == null) {
    return (
      <div className="card p-6 text-center text-slate-400 text-sm italic">
        Map unavailable — no geocoded data yet. Data is updated daily via GitHub Actions.
      </div>
    )
  }

  return (
    <div className="card overflow-hidden" style={{ height: 500 }}>
      <MapContainer
        center={[centerLat, centerLon]}
        zoom={5}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Track viewport changes */}
        <MapEvents onBoundsChange={onBoundsChange} />

        {/* Home city marker */}
        <Circle
          center={[centerLat, centerLon]}
          radius={5000}
          pathOptions={{
            color: '#6366f1',
            fillColor: '#6366f1',
            fillOpacity: 0.4,
            weight: 2,
          }}
        />

        {/* Artist show pins */}
        {artistPins.map((pin, i) => {
          const hasNew        = pin.shows.some(s => s.is_new)
          const allSoldOut    = pin.shows.every(s => s.status === 'sold_out')
          const allComingSoon = pin.shows.every(s => s.source === 'tm')
          const icon = hasNew        ? NEW_ICON
                     : allSoldOut   ? SOLD_OUT_ICON
                     : allComingSoon ? COMING_SOON_ICON
                     : DEFAULT_ICON

          return (
            <Marker key={`a-${i}`} position={[pin.lat, pin.lon]} icon={icon}>
              <Tooltip direction="top" offset={[0, -30]} opacity={0.95}>
                <div className="text-xs space-y-0.5" style={{ maxWidth: 260 }}>
                  {pin.shows.map((s, j) => (
                    <div key={j}>
                      <strong>{s.artist}</strong>
                      {' \u00b7 '}{s.date}{' \u00b7 '}{s.venue}
                      {s.is_new && <span className="ml-1 text-emerald-600 font-semibold">NEW</span>}
                      {s.source === 'tm' && (
                        <span className="ml-1 text-amber-600 font-semibold">
                          {s.onsale_tbd ? 'On Sale TBD'
                            : s.onsale_datetime
                            ? `On Sale ${new Date(s.onsale_datetime).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
                            : 'Coming Soon'}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </Tooltip>
            </Marker>
          )
        })}

        {/* Venue pins */}
        {venuePins.map((venue, i) => {
          const events = venue.events || []

          return (
            <Marker key={`v-${i}`} position={[venue.lat, venue.lon]} icon={VENUE_ICON}>
              <Tooltip direction="top" offset={[0, -30]} opacity={0.95}>
                <div className="text-xs space-y-0.5" style={{ maxWidth: 260 }}>
                  <div className="font-bold text-sm">{venue.venueName}</div>
                  {events.map((e, j) => (
                    <div key={j}>
                      {e.date}{' \u00b7 '}{e.artist}
                      {e.tracked && <span className="ml-1 text-emerald-600 font-semibold">\u2605</span>}
                    </div>
                  ))}
                  {events.length === 0 && (
                    <div className="text-slate-400 italic">No events data yet</div>
                  )}
                </div>
              </Tooltip>
            </Marker>
          )
        })}

        {/* Festival pins */}
        {festivalPins.map((pin, i) => (
          <Marker key={`f-${i}`} position={[pin.lat, pin.lon]} icon={FESTIVAL_ICON}>
            <Tooltip direction="top" offset={[0, -30]} opacity={0.95}>
              <div className="text-xs space-y-0.5" style={{ maxWidth: 260 }}>
                {pin.shows.map((s, j) => (
                  <div key={j}>
                    <strong>{s.festivalName}</strong>
                    {' \u00b7 '}{s.date}{' \u00b7 '}{s.venue}
                    {s.is_new && <span className="ml-1 text-emerald-600 font-semibold">NEW</span>}
                  </div>
                ))}
              </div>
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
