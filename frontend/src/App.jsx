import { useState, useEffect } from 'react'
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

export default function App() {
  const [active, setActive] = useState('coming-soon')
  const [pagesUrl, setPagesUrl] = useState('')

  useEffect(() => {
    if (!DEMO) {
      fetch('/api/config')
        .then(r => r.json())
        .then(cfg => setPagesUrl(cfg.github_pages_url || ''))
        .catch(() => {})
    }
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
        {active === 'coming-soon' && <ComingSoonTab />}
        {active === 'artists'     && <ArtistsSummaryTab />}
        {active === 'festivals'   && <FestivalsSummaryTab />}
        {active === 'venues'      && <VenuesSummaryTab />}
        {active === 'configure'   && <ConfigureTab />}
        {active === 'settings'    && <SettingsTab />}
      </main>
    </div>
  )
}
