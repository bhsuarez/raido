import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface Track {
  id: number
  title: string
  artist: string
  album?: string
  year?: number
  genre?: string
  duration_sec?: number
  artwork_url?: string
  tags: string[]
  is_christmas?: boolean
}

export interface Play {
  id: number
  started_at: string
  ended_at?: string
  liquidsoap_id?: string
  station_slug?: string
}

export interface Progress {
  elapsed_seconds: number
  total_seconds: number
  percentage: number
}

export interface NowPlaying {
  is_playing: boolean
  track?: Track
  play?: Play
  progress?: Progress
  station_slug?: string
  station_name?: string
}

export interface Station {
  id: number
  name: string
  slug: string
  stream_mount: string
  stream_url?: string
  description?: string
  genre?: string
  stream_name?: string
}

export interface Commentary {
  id: number
  text: string
  audio_url?: string
  duration_ms?: number
  created_at: string
}

export interface RadioState {
  // Connection state
  isConnected: boolean
  setIsConnected: (connected: boolean) => void

  // Now playing
  nowPlaying?: NowPlaying
  nowPlayingByStation: Record<string, NowPlaying | undefined>
  updateNowPlaying: (data: NowPlaying) => void

  // UI state
  isDarkMode: boolean
  toggleDarkMode: () => void

  // Stations
  stations: Station[]
  setStations: (stations: Station[]) => void
  currentStationSlug: string
  setCurrentStationSlug: (slug: string) => void

  // Audio player state
  volume: number
  setVolume: (volume: number) => void
  isMuted: boolean
  toggleMute: () => void
  
  // Admin state
  isAdmin: boolean
  setIsAdmin: (isAdmin: boolean) => void
}

export const useRadioStore = create<RadioState>()(
  devtools(
    (set, get) => ({
      // Connection state
      isConnected: false,
      setIsConnected: (connected) => set({ isConnected: connected }),
      
      // Now playing
      nowPlaying: undefined,
      nowPlayingByStation: {},
      updateNowPlaying: (data) => {
        const currentState = get()
        const slug = data.station_slug || data.play?.station_slug || currentState.currentStationSlug || 'main'
        set((state) => {
          const updatedByStation = { ...state.nowPlayingByStation, [slug]: data }
          const activeSlug = state.currentStationSlug || slug
          return {
            nowPlayingByStation: updatedByStation,
            nowPlaying: updatedByStation[activeSlug] ?? state.nowPlaying,
          }
        })
      },

      // Stations
      stations: [],
      setStations: (stations) => {
        set((state) => {
          const nextStations = stations ?? []
          const hasCurrent = nextStations.some((s) => s.slug === state.currentStationSlug)
          const newSlug = hasCurrent
            ? state.currentStationSlug
            : nextStations[0]?.slug || state.currentStationSlug || 'main'
          return {
            stations: nextStations,
            currentStationSlug: newSlug,
            nowPlaying: state.nowPlayingByStation[newSlug] ?? state.nowPlaying,
          }
        })
      },
      currentStationSlug: 'main',
      setCurrentStationSlug: (slug) => {
        set((state) => ({
          currentStationSlug: slug,
          nowPlaying: state.nowPlayingByStation[slug] ?? state.nowPlaying,
        }))
      },

      // UI state
      isDarkMode: true,
      toggleDarkMode: () => {
        const newMode = !get().isDarkMode
        set({ isDarkMode: newMode })
        
        // Update document class
        if (newMode) {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
        
        // Store in localStorage
        localStorage.setItem('raido-dark-mode', newMode.toString())
      },
      
      // Audio player state
      volume: parseInt(localStorage.getItem('raido-volume') || '75'),
      setVolume: (volume) => {
        set({ volume })
        localStorage.setItem('raido-volume', volume.toString())
      },
      
      isMuted: localStorage.getItem('raido-muted') === 'true',
      toggleMute: () => {
        const newMuted = !get().isMuted
        set({ isMuted: newMuted })
        localStorage.setItem('raido-muted', newMuted.toString())
      },
      
      // Admin state
      isAdmin: false,
      setIsAdmin: (isAdmin) => set({ isAdmin }),
    }),
    {
      name: 'raido-store'
    }
  )
)

// Initialize dark mode from localStorage
const isDarkMode = localStorage.getItem('raido-dark-mode') !== 'false'
if (isDarkMode) {
  document.documentElement.classList.add('dark')
} else {
  document.documentElement.classList.remove('dark')
}