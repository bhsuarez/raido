import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  userId: number | null
  email: string | null
  role: string | null
  fullName: string | null
  displayName: string | null
  avatarUrl: string | null
  setAuth: (token: string, userId: number, email: string, role: string) => void
  setProfile: (profile: { full_name?: string | null; display_name?: string | null; avatar_url?: string | null }) => void
  clearAuth: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      userId: null,
      email: null,
      role: null,
      fullName: null,
      displayName: null,
      avatarUrl: null,
      setAuth: (token, userId, email, role) => set({ token, userId, email, role }),
      setProfile: (profile) => set({
        fullName: profile.full_name ?? get().fullName,
        displayName: profile.display_name ?? get().displayName,
        avatarUrl: profile.avatar_url ?? get().avatarUrl,
      }),
      clearAuth: () => set({ token: null, userId: null, email: null, role: null, fullName: null, displayName: null, avatarUrl: null }),
      isAuthenticated: () => !!get().token,
    }),
    { name: 'raido-auth' }
  )
)
