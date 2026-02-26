import { useState, useEffect, useRef } from 'react'

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ title, children }) {
  return (
    <div className="card p-5 space-y-4">
      <h2 className="font-bold text-neutral-800 text-base border-b border-neutral-100 pb-2">{title}</h2>
      {children}
    </div>
  )
}

// ── Map Home (center city) ────────────────────────────────────────────────────
function MapHomeSettings({ config, onSave }) {
  const [centerCity, setCenterCity] = useState(config.center_city || '')
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
        body: JSON.stringify({
          center_city: centerCity.trim(),
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
    <Section title="Map Home">
      <form onSubmit={handleSave} className="space-y-4">
        {error && <p className="text-sm text-neutral-800">{error}</p>}

        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">Home City</label>
          <input
            className="input"
            value={centerCity}
            onChange={e => setCenterCity(e.target.value)}
            placeholder="Des Moines, IA"
          />
          <p className="text-xs text-neutral-400 mt-1">
            The map starts centered on this city. All artist shows across North America are displayed.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving\u2026' : 'Save'}
          </button>
          {saved && <span className="text-sm text-neutral-700 font-medium">Saved!</span>}
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

  if (loading) return <Section title="Schedule"><p className="text-neutral-400 text-sm">Loading…</p></Section>

  return (
    <Section title="Scheduled Run">
      {schedule?._note && (
        <div className="bg-neutral-50 border border-neutral-200 rounded p-3 text-xs text-neutral-600">
          {schedule._note}
        </div>
      )}
      {error && <p className="text-sm text-neutral-800">{error}</p>}

      {!editing ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-neutral-600 w-24">Next run:</span>
            <span className="text-sm text-neutral-800 font-medium">
              {schedule?.next_run
                ? new Date(schedule.next_run).toLocaleString()
                : <span className="text-neutral-400 italic">Unknown</span>
              }
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-neutral-600 w-24">Schedule:</span>
            <span className="text-sm text-neutral-800 font-mono">{schedule?.cron || '—'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-neutral-600 w-24">Enabled:</span>
            <span className="text-sm font-medium text-neutral-700">
              {schedule?.enabled === false ? 'Disabled' : 'Enabled'}
            </span>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button onClick={() => setEditing(true)} className="btn-ghost border border-neutral-200">
              Edit Schedule
            </button>
            {saved && <span className="text-sm text-neutral-700 font-medium">Saved!</span>}
          </div>
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
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
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Cron expression <span className="text-neutral-400 font-normal">(e.g. <code>0 9 * * 6</code> = Saturdays 9 AM)</span>
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
      <p className="text-sm text-neutral-600">
        Triggers <code className="bg-neutral-100 px-1 rounded text-xs">concert_weekly.py</code> immediately.
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
          <span className="text-neutral-700 font-medium text-sm">
            Completed successfully
          </span>
        )}
        {status === 'error' && (
          <span className="text-neutral-800 font-medium text-sm">
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
          className="bg-neutral-900 text-neutral-100 rounded p-3 text-xs font-mono max-h-56 overflow-y-auto space-y-0.5"
        >
          {log.map((line, i) => (
            <div key={i} className={
              line.includes('ERROR') || line.includes('⚠') ? 'text-neutral-400 font-medium' :
              line.includes('✅') ? 'text-neutral-300' :
              'text-neutral-400'
            }>{line || '\u00a0'}</div>
          ))}
          {status === 'running' && (
            <div className="text-neutral-500 animate-pulse">▌</div>
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
        {error && <p className="text-sm text-neutral-800">{error}</p>}
        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">
            Public Report URL
          </label>
          <input
            className="input"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://username.github.io/Wingman/"
          />
          <p className="text-xs text-neutral-400 mt-1">
            The "Live →" button in the header links here. Set this to your GitHub Pages URL.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          {saved && <span className="text-sm text-neutral-700 font-medium">Saved!</span>}
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost border border-neutral-200"
            >
              Open →
            </a>
          )}
        </div>
      </form>
    </Section>
  )
}

// ── Ticketmaster Integration ──────────────────────────────────────────────────
function TicketmasterSettings({ config, onSave }) {
  const [apiKey,  setApiKey]  = useState(config.ticketmaster_api_key || '')
  const [saving,  setSaving]  = useState(false)
  const [saved,   setSaved]   = useState(false)
  const [error,   setError]   = useState(null)

  const isConfigured = !!config.ticketmaster_api_key

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticketmaster_api_key: apiKey.trim() }),
      })
      if (!res.ok) throw new Error((await res.json()).detail)
      onSave({ ticketmaster_api_key: apiKey.trim() || null })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Ticketmaster Integration">
      <form onSubmit={handleSave} className="space-y-3">
        {error && <p className="text-sm text-neutral-800">{error}</p>}
        <p className="text-sm text-neutral-600">
          Powers the <strong>Coming Soon</strong> tab — shows announced concerts not yet on public sale,
          plus any presale windows (fan club, credit card, etc.).
        </p>
        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">
            Discovery API Key{' '}
            {isConfigured && (
              <span className="text-neutral-700 font-medium">(configured)</span>
            )}
          </label>
          <input
            className="input font-mono text-sm"
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder="Paste your TM Discovery API key"
          />
          <p className="text-xs text-neutral-400 mt-1">
            Free tier at{' '}
            <a
              href="https://developer.ticketmaster.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-neutral-500 underline hover:text-neutral-700"
            >
              developer.ticketmaster.com
            </a>
            {' '}— up to 5,000 calls/day. Results cached for 6 hours.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="btn-primary"
            disabled={saving || !apiKey.trim()}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          {saved && <span className="text-sm text-neutral-700 font-medium">Saved!</span>}
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
        <p className="text-sm text-neutral-600">
          Connect Spotify to sync followed artists, discover new bands from your listening history,
          and keep your Wingman and Spotify libraries in sync.
        </p>
        <div className="bg-neutral-50 border border-neutral-200 rounded p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <span className="font-medium">Spotify — Not connected</span>
          </div>
          <p className="text-xs text-neutral-400">
            Requires a Spotify Developer App. Set up at{' '}
            <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noopener noreferrer" className="text-neutral-500 underline hover:text-neutral-700">
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
      <div className="w-8 h-8 border-2 border-neutral-200 border-t-neutral-700 rounded-full animate-spin" />
    </div>
  )
  if (error) return <div className="card p-6 text-neutral-800 text-sm">{error}</div>

  return (
    <div className="space-y-5">
      <MapHomeSettings config={config} onSave={updated => setConfig(c => ({ ...c, ...updated }))} />
      <GitHubPagesSettings config={config} onSave={updated => setConfig(c => ({ ...c, ...updated }))} />
      <TicketmasterSettings config={config} onSave={updated => setConfig(c => ({ ...c, ...updated }))} />
      <SpotifySettings />
      <ScheduleSettings />
      <RunNow />
    </div>
  )
}
