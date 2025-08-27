import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import { NowPlaying } from '../store/radioStore'

export function useNowPlaying() {
  return useQuery<NowPlaying>({
    queryKey: ['nowPlaying'],
    queryFn: () => api.get('/now').then(res => res.data),
    refetchInterval: 5000, // Refetch every 5 seconds as fallback
    staleTime: 3000, // Consider stale after 3 seconds
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  })
}

export function usePlayHistory(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ['history', limit, offset],
    queryFn: () => api.get(`/now/history?limit=${limit}&offset=${offset}`).then(res => res.data),
    staleTime: 10000, // History is less frequently updated
  })
}

export function useNextUp() {
  return useQuery({
    queryKey: ['nextUp'],
    queryFn: () => api.get('/now/next').then(res => res.data),
    refetchInterval: 10000,
    staleTime: 5000,
  })
}