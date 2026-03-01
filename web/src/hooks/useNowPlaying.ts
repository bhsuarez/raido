import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import { NowPlaying } from '../store/radioStore'

export interface CommentaryTrack {
  id: number
  title: string
  artist: string
  album: string | null
  artwork_url: string | null
}

export interface CommentaryItem {
  id: number
  transcript: string | null
  text: string
  provider: string
  model: string | null
  audio_url: string | null
  duration_ms: number | null
  created_at: string
  track: CommentaryTrack | null
}

export interface CommentariesResult {
  items: CommentaryItem[]
  total: number
  page: number
  per_page: number
  total_tracks: number
}

export interface CommentaryFilters {
  provider?: string
  status?: string
  search?: string
  page?: number
  per_page?: number
}

export function useNowPlaying() {
  return useQuery<NowPlaying>({
    queryKey: ['nowPlaying'],
    queryFn: () => api.get('/now/').then(res => res.data),
    refetchInterval: 10000, // Refetch every 10 seconds 
    staleTime: 5000, // Consider stale after 5 seconds
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    retry: 3,
  })
}

export function usePlayHistory(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ['history', limit, offset],
    queryFn: () => api.get(`/now/history?limit=${limit}&offset=${offset}`).then(res => res.data),
    staleTime: 30000, // History is less frequently updated
    refetchInterval: 60000, // Refetch every minute
    retry: 2,
  })
}

export function useNextUp() {
  return useQuery({
    queryKey: ['nextUp'],
    queryFn: () => api.get('/now/next?limit=5').then(res => res.data),
    refetchInterval: 30000, // Every 30 seconds
    staleTime: 15000,
    retry: 2,
  })
}

export function useCommentaries(filters: CommentaryFilters = {}) {
  return useQuery<CommentariesResult>({
    queryKey: ['commentaries', filters],
    queryFn: () => {
      const params = new URLSearchParams()
      if (filters.provider) params.set('provider', filters.provider)
      if (filters.status) params.set('status', filters.status)
      if (filters.search) params.set('search', filters.search)
      params.set('page', String(filters.page ?? 1))
      params.set('per_page', String(filters.per_page ?? 20))
      return api.get(`/admin/commentaries?${params}`).then(res => res.data)
    },
    staleTime: 30000,
    retry: 2,
  })
}
