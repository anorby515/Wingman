import { useState, useEffect } from 'react'
import ArtistsSummaryTab   from './components/ArtistsSummaryTab.jsx'
import ComingSoonTab       from './components/ComingSoonTab.jsx'
import ConfigureTab        from './components/ConfigureTab.jsx'
import SettingsTab         from './components/SettingsTab.jsx'

const DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

const ALL_TABS = [
  { id: 'concerts',    label: 'Concerts & Festivals' },
  { id: 'on-sale-soon', label: 'On Sale Soon'        },
  { id: 'configure',   label: 'Configure'            },
  { id: 'settings',    label: 'Settings'             },
]

const TABS = DEMO
  ? ALL_TABS.filter(t => ['concerts', 'on-sale-soon'].includes(t.id))
  : ALL_TABS.filter(t => ['configure', 'settings'].includes(t.id))

export default function App() {
  const [active, setActive] = useState(DEMO ? 'concerts' : 'configure')
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
    <div className="min-h-screen flex flex-col">
      {/* ── Header ── */}
      <header className="sticky top-0 z-[1000] header-titanium">
        <div className="max-w-3xl mx-auto px-4 pt-4 pb-0">
          <div className="relative flex items-center justify-center mb-4 pt-2">
            <h1 className="text-5xl font-bold tracking-tight text-neutral-900">WINGMAN</h1>

            <div className="absolute right-0 flex items-center gap-2 flex-shrink-0">
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
        {active === 'concerts'      && <ArtistsSummaryTab />}
        {active === 'on-sale-soon'  && <ComingSoonTab />}
        {active === 'configure'     && <ConfigureTab />}
        {active === 'settings'      && <SettingsTab />}
      </main>
    </div>
  )
}
