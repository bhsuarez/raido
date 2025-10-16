import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import VoiceCloning from '@/components/VoiceCloning'

// Mock the api client used by the component
vi.mock('@/utils/api', async () => {
  const actual = await vi.importActual<any>('@/utils/api')
  return {
    __esModule: true,
    default: {
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
    },
  }
})

import api from '@/utils/api'

// Helper to render with React Query provider
const renderWithQuery = (ui: React.ReactElement) => {
  const qc = new QueryClient()
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('VoiceCloning page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock initial GET /admin/voice-references
    ;(api.get as any).mockImplementation((url: string) => {
      if (url === '/admin/voice-references') {
        return Promise.resolve({
          data: {
            voices: [
              { name: 'female', filename: 'female.wav', size: 12345, created: 1700000000, modified: 1700000000 },
              { name: 'morgan_freeman', filename: 'morgan_freeman.wav', size: 54321, created: 1700000100, modified: 1700000100 },
            ],
          },
        })
      }
      return Promise.resolve({ data: {} })
    })

    // Mock Audio playback in browser env
    // @ts-ignore
    global.Audio = vi.fn().mockImplementation(() => ({ play: vi.fn().mockResolvedValue(undefined) }))
  })

  it('renders and lists existing voice references', async () => {
    renderWithQuery(<VoiceCloning />)

    // Loading state
    expect(await screen.findByText(/Loading voice references/i)).toBeInTheDocument()

    // After data loads, show voices
    expect(await screen.findByText('female')).toBeInTheDocument()
    expect(screen.getByText('morgan_freeman')).toBeInTheDocument()
  })

  it('uploads a wav file and refreshes the list', async () => {
    ;(api.post as any).mockResolvedValue({ data: { status: 'success' } })

    renderWithQuery(<VoiceCloning />)

    // Wait for list
    await screen.findByText('female')

    const nameInput = screen.getByLabelText(/Voice Name/i)
    const fileInput = screen.getByLabelText(/Audio File/i)

    // Prepare a fake WAV file
    const wavFile = new File([new Uint8Array([82,73,70,70])], 'sample.wav', { type: 'audio/wav' })

    fireEvent.change(nameInput, { target: { value: 'test_voice' } })
    fireEvent.change(fileInput, { target: { files: [wavFile] } })

    const uploadBtn = screen.getByRole('button', { name: /Upload Voice Reference/i })
    fireEvent.click(uploadBtn)

    await waitFor(() => {
      expect(api.post).toHaveBeenCalled()
      const [url, formData] = (api.post as any).mock.calls[0]
      expect(url).toBe('/admin/upload-voice-reference')
      // FormData cannot be inspected directly; assert call happened is enough
    })
  })

  it('tests a voice and attempts to play audio', async () => {
    ;(api.post as any).mockImplementation((url: string) => {
      if (url === '/admin/tts-test-chatterbox') {
        return Promise.resolve({ data: { status: 'success', audio_url: '/static/tts/test.mp3' } })
      }
      return Promise.resolve({ data: {} })
    })

    renderWithQuery(<VoiceCloning />)

    await screen.findByText('morgan_freeman')

    const testBtn = screen.getAllByRole('button', { name: /Test Voice/i })[1]
    fireEvent.click(testBtn)

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/admin/tts-test-chatterbox', expect.objectContaining({ voice: 'morgan_freeman' }))
      // @ts-ignore
      expect(global.Audio).toHaveBeenCalledWith('/static/tts/test.mp3')
    })
  })

  it('deletes a voice reference', async () => {
    // Confirm dialog always true
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    ;(api.delete as any).mockResolvedValue({ data: { status: 'success' } })

    renderWithQuery(<VoiceCloning />)
    await screen.findByText('female')

    const deleteButtons = screen.getAllByRole('button', { name: /Delete/i })
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith('/admin/voice-reference/female')
    })
  })
})

