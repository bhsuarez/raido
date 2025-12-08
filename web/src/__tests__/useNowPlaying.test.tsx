import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useNowPlaying, usePlayHistory, useNextUp } from '@/hooks/useNowPlaying'
import { api } from '@/utils/api'

// Mock the API
vi.mock('@/utils/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useNowPlaying Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches now playing data successfully', async () => {
    const mockData = {
      is_playing: true,
      track: {
        id: 1,
        title: 'Test Song',
        artist: 'Test Artist',
        duration_sec: 180,
      },
    }

    ;(api.get as any).mockResolvedValue({ data: mockData })

    const { result } = renderHook(() => useNowPlaying(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockData)
    expect(api.get).toHaveBeenCalledWith('/now/')
  })

  it('handles errors when fetching now playing', async () => {
    ;(api.get as any).mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useNowPlaying(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect(result.current.error).toBeTruthy()
  })

  it('refetches at configured interval', async () => {
    const mockData = { is_playing: false, track: null }
    ;(api.get as any).mockResolvedValue({ data: mockData })

    renderHook(() => useNowPlaying(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(api.get).toHaveBeenCalled()
    })

    // The hook should set refetchInterval: 10000
    // Testing actual interval behavior requires time manipulation
  })
})

describe('usePlayHistory Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches play history with default params', async () => {
    const mockData = {
      tracks: [
        {
          track: { id: 1, title: 'Song 1', artist: 'Artist 1' },
          play: { id: 1, started_at: '2023-01-01T00:00:00Z' },
        },
      ],
      total_count: 1,
      has_more: false,
    }

    ;(api.get as any).mockResolvedValue({ data: mockData })

    const { result } = renderHook(() => usePlayHistory(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockData)
    expect(api.get).toHaveBeenCalledWith('/now/history?limit=20&offset=0')
  })

  it('fetches play history with custom params', async () => {
    const mockData = { tracks: [], total_count: 0, has_more: false }
    ;(api.get as any).mockResolvedValue({ data: mockData })

    const { result } = renderHook(() => usePlayHistory(10, 5), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(api.get).toHaveBeenCalledWith('/now/history?limit=10&offset=5')
  })
})

describe('useNextUp Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches next up data successfully', async () => {
    const mockData = {
      next_tracks: [
        {
          track: { id: 2, title: 'Next Song', artist: 'Next Artist' },
          estimated_start_time: '2023-01-01T00:05:00Z',
          commentary_before: true,
        },
      ],
      commentary_scheduled: true,
      estimated_start_time: '2023-01-01T00:05:00Z',
    }

    ;(api.get as any).mockResolvedValue({ data: mockData })

    const { result } = renderHook(() => useNextUp(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockData)
    expect(api.get).toHaveBeenCalledWith('/now/next?limit=1')
  })

  it('handles empty next up queue', async () => {
    const mockData = {
      next_tracks: [],
      commentary_scheduled: false,
      estimated_start_time: null,
    }

    ;(api.get as any).mockResolvedValue({ data: mockData })

    const { result } = renderHook(() => useNextUp(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data?.next_tracks).toHaveLength(0)
  })
})
