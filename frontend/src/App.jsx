import { useState, useEffect, useCallback } from 'react'
import ArtistsSummaryTab   from './components/ArtistsSummaryTab.jsx'
import FestivalsSummaryTab from './components/FestivalsSummaryTab.jsx'
import VenuesSummaryTab    from './components/VenuesSummaryTab.jsx'
import ComingSoonTab       from './components/ComingSoonTab.jsx'
import ConfigureTab        from './components/ConfigureTab.jsx'
import SettingsTab         from './components/SettingsTab.jsx'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

const ALL_TABS = [
  { id: 'coming-soon', label: 'Coming Soon', icon: '🎟' },
  { id: 'artists',     label: 'Artists',     icon: '🎤' },
  { id: 'festivals',   label: 'Festivals',   icon: '🎪' },
  { id: 'venues',      label: 'Venues',      icon: '🏟' },
  { id: 'configure',   label: 'Configure',   icon: '🔧' },
  { id: 'settings',    label: 'Settings',    icon: '⚙️' },
]

const TABS = DEMO
  ? ALL_TABS.filter(t => ['coming-soon', 'artists', 'festivals', 'venues'].includes(t.id))
  : ALL_TABS

function timeAgo(isoStr) {
  if (!isoStr) return null
  try {
    const diff = Date.now() - new Date(isoStr).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    const days = Math.floor(hrs / 24)
    return `${days}d ago`
  } catch { return null }
}

export default function App() {
  const [active, setActive] = useState('coming-soon')
  const [pagesUrl, setPagesUrl] = useState('')
  const [lastRefreshed, setLastRefreshed] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState(null)
  const [refreshVersion, setRefreshVersion] = useState(0)

  useEffect(() => {
    if (!DEMO) {
      fetch('/api/config')
        .then(r => r.json())
        .then(cfg => setPagesUrl(cfg.github_pages_url || ''))
        .catch(() => {})

      fetch('/api/shows')
        .then(r => r.json())
        .then(data => setLastRefreshed(data.last_refreshed))
        .catch(() => {})
    }
  }, [])

  const handleRefresh = useCallback(async () => {
    if (refreshing) return
    setRefreshing(true)
    setRefreshError(null)
    try {
      const res = await fetch('/api/refresh', { method: 'POST' })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Refresh failed')
      }

      // Poll for completion
      let done = false
      while (!done) {
        await new Promise(r => setTimeout(r, 1500))
        const status = await fetch('/api/refresh/status').then(r => r.json())
        if (!status.running) {
          done = true
          if (status.error) throw new Error(status.error)
        }
      }

      // Refresh succeeded — update last_refreshed and bump version to re-render tabs
      const showsData = await fetch('/api/shows').then(r => r.json())
      setLastRefreshed(showsData.last_refreshed)
      setRefreshVersion(v => v + 1)

      // Poll for background geocoding progress (map pins appear progressively)
      pollGeocodeProgress()
    } catch (e) {
      setRefreshError(e.message)
    } finally {
      setRefreshing(false)
    }
  }, [refreshing])

  const pollGeocodeProgress = useCallback(() => {
    let lastCached = 0
    const poll = async () => {
      try {
        const gp = await fetch('/api/geocode/progress').then(r => r.json())
        // If new locations were geocoded, bump version so map re-renders
        if (gp.total_cached > lastCached && lastCached > 0) {
          setRefreshVersion(v => v + 1)
        }
        lastCached = gp.total_cached
        if (gp.running) {
          setTimeout(poll, 2000)
        } else if (gp.total_cached > 0) {
          // Final bump to pick up any remaining geocodes
          setRefreshVersion(v => v + 1)
        }
      } catch {
        // Stop polling on error
      }
    }
    poll()
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-black">
      {/* ── Header ── */}
      <header className="bg-gunmetal text-white sticky top-0 z-20 shadow-lg">
        <div className="max-w-3xl mx-auto px-4 pt-4 pb-0">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">🎸</span>
            <div className="flex-1">
              <h1 className="text-[2.5rem] font-bold leading-tight">Wingman</h1>
              <p className="text-indigo-300 text-xs">Concert Tracker</p>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              {/* Last refreshed */}
              {!DEMO && lastRefreshed && (
                <span className="text-xs text-indigo-300" title={lastRefreshed}>
                  Updated {timeAgo(lastRefreshed)}
                </span>
              )}

              {/* Refresh Data button (local only) */}
              {!DEMO && (
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-400 disabled:bg-amber-600 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition-colors text-slate-900"
                  title="Fetch latest data from Ticketmaster"
                >
                  {refreshing ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-slate-700 border-t-transparent rounded-full animate-spin" />
                      Refreshing...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Refresh Data
                    </>
                  )}
                </button>
              )}

              {/* Public Report link */}
              {!DEMO && pagesUrl && (
                <a
                  href={pagesUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium transition-colors"
                  title="View public report on GitHub Pages"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  Public Report
                </a>
              )}
            </div>
          </div>

          {/* Refresh error */}
          {refreshError && (
            <div className="mb-2 px-3 py-1.5 bg-red-500/20 rounded text-xs text-red-200">
              Refresh failed: {refreshError}
            </div>
          )}

          {/* ── Tab bar ── */}
          <nav className="flex -mb-px" role="tablist">
            {TABS.map(tab => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={active === tab.id}
                onClick={() => setActive(tab.id)}
                className={[
                  'flex-1 py-3 text-sm font-medium transition-colors border-b-2',
                  active === tab.id
                    ? 'border-amber-400 text-white'
                    : 'border-transparent text-indigo-300 hover:text-white hover:border-indigo-400',
                ].join(' ')}
              >
                <span className="hidden sm:inline mr-1">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-6">
        {active === 'coming-soon' && <ComingSoonTab key={refreshVersion} />}
        {active === 'artists'     && <ArtistsSummaryTab key={refreshVersion} />}
        {active === 'festivals'   && <FestivalsSummaryTab key={refreshVersion} />}
        {active === 'venues'      && <VenuesSummaryTab key={refreshVersion} />}
        {active === 'configure'   && <ConfigureTab />}
        {active === 'settings'    && <SettingsTab />}
      </main>
    </div>
  )
}
