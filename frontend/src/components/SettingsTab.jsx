import { useState, useEffect } from 'react'

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
          Required for fetching concert data from Ticketmaster. Click <strong>Refresh</strong> in the
          header to pull the latest shows for all tracked artists, venues, and festivals.
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

// ── Spotify Integration ───────────────────────────────────────────────────────
function SpotifySettings({ config, onSave }) {
  const [clientId,     setClientId]     = useState(config.spotify_client_id || '')
  const [clientSecret, setClientSecret] = useState(config.spotify_client_secret || '')
  const [saving,       setSaving]       = useState(false)
  const [saved,        setSaved]        = useState(false)
  const [error,        setError]        = useState(null)
  const [status,       setStatus]       = useState(null) // {connected, display_name}

  useEffect(() => {
    fetch('/api/spotify/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {})
  }, [])

  // Handle redirect back from Spotify OAuth
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('spotify_connected')) {
      setStatus({ connected: true })
      // Re-fetch to get display name
      fetch('/api/spotify/status').then(r => r.json()).then(setStatus).catch(() => {})
      window.history.replaceState({}, '', window.location.pathname)
    }
    if (params.get('spotify_error')) {
      setError('Spotify auth failed: ' + params.get('spotify_error'))
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spotify_client_id: clientId.trim(),
          spotify_client_secret: clientSecret.trim(),
        }),
      })
      if (!res.ok) throw new Error((await res.json()).detail)
      onSave({ spotify_client_id: clientId.trim() || null, spotify_client_secret: clientSecret.trim() || null })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDisconnect() {
    await fetch('/api/spotify/disconnect', { method: 'DELETE' })
    setStatus({ connected: false, display_name: null })
  }

  const credentialsEntered = clientId.trim() && clientSecret.trim()
  const isConfigured = !!(config.spotify_client_id && config.spotify_client_secret)

  return (
    <Section title="Spotify">
      <form onSubmit={handleSave} className="space-y-3">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <p className="text-sm text-neutral-600">
          Used for Spotify sync — matching your followed artists with Wingman and discovering new ones from your listening history.
        </p>

        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">
            Client ID{isConfigured && <span className="text-neutral-700 font-medium"> (configured)</span>}
          </label>
          <input
            className="input font-mono text-sm"
            value={clientId}
            onChange={e => setClientId(e.target.value)}
            placeholder="Paste your Spotify Client ID"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-neutral-600 mb-1">
            Client Secret{isConfigured && <span className="text-neutral-700 font-medium"> (configured)</span>}
          </label>
          <input
            className="input font-mono text-sm"
            type="password"
            value={clientSecret}
            onChange={e => setClientSecret(e.target.value)}
            placeholder="Paste your Spotify Client Secret"
          />
          <p className="text-xs text-neutral-400 mt-1">
            Get these from{' '}
            <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noopener noreferrer"
               className="text-neutral-500 underline hover:text-neutral-700">
              developer.spotify.com/dashboard
            </a>
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button type="submit" className="btn-primary" disabled={saving || !credentialsEntered}>
            {saving ? 'Saving…' : 'Save'}
          </button>
          {saved && <span className="text-sm text-neutral-700 font-medium">Saved!</span>}
        </div>
      </form>

      {/* Connection status + Connect button */}
      <div className="pt-3 border-t border-neutral-100 mt-3">
        {status?.connected ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
              <span className="text-sm text-neutral-700 font-medium">
                Connected{status.display_name ? ` as ${status.display_name}` : ''}
              </span>
            </div>
            <button
              onClick={handleDisconnect}
              className="text-xs text-neutral-400 hover:text-neutral-600 underline"
            >
              Disconnect
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <a
              href={isConfigured ? '/auth/spotify' : undefined}
              target="_blank"
              rel="noopener noreferrer"
              className={`btn-primary ${!isConfigured ? 'opacity-50 pointer-events-none cursor-not-allowed' : ''}`}
              onClick={!isConfigured ? e => e.preventDefault() : undefined}
            >
              Connect Spotify →
            </a>
            {!isConfigured && (
              <span className="text-xs text-neutral-400">Save credentials first</span>
            )}
          </div>
        )}
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
      <SpotifySettings config={config} onSave={updated => setConfig(c => ({ ...c, ...updated }))} />
    </div>
  )
}
