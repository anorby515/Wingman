import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ConfigureTab from '../components/ConfigureTab.jsx'

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    if (url === '/api/artists') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { name: 'Tyler Childers', url: 'https://tc.com', genre: 'Country / Americana', paused: false },
        ]),
      })
    }
    if (url === '/api/venues') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { name: 'Wells Fargo Arena', url: 'https://wfa.com', city: 'Des Moines, IA', is_local: true, paused: false },
        ]),
      })
    }
    if (url === '/api/festivals') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { name: 'Hinterland', url: 'https://hinterland.com', paused: false },
        ]),
      })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
  })
})

describe('ConfigureTab', () => {
  it('renders sub-tabs for Artists, Venues, Festivals', () => {
    render(<ConfigureTab />)
    expect(screen.getByText('Artists')).toBeInTheDocument()
    expect(screen.getByText('Venues')).toBeInTheDocument()
    expect(screen.getByText('Festivals')).toBeInTheDocument()
  })

  it('defaults to Artists sub-tab', async () => {
    render(<ConfigureTab />)
    // Wait for artist data to load
    await waitFor(() => {
      expect(screen.getByText('Tyler Childers')).toBeInTheDocument()
    })
  })

  it('switches to Festivals sub-tab', async () => {
    const user = userEvent.setup()
    render(<ConfigureTab />)

    await user.click(screen.getByText('Festivals'))
    await waitFor(() => {
      expect(screen.getByText('Hinterland')).toBeInTheDocument()
    })
  })
})
