import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { useWebSocket } from './hooks/useWebSocket'
import { useNowPlaying } from './hooks/useNowPlaying'

// Components
import Layout from './components/Layout'
import RadioPlayer from './components/RadioPlayer'
import PlayHistory from './components/PlayHistory'
import AdminPanel from './components/AdminPanel'
import LoadingSpinner from './components/LoadingSpinner'

function App() {
  // Initialize WebSocket connection
  useWebSocket()
  
  // Keep now playing data fresh
  const { data: nowPlaying, isLoading } = useNowPlaying()

  if (isLoading) {
    return <LoadingSpinner />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900">
      <Layout>
        <Routes>
          <Route 
            path="/" 
            element={
              <div className="space-y-8">
                <RadioPlayer nowPlaying={nowPlaying} />
                <PlayHistory />
              </div>
            } 
          />
          <Route 
            path="/history" 
            element={<PlayHistory />} 
          />
          <Route 
            path="/admin" 
            element={<AdminPanel />} 
          />
          <Route 
            path="*" 
            element={
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-white mb-2">
                    🏴‍☠️ Page Not Found
                  </h2>
                  <p className="text-gray-400">
                    Ye've sailed into uncharted waters, matey!
                  </p>
                </div>
              </div>
            } 
          />
        </Routes>
      </Layout>
    </div>
  )
}

export default App