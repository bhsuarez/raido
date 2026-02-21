import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  userId: number | null
  email: string | null
  role: string | null
  setAuth: (token: string, userId: number, email: string, role: string) => void
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
      setAuth: (token, userId, email, role) => set({ token, userId, email, role }),
      clearAuth: () => set({ token: null, userId: null, email: null, role: null }),
      isAuthenticated: () => !!get().token,
    }),
    { name: 'raido-auth' }
  )
)
