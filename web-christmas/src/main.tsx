import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute - data is considered fresh for this long
      gcTime: 10 * 60 * 1000, // 10 minutes - cache cleanup time
      refetchOnWindowFocus: false, // Don't refetch when window gains focus
      refetchOnMount: true, // Do refetch when component mounts
      refetchInterval: false, // Don't auto-refetch by default (individual hooks can override)
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false
        }
        return failureCount < 2 // Reduce retries from 3 to 2
      },
    },
  },
})

const baseUrl = import.meta.env.BASE_URL || '/'
const basename = baseUrl === '/' ? '/' : baseUrl.replace(/\/$/, '')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={basename}>
        <App />
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#1f2937',
              color: '#f9fafb',
              border: '1px solid #374151',
            },
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
