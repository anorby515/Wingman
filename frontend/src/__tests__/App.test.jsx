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
    expect(screen.getByText('Wingman')).toBeInTheDocument()
    expect(screen.getByText('Concert Tracker')).toBeInTheDocument()
  })

  it('renders all tab buttons in local mode', () => {
    render(<App />)
    expect(screen.getByRole('tab', { name: /Coming Soon/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Artists/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Festivals/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Venues/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Configure/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Settings/i })).toBeInTheDocument()
  })

  it('defaults to Coming Soon tab as active', () => {
    render(<App />)
    const comingSoonTab = screen.getByRole('tab', { name: /Coming Soon/i })
    expect(comingSoonTab).toHaveAttribute('aria-selected', 'true')
  })

  it('switches tabs on click', async () => {
    const user = userEvent.setup()
    render(<App />)

    const artistsTab = screen.getByRole('tab', { name: /Artists/i })
    await user.click(artistsTab)
    expect(artistsTab).toHaveAttribute('aria-selected', 'true')

    const comingSoonTab = screen.getByRole('tab', { name: /Coming Soon/i })
    expect(comingSoonTab).toHaveAttribute('aria-selected', 'false')
  })
})
