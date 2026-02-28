import { useState, useEffect } from 'react'
import ArtistsTab from './ArtistsTab.jsx'
import VenuesTab  from './VenuesTab.jsx'

// ── Toggle switch ─────────────────────────────────────────────────────────────
function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      aria-checked={checked}
      className={[
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-neutral-400',
        checked ? 'bg-neutral-800' : 'bg-neutral-200',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
      ].join(' ')}
    >
      <span
        className={[
          'inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform',
          checked ? 'translate-x-6' : 'translate-x-1',
        ].join(' ')}
      />
    </button>
  )
}

// ── Add festival form ─────────────────────────────────────────────────────────
function AddFestivalForm({ onAdd, onCancel }) {
  const [name,   setName]   = useState('')
  const [url,    setUrl]    = useState('')
  const [saving, setSaving] = useState(false)
  const [error,  setError]  = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim() || !url.trim()) return
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/festivals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), url: url.trim() }),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to add festival')
      }
      const festival = await res.json()
      onAdd(festival)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card p-4 space-y-3">
      <h3 className="font-semibold text-neutral-800">Add Festival</h3>
      {error && <p className="text-sm text-neutral-800">{error}</p>}
      <div>
        <label className="block text-xs font-medium text-neutral-600 mb-1">Festival Name</label>
        <input
          className="input"
          placeholder="e.g. Bonnaroo Music Festival"
          value={name}
          onChange={e => setName(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-neutral-600 mb-1">Lineup URL</label>
        <input
          className="input"
          type="url"
          placeholder="https://festival.com/lineup"
          value={url}
          onChange={e => setUrl(e.target.value)}
          required
        />
      </div>
      <div className="flex gap-2">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? 'Adding…' : 'Add Festival'}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

// ── Lineup editor ─────────────────────────────────────────────────────────────
function LineupEditor({ festivalName, lineup, onSave, onCancel }) {
  const [imageUrl, setImageUrl] = useState(lineup?.image_url || '')
  const [venue,    setVenue]    = useState(lineup?.venue || '')
  const [city,     setCity]     = useState(lineup?.city || '')
  const [days,     setDays]     = useState(() => {
    if (!lineup?.days?.length) return []
    return lineup.days.map(d => ({
      label: d.label || '',
      date: d.date || '',
      artists: d.artists?.map(a => ({ name: a.name, headliner: a.headliner || false })) || [],
    }))
  })
  const [saving,   setSaving]   = useState(false)
  const [error,    setError]    = useState(null)

  function addDay() {
    setDays(prev => [...prev, { label: '', date: '', artists: [] }])
  }

  function removeDay(dayIdx) {
    setDays(prev => prev.filter((_, i) => i !== dayIdx))
  }

  function updateDayLabel(dayIdx, label) {
    setDays(prev => prev.map((d, i) => i === dayIdx ? { ...d, label } : d))
  }

  function addArtist(dayIdx) {
    setDays(prev => prev.map((d, i) =>
      i === dayIdx ? { ...d, artists: [...d.artists, { name: '', headliner: false }] } : d
    ))
  }

  function removeArtist(dayIdx, artistIdx) {
    setDays(prev => prev.map((d, i) =>
      i === dayIdx ? { ...d, artists: d.artists.filter((_, j) => j !== artistIdx) } : d
    ))
  }

  function updateArtistName(dayIdx, artistIdx, name) {
    setDays(prev => prev.map((d, i) =>
      i === dayIdx ? {
        ...d,
        artists: d.artists.map((a, j) => j === artistIdx ? { ...a, name } : a),
      } : d
    ))
  }

  function toggleHeadliner(dayIdx, artistIdx) {
    setDays(prev => prev.map((d, i) =>
      i === dayIdx ? {
        ...d,
        artists: d.artists.map((a, j) => j === artistIdx ? { ...a, headliner: !a.headliner } : a),
      } : d
    ))
  }

  function handlePasteArtists(dayIdx, e) {
    const text = e.clipboardData.getData('text')
    // If pasting multiple lines, add them all as artists
    const lines = text.split(/\n/).map(l => l.trim()).filter(Boolean)
    if (lines.length > 1) {
      e.preventDefault()
      setDays(prev => prev.map((d, i) => {
        if (i !== dayIdx) return d
        const existing = new Set(d.artists.map(a => a.name.toLowerCase()))
        const newArtists = lines
          .filter(l => !existing.has(l.toLowerCase()))
          .map((name, idx) => ({ name, headliner: idx < 3 && d.artists.length === 0 }))
        return { ...d, artists: [...d.artists.filter(a => a.name), ...newArtists] }
      }))
    }
  }

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      // Filter out empty artists and days with no label
      const cleanDays = days
        .filter(d => d.label.trim())
        .map(d => ({
          label: d.label.trim(),
          date: d.date || undefined,
          artists: d.artists
            .filter(a => a.name.trim())
            .map(a => ({ name: a.name.trim(), headliner: a.headliner })),
        }))

      const res = await fetch(`/api/festival-lineups/${encodeURIComponent(festivalName)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_url: imageUrl.trim() || null,
          venue: venue.trim() || null,
          city: city.trim() || null,
          days: cleanDays,
        }),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to save lineup')
      }
      const saved = await res.json()
      onSave(saved)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="px-4 pb-4 space-y-4 border-t border-neutral-100 bg-neutral-50/50">
      <h4 className="text-xs font-bold uppercase tracking-wide text-neutral-500 pt-3">Edit Lineup</h4>

      {error && <p className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">{error}</p>}

      {/* Poster URL */}
      <div>
        <label className="block text-xs font-medium text-neutral-600 mb-1">Poster Image URL</label>
        <input
          className="input text-xs"
          placeholder="https://festival.com/poster.jpg"
          value={imageUrl}
          onChange={e => setImageUrl(e.target.value)}
        />
        {imageUrl && (
          <img src={imageUrl} alt="Poster preview" className="mt-2 max-h-32 rounded border border-neutral-200" />
        )}
      </div>

      {/* Venue / City */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">Venue</label>
          <input
            className="input text-xs"
            placeholder="e.g. Harriet Island Regional Park"
            value={venue}
            onChange={e => setVenue(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">City</label>
          <input
            className="input text-xs"
            placeholder="e.g. Saint Paul, MN"
            value={city}
            onChange={e => setCity(e.target.value)}
          />
        </div>
      </div>

      {/* Days */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-neutral-600">Lineup by Day</label>
          <button type="button" onClick={addDay} className="text-xs text-neutral-600 hover:text-neutral-900 font-medium">
            + Add Day
          </button>
        </div>

        {days.length === 0 && (
          <p className="text-xs text-neutral-400 italic py-2">
            No lineup days. Click "Add Day" to start building the lineup, or just use the poster image.
          </p>
        )}

        {days.map((day, dayIdx) => (
          <div key={dayIdx} className="bg-white rounded border border-neutral-200 p-3 space-y-2">
            <div className="flex items-center gap-2">
              <input
                className="input text-xs flex-1"
                placeholder="Day label (e.g. Friday, Saturday)"
                value={day.label}
                onChange={e => updateDayLabel(dayIdx, e.target.value)}
              />
              <button
                type="button"
                onClick={() => removeDay(dayIdx)}
                className="text-xs text-neutral-400 hover:text-neutral-700 px-1"
                title="Remove day"
              >
                &times;
              </button>
            </div>

            {/* Artists for this day */}
            <div className="space-y-1">
              {day.artists.map((artist, artistIdx) => (
                <div key={artistIdx} className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => toggleHeadliner(dayIdx, artistIdx)}
                    className={`w-5 h-5 rounded text-[10px] flex-shrink-0 font-bold border transition-colors ${
                      artist.headliner
                        ? 'bg-neutral-800 text-white border-neutral-800'
                        : 'bg-white text-neutral-300 border-neutral-200 hover:border-neutral-400'
                    }`}
                    title={artist.headliner ? 'Headliner (click to toggle)' : 'Not headliner (click to toggle)'}
                  >
                    H
                  </button>
                  <input
                    className="input text-xs flex-1"
                    placeholder="Artist name"
                    value={artist.name}
                    onChange={e => updateArtistName(dayIdx, artistIdx, e.target.value)}
                    onPaste={e => handlePasteArtists(dayIdx, e)}
                  />
                  <button
                    type="button"
                    onClick={() => removeArtist(dayIdx, artistIdx)}
                    className="text-xs text-neutral-400 hover:text-neutral-700 px-1"
                    title="Remove artist"
                  >
                    &times;
                  </button>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => addArtist(dayIdx)}
              className="text-[11px] text-neutral-500 hover:text-neutral-700 font-medium"
            >
              + Add Artist
            </button>
          </div>
        ))}
      </div>

      {/* Save / Cancel */}
      <div className="flex gap-2 pt-1">
        <button onClick={handleSave} className="btn-primary text-sm" disabled={saving}>
          {saving ? 'Saving…' : 'Save Lineup'}
        </button>
        <button onClick={onCancel} className="btn-ghost text-sm">Cancel</button>
      </div>
    </div>
  )
}

// ── Festival row ──────────────────────────────────────────────────────────────
function FestivalRow({ festival, lineup, onTogglePause, onDelete, onLineupSaved }) {
  const [togglingPause, setTogglingPause] = useState(false)
  const [deleting,      setDeleting]      = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [editing,       setEditing]       = useState(false)

  const artistCount = lineup?.days?.reduce((s, d) => s + (d.artists?.length || 0), 0) || 0

  async function handlePause(val) {
    setTogglingPause(true)
    try {
      await fetch(`/api/festivals/${encodeURIComponent(festival.name)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paused: val }),
      })
      onTogglePause(festival.name, val)
    } catch (e) {
      console.error(e)
    } finally {
      setTogglingPause(false)
    }
  }

  async function handleDelete() {
    setDeleting(true)
    try {
      await fetch(`/api/festivals/${encodeURIComponent(festival.name)}`, { method: 'DELETE' })
      onDelete(festival.name)
    } catch (e) {
      console.error(e)
      setDeleting(false)
    }
  }

  function handleLineupSaved(saved) {
    setEditing(false)
    if (onLineupSaved) onLineupSaved(festival.name, saved)
  }

  return (
    <div className={`border-b border-neutral-50 last:border-0 transition-opacity ${festival.paused ? 'opacity-60' : ''}`}>
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-neutral-900 text-sm">{festival.name}</span>
            {festival.paused && <span className="badge-paused">Paused</span>}
            {artistCount > 0 && (
              <span className="text-[10px] text-neutral-400">{artistCount} artists</span>
            )}
            {!artistCount && lineup?.image_url && (
              <span className="text-[10px] text-neutral-400">poster only</span>
            )}
          </div>
          <a
            href={festival.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-neutral-500 hover:underline truncate block mt-0.5 max-w-xs"
          >
            {festival.url}
          </a>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <button
            onClick={() => setEditing(e => !e)}
            className="text-xs px-2 py-1 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded transition-colors"
          >
            {editing ? 'Close' : 'Edit Lineup'}
          </button>

          <div className="flex items-center gap-1.5">
            <span className="text-xs text-neutral-500 hidden sm:inline">
              {festival.paused ? 'Paused' : 'Active'}
            </span>
            <Toggle checked={festival.paused} onChange={handlePause} disabled={togglingPause} />
          </div>

          {confirmDelete ? (
            <div className="flex items-center gap-1">
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="text-xs px-2 py-1 bg-neutral-900 text-white rounded hover:bg-neutral-700"
              >
                {deleting ? '…' : 'Confirm'}
              </button>
              <button onClick={() => setConfirmDelete(false)} className="text-xs px-2 py-1 bg-neutral-100 text-neutral-600 rounded">
                Cancel
              </button>
            </div>
          ) : (
            <button onClick={() => setConfirmDelete(true)} className="btn-danger">Remove</button>
          )}
        </div>
      </div>

      {editing && (
        <LineupEditor
          festivalName={festival.name}
          lineup={lineup}
          onSave={handleLineupSaved}
          onCancel={() => setEditing(false)}
        />
      )}
    </div>
  )
}

// ── Festivals section ─────────────────────────────────────────────────────────
function FestivalsSection() {
  const [festivals, setFestivals] = useState([])
  const [lineups,   setLineups]   = useState({})
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [showAdd,   setShowAdd]   = useState(false)
  const [scraping,  setScraping]  = useState(false)
  const [scrapeMsg, setScrapeMsg] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/festivals').then(r => r.json()),
      fetch('/api/festival-lineups').then(r => r.json()),
    ])
      .then(([fests, lu]) => {
        setFestivals(fests)
        setLineups(lu || {})
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function handleTogglePause(name, val) {
    setFestivals(prev => prev.map(f => f.name === name ? { ...f, paused: val } : f))
  }
  function handleDelete(name) {
    setFestivals(prev => prev.filter(f => f.name !== name))
  }
  function handleAdd(festival) {
    setFestivals(prev => [...prev, festival])
    setShowAdd(false)
  }
  function handleLineupSaved(name, saved) {
    setLineups(prev => ({ ...prev, [name]: saved }))
  }

  async function handleRefreshPosters() {
    setScraping(true)
    setScrapeMsg(null)
    try {
      const res = await fetch('/api/festival-lineups/refresh', { method: 'POST' })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Refresh failed')
      }
      const data = await res.json()
      const count = Object.keys(data.lineups || {}).length
      setLineups(data.lineups || {})
      setScrapeMsg(`Updated poster images for ${count} festival${count !== 1 ? 's' : ''}`)
    } catch (e) {
      setScrapeMsg(`Error: ${e.message}`)
    } finally {
      setScraping(false)
    }
  }

  if (loading) return <Spinner />
  if (error)   return <ErrBox message={error} />

  const activeCount = festivals.filter(f => !f.paused).length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="text-sm text-neutral-500 flex-1">
          {activeCount} active / {festivals.length} total
        </div>
        <button
          className="btn-ghost text-sm"
          onClick={handleRefreshPosters}
          disabled={scraping}
        >
          {scraping ? 'Fetching posters…' : 'Refresh Posters'}
        </button>
        <button className="btn-primary" onClick={() => setShowAdd(s => !s)}>
          {showAdd ? 'Cancel' : '+ Add Festival'}
        </button>
      </div>

      {scrapeMsg && (
        <div className={`text-xs px-3 py-2 rounded ${scrapeMsg.startsWith('Error') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700'}`}>
          {scrapeMsg}
        </div>
      )}

      {showAdd && <AddFestivalForm onAdd={handleAdd} onCancel={() => setShowAdd(false)} />}

      <div className="card overflow-hidden">
        <div className="px-4 py-2 text-xs font-bold uppercase tracking-wide bg-neutral-50 text-neutral-600">
          Festivals ({festivals.length})
        </div>
        {festivals.length === 0 ? (
          <p className="px-4 py-3 text-sm text-neutral-400 italic">No festivals configured.</p>
        ) : (
          festivals.map(f => (
            <FestivalRow
              key={f.name}
              festival={f}
              lineup={lineups[f.name] || null}
              onTogglePause={handleTogglePause}
              onDelete={handleDelete}
              onLineupSaved={handleLineupSaved}
            />
          ))
        )}
      </div>
    </div>
  )
}

// ── Main Configure tab ────────────────────────────────────────────────────────
const SUB_TABS = [
  { id: 'artists',   label: 'Artists' },
  { id: 'venues',    label: 'Venues' },
  { id: 'festivals', label: 'Festivals' },
]

export default function ConfigureTab() {
  const [active, setActive] = useState('artists')

  return (
    <div className="space-y-4">
      {/* Sub-tab bar */}
      <div className="flex border-b border-neutral-200">
        {SUB_TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={[
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
              active === tab.id
                ? 'border-neutral-900 text-neutral-900'
                : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      {active === 'artists'   && <ArtistsTab />}
      {active === 'venues'    && <VenuesTab />}
      {active === 'festivals' && <FestivalsSection />}
    </div>
  )
}

function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="w-8 h-8 border-2 border-neutral-200 border-t-neutral-700 rounded-full animate-spin" />
    </div>
  )
}
function ErrBox({ message }) {
  return <div className="card p-6 text-neutral-800 text-sm">{message}</div>
}
