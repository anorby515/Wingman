import { useState, useEffect } from 'react'

const GENRES = ['Indie', 'Rock/Alternative', 'Country/Americana', 'Hip-Hop', 'Electronic', 'Other']

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

// ── Add artist form ───────────────────────────────────────────────────────────
function AddArtistForm({ onAdd, onCancel }) {
  const [name,  setName]  = useState('')
  const [url,   setUrl]   = useState('')
  const [genre, setGenre] = useState('Other')
  const [saving, setSaving] = useState(false)
  const [error,  setError]  = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim() || !url.trim()) return
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/artists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), url: url.trim(), genre }),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to add artist')
      }
      const artist = await res.json()
      onAdd(artist)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card p-4 space-y-3">
      <h3 className="font-semibold text-neutral-800">Add Artist</h3>
      {error && <p className="text-sm text-neutral-800">{error}</p>}
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">Name</label>
          <input
            className="input"
            placeholder="e.g. Hozier"
            value={name}
            onChange={e => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">Genre</label>
          <select
            className="input"
            value={genre}
            onChange={e => setGenre(e.target.value)}
          >
            {GENRES.map(g => <option key={g}>{g}</option>)}
          </select>
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-neutral-600 mb-1">Tour page URL</label>
        <input
          className="input"
          type="url"
          placeholder="https://artist.com/tour"
          value={url}
          onChange={e => setUrl(e.target.value)}
          required
        />
      </div>
      <div className="flex gap-2">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? 'Adding…' : 'Add Artist'}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

// ── Artist row ────────────────────────────────────────────────────────────────
function ArtistRow({ artist, onTogglePause, onDelete, onUpdate }) {
  const [togglingPause, setTogglingPause] = useState(false)
  const [togglingFav, setTogglingFav] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editUrl, setEditUrl] = useState(artist.url)
  const [editGenre, setEditGenre] = useState(artist.genre)
  const [saving, setSaving] = useState(false)

  async function handlePause(val) {
    setTogglingPause(true)
    try {
      await fetch(`/api/artists/${encodeURIComponent(artist.name)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paused: val }),
      })
      onTogglePause(artist.name, val)
    } catch (e) {
      console.error(e)
    } finally {
      setTogglingPause(false)
    }
  }

  async function handleFavorite() {
    setTogglingFav(true)
    try {
      const res = await fetch(`/api/artists/${encodeURIComponent(artist.name)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ favorite: !artist.favorite }),
      })
      if (res.ok) onUpdate(artist.name, { favorite: !artist.favorite })
    } catch (e) {
      console.error(e)
    } finally {
      setTogglingFav(false)
    }
  }

  async function handleSaveEdit() {
    setSaving(true)
    try {
      const patch = {}
      if (editUrl !== artist.url) patch.url = editUrl
      if (editGenre !== artist.genre) patch.genre = editGenre
      if (Object.keys(patch).length === 0) { setEditing(false); return }
      const res = await fetch(`/api/artists/${encodeURIComponent(artist.name)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      })
      if (res.ok) {
        onUpdate(artist.name, patch)
        setEditing(false)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  function handleCancelEdit() {
    setEditUrl(artist.url)
    setEditGenre(artist.genre)
    setEditing(false)
  }

  async function handleDelete() {
    setDeleting(true)
    try {
      await fetch(`/api/artists/${encodeURIComponent(artist.name)}`, { method: 'DELETE' })
      onDelete(artist.name)
    } catch (e) {
      console.error(e)
      setDeleting(false)
    }
  }

  return (
    <div className={`px-4 py-3 border-b border-neutral-50 last:border-0 transition-opacity ${artist.paused ? 'opacity-60' : ''}`}>
      <div className="flex items-center gap-3">
        {/* Favorite star */}
        <button
          onClick={handleFavorite}
          disabled={togglingFav}
          className={`text-lg leading-none transition-colors flex-shrink-0 ${
            artist.favorite ? 'text-amber-400' : 'text-neutral-200 hover:text-amber-300'
          }`}
          title={artist.favorite ? 'Remove from favorites' : 'Add to favorites'}
        >
          {artist.favorite ? '\u2605' : '\u2606'}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-neutral-900 text-sm">{artist.name}</span>
            <span className="badge-genre">{artist.genre}</span>
            {artist.paused && <span className="badge-paused">Paused</span>}
          </div>
          <a
            href={artist.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-neutral-500 hover:underline truncate block mt-0.5 max-w-xs"
          >
            {artist.url}
          </a>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <button
            onClick={() => { setEditing(true); setEditUrl(artist.url); setEditGenre(artist.genre) }}
            className="text-xs text-neutral-400 hover:text-neutral-700 transition-colors"
            title="Edit artist"
          >
            Edit
          </button>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-neutral-500 hidden sm:inline">
              {artist.paused ? 'Paused' : 'Active'}
            </span>
            <Toggle
              checked={artist.paused}
              onChange={handlePause}
              disabled={togglingPause}
            />
          </div>

          {confirmDelete ? (
            <div className="flex items-center gap-1">
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="text-xs px-2 py-1 bg-neutral-900 text-white rounded hover:bg-neutral-700"
              >
                {deleting ? '\u2026' : 'Confirm'}
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="text-xs px-2 py-1 bg-neutral-100 text-neutral-600 rounded"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="btn-danger"
              title="Remove artist"
            >
              Remove
            </button>
          )}
        </div>
      </div>

      {/* Inline edit panel */}
      {editing && (
        <div className="mt-2 ml-8 p-3 bg-neutral-50 rounded-sm space-y-2">
          <div className="grid sm:grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">Genre</label>
              <select className="input text-sm" value={editGenre} onChange={e => setEditGenre(e.target.value)}>
                {GENRES.map(g => <option key={g}>{g}</option>)}
                {!GENRES.includes(editGenre) && <option key={editGenre}>{editGenre}</option>}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">Tour page URL</label>
              <input className="input text-sm" type="url" value={editUrl} onChange={e => setEditUrl(e.target.value)} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleSaveEdit} disabled={saving} className="btn-primary text-xs">
              {saving ? 'Saving\u2026' : 'Save'}
            </button>
            <button onClick={handleCancelEdit} className="btn-ghost text-xs">Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Group section ─────────────────────────────────────────────────────────────
function GenreGroup({ genre, artists, onTogglePause, onDelete, onUpdate }) {
  if (artists.length === 0) return null
  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-2 text-xs font-bold uppercase tracking-wide bg-neutral-50 text-neutral-600">
        {genre} ({artists.length})
      </div>
      {artists.map(a => (
        <ArtistRow key={a.name} artist={a} onTogglePause={onTogglePause} onDelete={onDelete} onUpdate={onUpdate} />
      ))}
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function ArtistsTab() {
  const [artists, setArtists] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [showAdd, setShowAdd] = useState(false)
  const [search,  setSearch]  = useState('')

  useEffect(() => {
    fetch('/api/artists')
      .then(r => r.json())
      .then(setArtists)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function handleTogglePause(name, val) {
    setArtists(prev => prev.map(a => a.name === name ? { ...a, paused: val } : a))
  }

  function handleDelete(name) {
    setArtists(prev => prev.filter(a => a.name !== name))
  }

  function handleUpdate(name, fields) {
    setArtists(prev => prev.map(a => a.name === name ? { ...a, ...fields } : a))
  }

  function handleAdd(artist) {
    setArtists(prev => [...prev, artist])
    setShowAdd(false)
  }

  if (loading) return <Spinner />
  if (error)   return <ErrBox message={error} />

  const q = search.toLowerCase()
  const filtered = q
    ? artists.filter(a => a.name.toLowerCase().includes(q) || a.genre.toLowerCase().includes(q))
    : artists

  // Group by known genres first, then collect any legacy genres
  const byGenre = {}
  for (const g of GENRES) byGenre[g] = []
  for (const a of filtered) {
    if (!byGenre[a.genre]) byGenre[a.genre] = []
    byGenre[a.genre].push(a)
  }
  const genreOrder = [...GENRES, ...Object.keys(byGenre).filter(g => !GENRES.includes(g))]

  const activeCount = artists.filter(a => !a.paused).length

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          className="input flex-1 min-w-48"
          placeholder="Search artists…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="text-sm text-neutral-500">
          {activeCount} active / {artists.length} total
        </div>
        <button className="btn-primary" onClick={() => setShowAdd(s => !s)}>
          {showAdd ? 'Cancel' : '+ Add Artist'}
        </button>
      </div>

      {/* Add form */}
      {showAdd && <AddArtistForm onAdd={handleAdd} onCancel={() => setShowAdd(false)} />}

      {/* Groups */}
      {genreOrder.map(g => (
        <GenreGroup
          key={g}
          genre={g}
          artists={byGenre[g] || []}
          onTogglePause={handleTogglePause}
          onDelete={handleDelete}
          onUpdate={handleUpdate}
        />
      ))}

      {filtered.length === 0 && (
        <p className="text-center text-neutral-400 py-8">No artists match your search.</p>
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
