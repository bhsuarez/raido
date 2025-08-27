import axios from 'axios'
import { toast } from 'react-hot-toast'

// Create axios instance with default config
export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('raido-token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    
    // Don't show error toasts for expected errors
    if (error.response?.status === 401) {
      // Unauthorized - redirect to login or clear token
      localStorage.removeItem('raido-token')
      window.location.reload()
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
)

// Helper functions for common API patterns
export const apiHelpers = {
  // Stream-related endpoints
  getNowPlaying: () => api.get('/now'),
  getHistory: (limit = 20, offset = 0) => api.get(`/now/history?limit=${limit}&offset=${offset}`),
  getNextUp: () => api.get('/now/next'),
  
  // Admin endpoints
  getSettings: () => api.get('/admin/settings'),
  updateSettings: (settings: Record<string, any>) => api.post('/admin/settings', settings),
  getStats: () => api.get('/admin/stats'),
  
  // User management
  getUsers: () => api.get('/admin/users'),
  createUser: (userData: any) => api.post('/admin/users', userData),
  updateUser: (userId: number, userData: any) => api.put(`/admin/users/${userId}`, userData),
  deleteUser: (userId: number) => api.delete(`/admin/users/${userId}`),
}

export default api