import axios from 'axios'
import { toast } from 'react-hot-toast'

// Determine API base URL
const API_BASE = (import.meta as any)?.env?.VITE_API_URL
  ? `${(import.meta as any).env.VITE_API_URL.replace(/\/$/, '')}/api/v1`
  : '/api/v1'

// Create axios instance with default config
export const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Create a separate axios instance for TTS operations with longer timeout
export const ttsApi = axios.create({
  baseURL: API_BASE,
  timeout: 180000, // 3 minutes for TTS operations
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptors for both instances
const requestInterceptor = (config: any) => {
  // Add auth token if available
  const token = localStorage.getItem('raido-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

const requestErrorInterceptor = (error: any) => {
  return Promise.reject(error)
}

// Response interceptors for both instances
const responseInterceptor = (response: any) => {
  return response
}

const responseErrorInterceptor = (error: any) => {
  const message = error.response?.data?.detail || error.message || 'An error occurred'

  // Don't show error toasts for expected errors
  if (error.response?.status === 401) {
    // Avoid reload loops if no token is set
    const hadToken = Boolean(localStorage.getItem('raido-token'))
    if (hadToken) {
      localStorage.removeItem('raido-token')
      window.location.reload()
    }
    // If no token, surface the error without reloading the page
    return Promise.reject(error)
  } else if (error.response?.status >= 500) {
    // Server errors
    toast.error(`Server error: ${message}`)
  } else if (error.response?.status >= 400) {
    // Client errors (but not auth)
    toast.error(message)
  } else if (error.code === 'NETWORK_ERROR') {
    toast.error('🏴‍☠️ Network error - check your connection!')
  }

  return Promise.reject(error)
}

// Apply interceptors to both instances
api.interceptors.request.use(requestInterceptor, requestErrorInterceptor)
api.interceptors.response.use(responseInterceptor, responseErrorInterceptor)

ttsApi.interceptors.request.use(requestInterceptor, requestErrorInterceptor)
ttsApi.interceptors.response.use(responseInterceptor, responseErrorInterceptor)

// Helper functions for common API patterns
export const apiHelpers = {
  // Stream-related endpoints
  getNowPlaying: (station = 'main') => api.get('/now', { params: { station } }),
  getHistory: (limit = 20, offset = 0, station = 'main') => api.get('/now/history', { params: { limit, offset, station } }),
  getNextUp: (limit = 1, station = 'main') => api.get('/now/next', { params: { limit, station } }),
  
  // Admin endpoints
  getSettings: (station = 'main') => api.get('/admin/settings', { params: { station } }),
  updateSettings: (settings: Record<string, any>, station = 'main') => api.post('/admin/settings', settings, { params: { station } }),
  getStats: () => api.get('/admin/stats'),
  getVoices: () => api.get("/admin/voices"),
  
  // User management
  getUsers: () => api.get('/admin/users'),
  createUser: (userData: any) => api.post('/admin/users', userData),
  updateUser: (userId: number, userData: any) => api.put(`/admin/users/${userId}`, userData),
  deleteUser: (userId: number) => api.delete(`/admin/users/${userId}`),
  
  // TTS management
  deleteCommentary: (commentaryId: number) => api.delete(`/admin/commentary/${commentaryId}`),

  // Resolve a static URL to a fully-qualified URL when needed (e.g., dev mode)
  resolveStaticUrl: (url: string | null | undefined): string | null => {
    if (!url) return null
    // Already absolute
    if (/^https?:\/\//i.test(url)) return url
    // If a VITE_API_URL is provided, prefer that origin for static assets
    const rawBase = (import.meta as any)?.env?.VITE_API_URL as string | undefined
    if (rawBase && url.startsWith('/')) {
      // Strip trailing slash and /api[/v1] if present
      const trimmed = rawBase.replace(/\/$/, '')
      const withoutApi = trimmed.replace(/\/(api)(\/v1)?$/i, '')
      return `${withoutApi}${url}`
    }
    // Fall back to relative path (same origin)
    return url
  },

  // Stream controls
  skipTrack: () => api.post('/liquidsoap/skip'),

  // Music library and stations
  getTracks: () => api.get('/tracks'),
  getStations: () => api.get('/admin/stations'),
  createStation: (data: any) => api.post('/stations', data),
}

export default api
