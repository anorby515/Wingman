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
      <ScheduleSettings />
      <RunNow />
    </div>
  )
}
