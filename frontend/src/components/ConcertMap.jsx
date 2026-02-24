import { useMemo } from 'react'
import { MapContainer, TileLayer, Circle, Marker, Popup } from 'react-leaflet'
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

// Miles to meters for Leaflet Circle radius
const MILES_TO_METERS = 1609.34

/**
 * Concert Map — shows a Leaflet map with:
 * - A circle representing the search radius from center city
 * - Pins for each show that has lat/lon data
 * - Green pins for new shows, red for sold out, blue for on sale
 *
 * Props:
 *   centerLat, centerLon — center city coordinates
 *   radiusMiles — search radius
 *   shows — array of { artist, date, venue, city, lat, lon, status, is_new }
 */
export default function ConcertMap({ centerLat, centerLon, radiusMiles, shows }) {
  // Deduplicate pins by venue location (group shows at same lat/lon)
  const pins = useMemo(() => {
    const byLocation = {}
    for (const show of shows) {
      if (show.lat == null || show.lon == null) continue
      const key = `${show.lat.toFixed(4)},${show.lon.toFixed(4)}`
      if (!byLocation[key]) {
        byLocation[key] = { lat: show.lat, lon: show.lon, shows: [] }
      }
      byLocation[key].shows.push(show)
    }
    return Object.values(byLocation)
  }, [shows])

  if (centerLat == null || centerLon == null) {
    return (
      <div className="card p-6 text-center text-slate-400 text-sm italic">
        Map unavailable — no geocoded data yet. Run a Cowork scrape session to populate coordinates.
      </div>
    )
  }

  return (
    <div className="card overflow-hidden" style={{ height: 400 }}>
      <MapContainer
        center={[centerLat, centerLon]}
        zoom={7}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Radius circle */}
        <Circle
          center={[centerLat, centerLon]}
          radius={radiusMiles * MILES_TO_METERS}
          pathOptions={{
            color: '#6366f1',
            fillColor: '#6366f1',
            fillOpacity: 0.06,
            weight: 2,
            dashArray: '8 4',
          }}
        />

        {/* Center city marker */}
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

        {/* Show pins */}
        {pins.map((pin, i) => {
          const hasNew = pin.shows.some(s => s.is_new)
          const allSoldOut = pin.shows.every(s => s.status === 'sold_out')
          const icon = hasNew ? NEW_ICON : allSoldOut ? SOLD_OUT_ICON : DEFAULT_ICON

          return (
            <Marker key={i} position={[pin.lat, pin.lon]} icon={icon}>
              <Popup>
                <div className="text-sm space-y-1">
                  {pin.shows.map((s, j) => (
                    <div key={j}>
                      <strong>{s.artist}</strong>
                      <br />
                      {s.date} &middot; {s.venue}
                      {s.distance_miles != null && (
                        <span className="text-slate-500"> &middot; {s.distance_miles} mi</span>
                      )}
                      {s.is_new && <span className="ml-1 text-emerald-600 font-semibold">NEW</span>}
                      {s.status === 'sold_out' && <span className="ml-1 text-red-500 font-semibold">SOLD OUT</span>}
                    </div>
                  ))}
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </div>
  )
}
