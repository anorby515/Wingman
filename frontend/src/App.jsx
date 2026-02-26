import { useState, useEffect, useCallback } from 'react'
import ArtistsSummaryTab   from './components/ArtistsSummaryTab.jsx'
import FestivalsSummaryTab from './components/FestivalsSummaryTab.jsx'
import VenuesSummaryTab    from './components/VenuesSummaryTab.jsx'
import ComingSoonTab       from './components/ComingSoonTab.jsx'
import ConfigureTab        from './components/ConfigureTab.jsx'
import SettingsTab         from './components/SettingsTab.jsx'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

const ALL_TABS = [
  { id: 'coming-soon', label: 'Coming Soon' },
  { id: 'artists',     label: 'Artists'     },
  { id: 'festivals',   label: 'Festivals'   },
  { id: 'venues',      label: 'Venues'      },
  { id: 'configure',   label: 'Configure'   },
  { id: 'settings',    label: 'Settings'    },
]

const TABS = DEMO
  ? ALL_TABS.filter(t => ['coming-soon', 'artists', 'festivals', 'venues'].includes(t.id))
  : ALL_TABS.filter(t => ['configure', 'settings'].includes(t.id))

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
  const [active, setActive] = useState(DEMO ? 'coming-soon' : 'configure')
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
        if (gp.total_cached > lastCached && lastCached > 0) {
          setRefreshVersion(v => v + 1)
        }
        lastCached = gp.total_cached
        if (gp.running) {
          setTimeout(poll, 2000)
        } else if (gp.total_cached > 0) {
          setRefreshVersion(v => v + 1)
        }
      } catch {
        // Stop polling on error
      }
    }
    poll()
  }, [])

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ── */}
      <header className="sticky top-0 z-[1000] header-titanium">
        <div className="max-w-3xl mx-auto px-4 pt-4 pb-0">
          <div className="relative flex items-center justify-center mb-4 pt-2">
            <h1 className="text-5xl font-bold tracking-tight text-neutral-900">WINGMAN</h1>

            <div className="absolute right-0 flex items-center gap-2 flex-shrink-0">
              {/* Last refreshed */}
              {!DEMO && lastRefreshed && (
                <span className="text-xs text-neutral-400" title={lastRefreshed}>
                  {timeAgo(lastRefreshed)}
                </span>
              )}

              {/* Refresh button (local only) */}
              {!DEMO && (
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="px-3 py-1 bg-neutral-900 text-white text-xs font-medium hover:bg-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  title="Fetch latest data from Ticketmaster"
                >
                  {refreshing ? (
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 border border-neutral-500 border-t-white rounded-full animate-spin" />
                      Refreshing
                    </span>
                  ) : 'Refresh'}
                </button>
              )}

              {/* Live link */}
              {!DEMO && pagesUrl && (
                <a
                  href={pagesUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1 border border-neutral-300 text-neutral-700 text-xs font-medium hover:bg-neutral-50 transition-colors"
                  title="View public report on GitHub Pages"
                >
                  Live →
                </a>
              )}
            </div>
          </div>

          {/* Refresh error */}
          {refreshError && (
            <div className="mb-2 px-3 py-1.5 border border-neutral-200 text-xs text-neutral-600">
              Refresh failed: {refreshError}
            </div>
          )}

          <hr className="border-neutral-200" />

          {/* ── Tab bar ── */}
          <nav className="flex -mb-px mt-0" role="tablist">
            {TABS.map(tab => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={active === tab.id}
                onClick={() => setActive(tab.id)}
                className={[
                  'flex-1 py-2.5 text-sm text-neutral-900 transition-colors border-b-2',
                  active === tab.id
                    ? 'border-neutral-900 font-semibold'
                    : 'border-transparent',
                ].join(' ')}
              >
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
