import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import DJSettings from '../../components/DJSettings'

vi.mock('../../utils/api', async () => {
  const actual = await vi.importActual<any>('../../utils/api')
  return {
    ...actual,
    apiHelpers: {
      ...actual.apiHelpers,
      getSettings: vi.fn(() => Promise.resolve({
        data: {
          dj_provider: 'ollama',
          dj_voice_provider: 'kokoro',
          dj_model: 'llama3.2:1b',
          dj_prompt_template: 'template',
          dj_temperature: 0.8,
          dj_max_tokens: 200,
          dj_max_seconds: 30,
          dj_commentary_interval: 1,
          dj_tone: 'energetic',
          dj_profanity_filter: true,
          enable_commentary: true,
          station_name: 'Raido Pirate Radio',
        },
      })),
      updateSettings: vi.fn(() => Promise.resolve({ status: 200 })),
    },
  }
})

describe('DJSettings', () => {
  it('loads settings and saves changes', async () => {
    render(<DJSettings />)

    // Wait for settings to load
    await waitFor(() => {
      expect(screen.getByText('DJ Configuration')).toBeInTheDocument()
    })

    // Change station name
    const stationInput = screen.getByLabelText('Station Name') as HTMLInputElement
    fireEvent.change(stationInput, { target: { value: 'Elements Radio' } })

    // Save
    const saveButton = screen.getByRole('button', { name: /save settings/i })
    fireEvent.click(saveButton)

    const { apiHelpers } = await import('../../utils/api')
    await waitFor(() => {
      expect(apiHelpers.updateSettings).toHaveBeenCalled()
    })
    // Validate payload contains updated field
    const lastCall = (apiHelpers.updateSettings as any).mock.calls.at(-1)[0]
    expect(lastCall.station_name).toBe('Elements Radio')
  })

  it('shows error toast on save failure', async () => {
    const { apiHelpers } = await import('../../utils/api')
    ;(apiHelpers.updateSettings as any).mockImplementationOnce(() => Promise.reject(new Error('boom')))

    render(<DJSettings />)
    await waitFor(() => screen.getByText('DJ Configuration'))

    fireEvent.click(screen.getByRole('button', { name: /save settings/i }))

    const toast = (await import('react-hot-toast')).toast
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled()
    })
  })
})

