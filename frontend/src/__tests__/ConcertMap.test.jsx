import { describe, it, expect, vi, beforeAll } from 'vitest'

// Mock leaflet before importing ConcertMap — Leaflet's L.Icon constructor
// requires DOM APIs (Image, document) that jsdom doesn't fully support.
vi.mock('leaflet', () => {
  class MockIcon {
    constructor(opts) {
      this._opts = opts
      this._mockUrl = opts.iconUrl
    }
  }
  return {
    default: {
      Icon: Object.assign(MockIcon, {
        Default: { prototype: { _getIconUrl: null }, mergeOptions: vi.fn() },
      }),
    },
    Icon: MockIcon,
  }
})

// Mock react-leaflet (not needed for pure function tests, but prevents import errors)
vi.mock('react-leaflet', () => ({
  MapContainer: vi.fn(({ children }) => children),
  TileLayer: vi.fn(() => null),
  Marker: vi.fn(({ children }) => children),
  Tooltip: vi.fn(({ children }) => children),
  useMapEvents: vi.fn(),
}))

// Mock leaflet CSS import
vi.mock('leaflet/dist/leaflet.css', () => ({}))

// Now import the module under test
import {
  getArtistPinIcon,
  NEW_ICON,
  DEFAULT_ICON,
  SOLD_OUT_ICON,
  COMING_SOON_ICON,
  FAVORITE_ICON,
  TOOLTIP_STYLE,
  TOOLTIP_STYLE_NARROW,
} from '../components/ConcertMap.jsx'

// ── Icon identity helpers ────────────────────────────────────────────────────
// We identify icons by their marker image URL (set in the mock constructor)
function iconColor(icon) {
  const url = icon._mockUrl || ''
  if (url.includes('green')) return 'green'
  if (url.includes('red')) return 'red'
  if (url.includes('blue')) return 'blue'
  if (url.includes('gold')) return 'gold'
  if (url.includes('violet')) return 'violet'
  return 'unknown'
}

// ── Pin icon priority tests ──────────────────────────────────────────────────
describe('getArtistPinIcon', () => {
  // Verify icon colors are set up correctly
  it('NEW_ICON is green', () => {
    expect(iconColor(NEW_ICON)).toBe('green')
  })
  it('DEFAULT_ICON is green', () => {
    expect(iconColor(DEFAULT_ICON)).toBe('green')
  })
  it('SOLD_OUT_ICON is red', () => {
    expect(iconColor(SOLD_OUT_ICON)).toBe('red')
  })
  it('COMING_SOON_ICON is blue', () => {
    expect(iconColor(COMING_SOON_ICON)).toBe('blue')
  })
  it('FAVORITE_ICON is gold', () => {
    expect(iconColor(FAVORITE_ICON)).toBe('gold')
  })

  // ── Basic single-show cases ──
  it('returns DEFAULT_ICON for a plain on-sale show', () => {
    const shows = [{ status: 'on_sale' }]
    expect(getArtistPinIcon(shows)).toBe(DEFAULT_ICON)
  })

  it('returns NEW_ICON when a show is new', () => {
    const shows = [{ is_new: true, status: 'on_sale' }]
    expect(getArtistPinIcon(shows)).toBe(NEW_ICON)
  })

  it('returns SOLD_OUT_ICON when all shows are sold out', () => {
    const shows = [
      { status: 'sold_out' },
      { status: 'sold_out' },
    ]
    expect(getArtistPinIcon(shows)).toBe(SOLD_OUT_ICON)
  })

  it('returns COMING_SOON_ICON for a coming-soon show (source=tm)', () => {
    const shows = [{ source: 'tm' }]
    expect(getArtistPinIcon(shows)).toBe(COMING_SOON_ICON)
  })

  it('returns FAVORITE_ICON for a favorite on-sale show', () => {
    const shows = [{ _isFavorite: true, status: 'on_sale' }]
    expect(getArtistPinIcon(shows)).toBe(FAVORITE_ICON)
  })

  // ── KEY REGRESSION TESTS: Favorite + Coming Soon / On Sale combinations ──
  it('Favorite + Coming Soon → COMING_SOON_ICON (blue, not gold)', () => {
    // A single show that is both favorite and coming soon
    const shows = [{ _isFavorite: true, source: 'tm' }]
    expect(getArtistPinIcon(shows)).toBe(COMING_SOON_ICON)
  })

  it('Favorite + On Sale → FAVORITE_ICON (gold)', () => {
    // A single show that is favorite and on sale (no source=tm)
    const shows = [{ _isFavorite: true, status: 'on_sale' }]
    expect(getArtistPinIcon(shows)).toBe(FAVORITE_ICON)
  })

  // ── Multi-show combinations at same location ──
  it('mixed coming-soon and on-sale shows → COMING_SOON_ICON (any coming-soon wins)', () => {
    const shows = [
      { source: 'tm' },              // coming soon
      { status: 'on_sale' },         // on sale
    ]
    expect(getArtistPinIcon(shows)).toBe(COMING_SOON_ICON)
  })

  it('mixed coming-soon + on-sale favorites → COMING_SOON_ICON (coming soon beats favorite)', () => {
    const shows = [
      { _isFavorite: true, source: 'tm' },   // favorite + coming soon
      { _isFavorite: true, status: 'on_sale' }, // favorite + on sale
    ]
    expect(getArtistPinIcon(shows)).toBe(COMING_SOON_ICON)
  })

  it('all on-sale with some favorites → FAVORITE_ICON', () => {
    const shows = [
      { _isFavorite: true, status: 'on_sale' },
      { status: 'on_sale' },
    ]
    expect(getArtistPinIcon(shows)).toBe(FAVORITE_ICON)
  })

  it('coming soon overrides new', () => {
    const shows = [
      { is_new: true, source: 'tm' },
    ]
    expect(getArtistPinIcon(shows)).toBe(COMING_SOON_ICON)
  })

  it('coming soon overrides everything (new + favorite + sold out)', () => {
    const shows = [
      { is_new: true, _isFavorite: true, source: 'tm', status: 'sold_out' },
    ]
    expect(getArtistPinIcon(shows)).toBe(COMING_SOON_ICON)
  })

  it('new overrides favorite', () => {
    const shows = [
      { is_new: true, _isFavorite: true, status: 'on_sale' },
    ]
    expect(getArtistPinIcon(shows)).toBe(NEW_ICON)
  })

  it('favorite overrides sold out', () => {
    const shows = [
      { _isFavorite: true, status: 'sold_out' },
    ]
    expect(getArtistPinIcon(shows)).toBe(FAVORITE_ICON)
  })

  it('sold out does not apply if any show is not sold out', () => {
    const shows = [
      { status: 'sold_out' },
      { status: 'on_sale' },
    ]
    // allSoldOut = false, no coming soon, no new, no favorite → DEFAULT
    expect(getArtistPinIcon(shows)).toBe(DEFAULT_ICON)
  })

  it('new overrides sold out', () => {
    const shows = [
      { is_new: true, status: 'sold_out' },
      { status: 'sold_out' },
    ]
    expect(getArtistPinIcon(shows)).toBe(NEW_ICON)
  })
})

// ── Tooltip style tests ──────────────────────────────────────────────────────
describe('Tooltip styles (prevent overflow regression)', () => {
  it('TOOLTIP_STYLE has whiteSpace: normal', () => {
    expect(TOOLTIP_STYLE.whiteSpace).toBe('normal')
  })

  it('TOOLTIP_STYLE has wordWrap: break-word', () => {
    expect(TOOLTIP_STYLE.wordWrap).toBe('break-word')
  })

  it('TOOLTIP_STYLE has a maxWidth constraint', () => {
    expect(TOOLTIP_STYLE.maxWidth).toBeGreaterThan(0)
    expect(TOOLTIP_STYLE.maxWidth).toBeLessThanOrEqual(400)
  })

  it('TOOLTIP_STYLE_NARROW has whiteSpace: normal', () => {
    expect(TOOLTIP_STYLE_NARROW.whiteSpace).toBe('normal')
  })

  it('TOOLTIP_STYLE_NARROW has wordWrap: break-word', () => {
    expect(TOOLTIP_STYLE_NARROW.wordWrap).toBe('break-word')
  })

  it('TOOLTIP_STYLE_NARROW has a maxWidth constraint', () => {
    expect(TOOLTIP_STYLE_NARROW.maxWidth).toBeGreaterThan(0)
    expect(TOOLTIP_STYLE_NARROW.maxWidth).toBeLessThanOrEqual(400)
  })
})

// ── CSS regression guard ─────────────────────────────────────────────────────
// Verify the CSS file contains the !important rules that prevent Leaflet's
// white-space:nowrap from overriding our tooltip fix.
describe('index.css tooltip rules', () => {
  let cssContent

  beforeAll(async () => {
    const fs = await import('fs')
    const path = await import('path')
    // Resolve relative to this test file's directory: __tests__/ → src/ → index.css
    const cssPath = path.resolve(__dirname, '..', 'index.css')
    cssContent = fs.readFileSync(cssPath, 'utf-8')
  })

  it('has .leaflet-tooltip rule with white-space: normal !important', () => {
    expect(cssContent).toMatch(/\.leaflet-tooltip\s*\{[^}]*white-space:\s*normal\s*!important/s)
  })

  it('has .leaflet-tooltip rule with max-width !important', () => {
    expect(cssContent).toMatch(/\.leaflet-tooltip\s*\{[^}]*max-width:\s*\d+px\s*!important/s)
  })

  it('has .leaflet-tooltip rule with word-wrap: break-word', () => {
    expect(cssContent).toMatch(/\.leaflet-tooltip\s*\{[^}]*word-wrap:\s*break-word/s)
  })
})
