import { useState, useEffect, useRef } from 'react'

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ title, children }) {
  return (
    <div className="card p-5 space-y-4">
      <h2 className="font-bold text-slate-800 text-base border-b border-slate-100 pb-2">{title}</h2>
      {children}
    </div>
  )
}

// ── Radius & Center City ──────────────────────────────────────────────────────
function LocationSettings({ config, onSave }) {
  const [centerCity,   setCenterCity]   = useState(config.center_city   || '')
  const [radiusMiles,  setRadiusMiles]  = useState(config.radius_miles  || 200)
  const [citiesInRange, setCitiesInRange] = useState((config.cities_in_range || []).join(', '))
  const [saving, setSaving] = useState(false)
  const [saved,  setSaved]  = useState(false)
  const [error,  setError]  = useState(null)

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const cities = citiesInRange.split(',').map(s => s.trim()).filter(Boolean)
      const res = await fetch('/api/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          center_city: centerCity.trim(),
          radius_miles: Number(radiusMiles),
          cities_in_range: cities,
        }),
      })
      if (!res.ok) throw new Error((await res.json()).detail)
      const updated = await res.json()
      onSave(updated.settings)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Search Area">
      <form onSubmit={handleSave} className="space-y-4">
        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Center City</label>
            <input
              className="input"
              value={centerCity}
              onChange={e => setCenterCity(e.target.value)}
              placeholder="Des Moines, IA"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Search Radius: <span className="font-bold text-indigo-600">{radiusMiles} miles</span>
            </label>
            <input
              type="range"
              min={25} max={600} step={25}
              value={radiusMiles}
              onChange={e => setRadiusMiles(Number(e.target.value))}
              className="w-full accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-0.5">
              <span>25 mi</span><span>600 mi</span>
            </div>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Cities in Range <span className="text-slate-400 font-normal">(comma-separated)</span>
          </label>
          <textarea
            className="input resize-none"
            rows={3}
            value={citiesInRange}
            onChange={e => setCitiesInRange(e.target.value)}
            placeholder="Des Moines, Ames, Iowa City…"
          />
          <p className="text-xs text-slate-400 mt-1">
            Used by concert_weekly.py to filter which cities are "in range".
            Update this list when you change the center or radius.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save Location Settings'}
          </button>
          {saved && <span className="text-sm text-emerald-600 font-medium">Saved!</span>}
        </div>
      </form>
    </Section>
  )
}

// ── Schedule ──────────────────────────────────────────────────────────────────
function ScheduleSettings() {
  const [schedule, setSchedule] = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [editing,  setEditing]  = useState(false)
  const [nextRun,  setNextRun]  = useState('')
  const [cron,     setCron]     = useState('')
  const [saving,   setSaving]   = useState(false)
  const [error,    setError]    = useState(null)
  const [saved,    setSaved]    = useState(false)

  useEffect(() => {
    fetch('/api/schedule')
      .then(r => r.json())
      .then(data => {
        setSchedule(data)
        setNextRun(data.next_run || '')
        setCron(data.cron || '')
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/schedule', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ next_run: nextRun || null, cron: cron || null }),
      })
      const data = await res.json()
      if (!res.ok && !data._warning) throw new Error(data.detail)
      setSchedule(data)
      setEditing(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
      if (data._warning) setError(`Note: ${data._warning}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Section title="Schedule"><p className="text-slate-400 text-sm">Loading…</p></Section>

  return (
    <Section title="Scheduled Run">
      {schedule?._note && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
          {schedule._note}
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!editing ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-600 w-24">Next run:</span>
            <span className="text-sm text-slate-800 font-medium">
              {schedule?.next_run
                ? new Date(schedule.next_run).toLocaleString()
                : <span className="text-slate-400 italic">Unknown</span>
              }
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-600 w-24">Schedule:</span>
            <span className="text-sm text-slate-800 font-mono">{schedule?.cron || '—'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-600 w-24">Enabled:</span>
            <span className={`text-sm font-medium ${schedule?.enabled ? 'text-emerald-600' : 'text-amber-600'}`}>
              {schedule?.enabled === false ? 'Disabled' : 'Enabled'}
            </span>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button onClick={() => setEditing(true)} className="btn-ghost border border-slate-200">
              Edit Schedule
            </button>
            {saved && <span className="text-sm text-emerald-600 font-medium">Saved!</span>}
          </div>
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Next run (datetime-local)
            </label>
            <input
              type="datetime-local"
              className="input"
              value={nextRun ? nextRun.slice(0, 16) : ''}
              onChange={e => setNextRun(e.target.value ? new Date(e.target.value).toISOString() : '')}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Cron expression <span className="text-slate-400 font-normal">(e.g. <code>0 9 * * 6</code> = Saturdays 9 AM)</span>
            </label>
            <input
              className="input font-mono"
              placeholder="0 9 * * 6"
              value={cron}
              onChange={e => setCron(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
            <button type="button" className="btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </form>
      )}
    </Section>
  )
}

// ── Run Now ───────────────────────────────────────────────────────────────────
function RunNow() {
  const [status, setStatus] = useState(null)  // null | 'running' | 'done' | 'error'
  const [log,    setLog]    = useState([])
  const [returncode, setReturncode] = useState(null)
  const [showLog, setShowLog] = useState(false)
  const pollRef = useRef(null)
  const logRef  = useRef(null)

  useEffect(() => () => clearInterval(pollRef.current), [])

  async function startRun() {
    setStatus('running')
    setLog([])
    setReturncode(null)
    setShowLog(true)
    try {
      const res = await fetch('/api/run', { method: 'POST' })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail)
      }
    } catch (e) {
      setStatus('error')
      setLog([`Error: ${e.message}`])
      return
    }

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch('/api/run/status')
        const data = await res.json()
        setLog(data.log || [])
        if (!data.running) {
          clearInterval(pollRef.current)
          setReturncode(data.returncode)
          setStatus(data.returncode === 0 ? 'done' : 'error')
          // Scroll log to bottom
          if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
        }
      } catch {
        clearInterval(pollRef.current)
        setStatus('error')
      }
    }, 1500)
  }

  return (
    <Section title="Manual Run">
      <p className="text-sm text-slate-600">
        Triggers <code className="bg-slate-100 px-1 rounded text-xs">concert_weekly.py</code> immediately.
        This scrapes all active artists and venues, diffs against last week's state, and generates a new PDF.
        Scraping takes several minutes.
      </p>

      <div className="flex items-center gap-4 flex-wrap">
        <button
          className="btn-primary"
          onClick={startRun}
          disabled={status === 'running'}
        >
          {status === 'running' ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Running…
            </span>
          ) : 'Run Now'}
        </button>

        {status === 'done' && (
          <span className="text-emerald-600 font-medium text-sm">
            Completed successfully
          </span>
        )}
        {status === 'error' && (
          <span className="text-red-600 font-medium text-sm">
            Finished with errors (code {returncode})
          </span>
        )}

        {log.length > 0 && (
          <button onClick={() => setShowLog(s => !s)} className="btn-ghost text-xs">
            {showLog ? 'Hide' : 'Show'} log ({log.length} lines)
          </button>
        )}
      </div>

      {showLog && log.length > 0 && (
        <div
          ref={logRef}
          className="bg-slate-900 text-slate-100 rounded-lg p-3 text-xs font-mono max-h-56 overflow-y-auto space-y-0.5"
        >
          {log.map((line, i) => (
            <div key={i} className={
              line.includes('ERROR') || line.includes('⚠') ? 'text-red-400' :
              line.includes('✅') ? 'text-emerald-400' :
              'text-slate-300'
            }>{line || '\u00a0'}</div>
          ))}
          {status === 'running' && (
            <div className="text-indigo-400 animate-pulse">▌</div>
          )}
        </div>
      )}
    </Section>
  )
}

// ── GitHub Pages URL ─────────────────────────────────────────────────────────
function GitHubPagesSettings({ config, onSave }) {
  const [url, setUrl] = useState(config.github_pages_url || '')
  const [saving, setSaving] = useState(false)
  const [saved,  setSaved]  = useState(false)
  const [error,  setError]  = useState(null)

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ github_pages_url: url.trim() }),
      })
      if (!res.ok) throw new Error((await res.json()).detail)
      onSave({ github_pages_url: url.trim() })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="GitHub Pages">
      <form onSubmit={handleSave} className="space-y-3">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            Public Report URL
          </label>
          <input
            className="input"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://username.github.io/Wingman/"
          />
          <p className="text-xs text-slate-400 mt-1">
            The "Public Report" button in the header links here. Set this to your GitHub Pages URL.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          {saved && <span className="text-sm text-emerald-600 font-medium">Saved!</span>}
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost border border-slate-200 flex items-center gap-1"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              Open
            </a>
          )}
        </div>
      </form>
    </Section>
  )
}

// ── Spotify Connect ──────────────────────────────────────────────────────────
function SpotifySettings() {
  return (
    <Section title="Spotify Integration">
      <div className="space-y-3">
        <p className="text-sm text-slate-600">
          Connect Spotify to sync followed artists, discover new bands from your listening history,
          and keep your Wingman and Spotify libraries in sync.
        </p>
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <svg className="w-5 h-5 text-[#1DB954]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
            <span className="font-medium">Not connected</span>
          </div>
          <p className="text-xs text-slate-400">
            Requires a Spotify Developer App. Set up at{' '}
            <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:underline">
              developer.spotify.com
            </a>, then configure your Client ID below.
          </p>
        </div>
        <button className="btn-primary opacity-50 cursor-not-allowed" disabled>
          Connect Spotify (Coming Soon)
        </button>
      </div>
    </Section>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function SettingsTab() {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    fetch('/api/config')
      .then(r => r.json())
      .then(setConfig)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex justify-center py-16">
      <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
    </div>
  )
  if (error) return <div className="card p-6 text-red-600 text-sm">{error}</div>

  return (
    <div className="space-y-5">
      <LocationSettings config={config} onSave={updated => setConfig(c => ({ ...c, ...updated }))} />
      <GitHubPagesSettings config={config} onSave={updated => setConfig(c => ({ ...c, ...updated }))} />
      <SpotifySettings />
      <ScheduleSettings />
      <RunNow />
    </div>
  )
}
