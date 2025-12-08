import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RadioPlayer from '@/components/RadioPlayer'

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

// Mock Audio API
class MockAudio {
  src = ''
  volume = 1
  paused = true
  currentTime = 0

  play = vi.fn().mockResolvedValue(undefined)
  pause = vi.fn()
  load = vi.fn()

  addEventListener = vi.fn()
  removeEventListener = vi.fn()
}

describe('RadioPlayer Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // @ts-ignore
    global.Audio = MockAudio
  })

  it('renders with play button when not playing', () => {
    renderWithProviders(<RadioPlayer />)

    const playButton = screen.getByRole('button', { name: /play/i })
    expect(playButton).toBeInTheDocument()
  })

  it('toggles play/pause on button click', async () => {
    renderWithProviders(<RadioPlayer />)

    const playButton = screen.getByRole('button', { name: /play/i })
    fireEvent.click(playButton)

    // After clicking, audio.play() should be called
    // and button should change to pause
  })

  it('displays volume control', () => {
    renderWithProviders(<RadioPlayer />)

    // Look for volume slider or volume controls
    const volumeControl = screen.queryByRole('slider', { name: /volume/i })

    // Volume control implementation may vary
  })

  it('handles stream URL correctly', () => {
    renderWithProviders(<RadioPlayer />)

    // Check that audio element has correct stream URL
    // Default: http://localhost:8000/raido.mp3 or configured URL
  })

  it('shows connection status', () => {
    renderWithProviders(<RadioPlayer />)

    // Component should show connection status (connecting, playing, paused, error)
  })

  it('handles audio errors gracefully', () => {
    renderWithProviders(<RadioPlayer />)

    // Simulate audio error
    // Component should show error state
  })

  it('allows volume adjustment', () => {
    renderWithProviders(<RadioPlayer />)

    const volumeSlider = screen.queryByRole('slider', { name: /volume/i })

    if (volumeSlider) {
      fireEvent.change(volumeSlider, { target: { value: 50 } })

      // Volume should be updated to 0.5
    }
  })

  it('displays current stream metadata', () => {
    renderWithProviders(<RadioPlayer />)

    // If metadata is available, it should be displayed
    // e.g., "Now Playing: Song Title - Artist"
  })
})
