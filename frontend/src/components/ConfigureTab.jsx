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

// ── Festival row ──────────────────────────────────────────────────────────────
function FestivalRow({ festival, onTogglePause, onDelete }) {
  const [togglingPause, setTogglingPause] = useState(false)
  const [deleting,      setDeleting]      = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

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

  return (
    <div className={`flex items-center gap-3 px-4 py-3 border-b border-neutral-50 last:border-0 transition-opacity ${festival.paused ? 'opacity-60' : ''}`}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-neutral-900 text-sm">{festival.name}</span>
          {festival.paused && <span className="badge-paused">Paused</span>}
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
  )
}

// ── Festivals section ─────────────────────────────────────────────────────────
function FestivalsSection() {
  const [festivals, setFestivals] = useState([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [showAdd,   setShowAdd]   = useState(false)
  const [scraping,  setScraping]  = useState(false)
  const [scrapeMsg, setScrapeMsg] = useState(null)

  useEffect(() => {
    fetch('/api/festivals')
      .then(r => r.json())
      .then(setFestivals)
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

  async function handleRefreshLineups() {
    setScraping(true)
    setScrapeMsg(null)
    try {
      const res = await fetch('/api/festival-lineups/refresh', { method: 'POST' })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Scraper failed')
      }
      const data = await res.json()
      const count = Object.keys(data.lineups || {}).length
      setScrapeMsg(`Updated lineups for ${count} festival${count !== 1 ? 's' : ''}`)
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
          onClick={handleRefreshLineups}
          disabled={scraping}
        >
          {scraping ? 'Scraping lineups…' : 'Refresh Lineups'}
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
            <FestivalRow key={f.name} festival={f} onTogglePause={handleTogglePause} onDelete={handleDelete} />
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
