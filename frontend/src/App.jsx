import { useState } from 'react'
import SummaryTab  from './components/SummaryTab.jsx'
import ArtistsTab  from './components/ArtistsTab.jsx'
import VenuesTab   from './components/VenuesTab.jsx'
import SettingsTab from './components/SettingsTab.jsx'

const TABS = [
  { id: 'summary',  label: 'Summary',  icon: '🎵' },
  { id: 'artists',  label: 'Artists',  icon: '🎤' },
  { id: 'venues',   label: 'Venues',   icon: '🏟' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
]

export default function App() {
  const [active, setActive] = useState('summary')

  return (
    <div className="min-h-screen flex flex-col bg-black">
      {/* ── Header ── */}
      <header className="bg-gunmetal text-white sticky top-0 z-20 shadow-lg">
        <div className="max-w-3xl mx-auto px-4 pt-4 pb-0">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">🎸</span>
            <div>
              <h1 className="text-[2.5rem] font-bold leading-tight">Wingman</h1>
              <p className="text-indigo-300 text-xs">Concert Tracker</p>
            </div>
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
        {active === 'summary'  && <SummaryTab />}
        {active === 'artists'  && <ArtistsTab />}
        {active === 'venues'   && <VenuesTab />}
        {active === 'settings' && <SettingsTab />}
      </main>
    </div>
  )
}
