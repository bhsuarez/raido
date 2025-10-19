import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import { NowPlaying } from '../store/radioStore'

export function useNowPlaying() {
  return useQuery<NowPlaying>({
    queryKey: ['nowPlaying', 'christmas'],
    queryFn: () => api.get('/now/', { params: { station: 'christmas' } }).then(res => res.data),
    refetchInterval: 10000, // Refetch every 10 seconds 
    staleTime: 5000, // Consider stale after 5 seconds
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    retry: 3,
  })
}

export function usePlayHistory(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ['history', 'christmas', limit, offset],
    queryFn: () => api.get('/now/history', { params: { limit, offset, station: 'christmas' } }).then(res => res.data),
    staleTime: 30000, // History is less frequently updated
    refetchInterval: 60000, // Refetch every minute
    retry: 2,
  })
}

export function useNextUp() {
  return useQuery({
    queryKey: ['nextUp', 'christmas'],
    queryFn: () => api.get('/now/next', { params: { limit: 1, station: 'christmas' } }).then(res => res.data),
    refetchInterval: 30000, // Every 30 seconds
    staleTime: 15000,
    retry: 2,
  })
}
