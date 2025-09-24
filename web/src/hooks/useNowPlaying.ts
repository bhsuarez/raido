import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import { NowPlaying, useRadioStore } from '../store/radioStore'

export function useNowPlaying() {
  const stationSlug = useRadioStore(state => state.currentStationSlug)

  return useQuery<NowPlaying>({
    queryKey: ['nowPlaying', stationSlug],
    queryFn: () => api.get(`/now?station_slug=${stationSlug}`).then(res => res.data),
    refetchInterval: 10000, // Refetch every 10 seconds
    staleTime: 5000, // Consider stale after 5 seconds
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    retry: 3,
    enabled: Boolean(stationSlug),
  })
}

export function usePlayHistory(limit = 20, offset = 0) {
  const stationSlug = useRadioStore(state => state.currentStationSlug)

  return useQuery({
    queryKey: ['history', stationSlug, limit, offset],
    queryFn: () => api.get(`/now/history?limit=${limit}&offset=${offset}&station_slug=${stationSlug}`).then(res => res.data),
    staleTime: 30000, // History is less frequently updated
    refetchInterval: 60000, // Refetch every minute
    retry: 2,
    enabled: Boolean(stationSlug),
  })
}

export function useNextUp() {
  const stationSlug = useRadioStore(state => state.currentStationSlug)

  return useQuery({
    queryKey: ['nextUp', stationSlug],
    queryFn: () => api.get(`/now/next?limit=1&station_slug=${stationSlug}`).then(res => res.data),
    refetchInterval: 30000, // Every 30 seconds
    staleTime: 15000,
    retry: 2,
    enabled: Boolean(stationSlug),
  })
}
