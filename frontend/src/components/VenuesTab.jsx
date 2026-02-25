import { useState, useEffect } from 'react'

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

// ── Add venue form ────────────────────────────────────────────────────────────
function AddVenueForm({ onAdd, onCancel }) {
  const [name,    setName]    = useState('')
  const [url,     setUrl]     = useState('')
  const [city,    setCity]    = useState('')
  const [isLocal, setIsLocal] = useState(true)
  const [saving,  setSaving]  = useState(false)
  const [error,   setError]   = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim() || !url.trim() || !city.trim()) return
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/venues', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), url: url.trim(), city: city.trim(), is_local: isLocal }),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to add venue')
      }
      const venue = await res.json()
      onAdd(venue)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card p-4 space-y-3">
      <h3 className="font-semibold text-neutral-800">Add Venue</h3>
      {error && <p className="text-sm text-neutral-800">{error}</p>}
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">Venue Name</label>
          <input className="input" placeholder="e.g. First Ave" value={name} onChange={e => setName(e.target.value)} required />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">City</label>
          <input className="input" placeholder="e.g. Minneapolis, MN" value={city} onChange={e => setCity(e.target.value)} required />
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-neutral-600 mb-1">Calendar URL</label>
        <input className="input" type="url" placeholder="https://venue.com/events" value={url} onChange={e => setUrl(e.target.value)} required />
      </div>
      <div className="flex items-center gap-3">
        <Toggle checked={isLocal} onChange={setIsLocal} />
        <div>
          <span className="text-sm font-medium text-neutral-700">
            {isLocal ? 'Local venue' : 'Travel venue'}
          </span>
          <p className="text-xs text-neutral-400">
            {isLocal ? 'Within your search radius' : 'Worth the trip — tracked for artist matches only'}
          </p>
        </div>
      </div>
      <div className="flex gap-2">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? 'Adding…' : 'Add Venue'}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

// ── Venue row ─────────────────────────────────────────────────────────────────
function VenueRow({ venue, onTogglePause, onDelete }) {
  const [togglingPause, setTogglingPause] = useState(false)
  const [deleting,      setDeleting]      = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  async function handlePause(val) {
    setTogglingPause(true)
    try {
      await fetch(`/api/venues/${encodeURIComponent(venue.name)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paused: val }),
      })
      onTogglePause(venue.name, val)
    } catch (e) {
      console.error(e)
    } finally {
      setTogglingPause(false)
    }
  }

  async function handleDelete() {
    setDeleting(true)
    try {
      await fetch(`/api/venues/${encodeURIComponent(venue.name)}`, { method: 'DELETE' })
      onDelete(venue.name)
    } catch (e) {
      console.error(e)
      setDeleting(false)
    }
  }

  return (
    <div className={`flex items-center gap-3 px-4 py-3 border-b border-neutral-50 last:border-0 transition-opacity ${venue.paused ? 'opacity-60' : ''}`}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-neutral-900 text-sm">{venue.name}</span>
          {venue.paused && <span className="badge-paused">Paused</span>}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-neutral-500">{venue.city}</span>
          <a
            href={venue.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-neutral-500 hover:underline truncate max-w-xs hidden sm:inline"
          >
            {venue.url}
          </a>
        </div>
      </div>

      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-neutral-500 hidden sm:inline">
            {venue.paused ? 'Paused' : 'Active'}
          </span>
          <Toggle checked={venue.paused} onChange={handlePause} disabled={togglingPause} />
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
  )
}

// ── Venue group ───────────────────────────────────────────────────────────────
function VenueGroup({ title, venues, onTogglePause, onDelete, accentClass }) {
  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-2 text-xs font-bold uppercase tracking-wide bg-neutral-50 text-neutral-600">
        {title} ({venues.length})
      </div>
      {venues.length === 0 ? (
        <p className="px-4 py-3 text-sm text-neutral-400 italic">No venues in this group.</p>
      ) : (
        venues.map(v => (
          <VenueRow key={v.name} venue={v} onTogglePause={onTogglePause} onDelete={onDelete} />
        ))
      )}
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function VenuesTab() {
  const [venues,  setVenues]  = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [showAdd, setShowAdd] = useState(false)
  const [search,  setSearch]  = useState('')

  useEffect(() => {
    fetch('/api/venues')
      .then(r => r.json())
      .then(setVenues)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function handleTogglePause(name, val) {
    setVenues(prev => prev.map(v => v.name === name ? { ...v, paused: val } : v))
  }
  function handleDelete(name) {
    setVenues(prev => prev.filter(v => v.name !== name))
  }
  function handleAdd(venue) {
    setVenues(prev => [...prev, venue])
    setShowAdd(false)
  }

  if (loading) return <Spinner />
  if (error)   return <ErrBox message={error} />

  const q = search.toLowerCase()
  const filtered = q
    ? venues.filter(v => v.name.toLowerCase().includes(q) || v.city.toLowerCase().includes(q))
    : venues

  const local  = filtered.filter(v => v.is_local)
  const travel = filtered.filter(v => !v.is_local)
  const activeCount = venues.filter(v => !v.paused).length

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          className="input flex-1 min-w-48"
          placeholder="Search venues…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="text-sm text-neutral-500">
          {activeCount} active / {venues.length} total
        </div>
        <button className="btn-primary" onClick={() => setShowAdd(s => !s)}>
          {showAdd ? 'Cancel' : '+ Add Venue'}
        </button>
      </div>

      {showAdd && <AddVenueForm onAdd={handleAdd} onCancel={() => setShowAdd(false)} />}

      <VenueGroup
        title="Local Venues"
        venues={local}
        onTogglePause={handleTogglePause}
        onDelete={handleDelete}
      />
      <VenueGroup
        title="Travel Venues"
        venues={travel}
        onTogglePause={handleTogglePause}
        onDelete={handleDelete}
      />

      {filtered.length === 0 && (
        <p className="text-center text-neutral-400 py-8">No venues match your search.</p>
      )}
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
