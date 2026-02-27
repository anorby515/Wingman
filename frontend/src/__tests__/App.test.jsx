import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from '../App.jsx'

beforeEach(() => {
  // Mock fetch so components that call /api/* don't break
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    if (url === '/api/config') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          center_city: 'Des Moines, IA',
          github_pages_url: '',
          artists: {},
          venues: {},
          festivals: {},
        }),
      })
    }
    if (url === '/api/shows') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          api_configured: false,
          artist_shows: {},
          venue_shows: {},
          festival_shows: {},
          coming_soon: [],
          festival_coming_soon: [],
          artists_not_found: [],
          venues_not_found: [],
          festivals_not_found: [],
          last_refreshed: null,
          stale: true,
        }),
      })
    }
    // Default: return empty array for list endpoints
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    })
  })
})

describe('App', () => {
  it('renders the Wingman header', () => {
    render(<App />)
    expect(screen.getByText('WINGMAN')).toBeInTheDocument()
  })

  it('renders Configure and Settings tabs in local mode', () => {
    render(<App />)
    expect(screen.getByRole('tab', { name: /Configure/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Settings/i })).toBeInTheDocument()
    // Viewer tabs are not shown in local mode
    expect(screen.queryByRole('tab', { name: /Concerts & Festivals/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /On Sale Soon/i })).not.toBeInTheDocument()
  })

  it('defaults to Configure tab as active in local mode', () => {
    render(<App />)
    const configureTab = screen.getByRole('tab', { name: /Configure/i })
    expect(configureTab).toHaveAttribute('aria-selected', 'true')
  })

  it('switches tabs on click', async () => {
    const user = userEvent.setup()
    render(<App />)

    const settingsTab = screen.getByRole('tab', { name: /Settings/i })
    await user.click(settingsTab)
    expect(settingsTab).toHaveAttribute('aria-selected', 'true')

    const configureTab = screen.getByRole('tab', { name: /Configure/i })
    expect(configureTab).toHaveAttribute('aria-selected', 'false')
  })
})
