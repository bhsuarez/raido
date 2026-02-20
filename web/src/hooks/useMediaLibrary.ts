import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiHelpers } from '../utils/api'

export interface Track {
  id: number
  title: string
  artist: string
  album: string | null
  year: number | null
  genre: string | null
  duration_sec: number | null
  bitrate: number | null
  artwork_url: string | null
  file_path: string
  play_count: number
  recording_mbid: string | null
  release_mbid: string | null
  last_played_at: string | null
}

export interface TrackFacets {
  genres: string[]
  artists: string[]
  albums: string[]
}

export interface MBCandidate {
  recording_mbid: string
  release_mbid: string | null
  title: string
  artist: string
  album: string | null
  year: number | null
  country: string | null
  label: string | null
  artwork_url: string | null
  genre: string | null
}

export interface TrackFilters {
  search?: string
  genre?: string
  artist?: string
  album?: string
  sort?: 'artist' | 'album' | 'title' | 'play_count'
  page?: number
  per_page?: number
  no_artwork?: boolean
}

export interface TracksResult {
  tracks: Track[]
  total: number
}

export function useTracks(params: TrackFilters) {
  return useQuery<TracksResult>({
    queryKey: ['tracks', params],
    queryFn: () =>
      apiHelpers.getTracks(params).then(res => ({
        tracks: res.data as Track[],
        total: parseInt(res.headers['x-total-count'] || '0', 10),
      })),
    staleTime: 30000,
    retry: 2,
  })
}

export function useTrackFacets() {
  return useQuery<TrackFacets>({
    queryKey: ['trackFacets'],
    queryFn: () => apiHelpers.getTrackFacets().then(res => res.data),
    staleTime: 60000,
  })
}

export function useMusicBrainzSearch(trackId: number | null) {
  return useQuery<MBCandidate[]>({
    queryKey: ['musicbrainz', trackId],
    queryFn: () => apiHelpers.searchMusicBrainz(trackId!).then(res => res.data),
    enabled: false, // only fetch when explicitly triggered
    retry: 1,
  })
}

export function useUpdateTrack() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Track> }) =>
      apiHelpers.updateTrack(id, data).then(res => res.data),
    onSuccess: (updatedTrack: Track) => {
      queryClient.invalidateQueries({ queryKey: ['tracks'] })
      queryClient.setQueryData(['track', updatedTrack.id], updatedTrack)
    },
  })
}
