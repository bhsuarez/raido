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
}

export interface Play {
  id: number
  started_at: string
  ended_at?: string
  liquidsoap_id?: string
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
  updateNowPlaying: (data: NowPlaying) => void

  // Commentary streaming
  commentaryText: string
  isGeneratingCommentary: boolean
  appendCommentaryToken: (token: string) => void
  setCommentaryReady: (transcript: string) => void
  clearCommentary: () => void

  // UI state
  isDarkMode: boolean
  toggleDarkMode: () => void

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
      updateNowPlaying: (data) => set({ nowPlaying: data }),

      // Commentary streaming
      commentaryText: '',
      isGeneratingCommentary: false,
      appendCommentaryToken: (token) =>
        set((state) => ({
          commentaryText: state.commentaryText + token,
          isGeneratingCommentary: true,
        })),
      setCommentaryReady: (transcript) =>
        set({ commentaryText: transcript, isGeneratingCommentary: false }),
      clearCommentary: () =>
        set({ commentaryText: '', isGeneratingCommentary: false }),
      
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