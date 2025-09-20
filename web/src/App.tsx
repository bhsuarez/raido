import React from 'react'
import { Routes, Route } from 'react-router-dom'

// Components
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import NowPlaying from './components/NowPlaying'
import ComingUp from './components/ComingUp'
import PlayHistory from './components/PlayHistory'
import TTSMonitor from './components/TTSMonitor'
import Analytics from './components/Analytics'
import AuthGuard from './components/AuthGuard'
import AuthCallback from './components/AuthCallback'
// import DJSettings from './components/DJSettings' // Removed - functionality moved to TTSMonitor

function App() {

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900">
      <Layout>
        <ErrorBoundary>
        <Routes>
          <Route
            path="/"
            element={
              <AuthGuard>
                <div className="space-y-6">
                  <ErrorBoundary fallback={<div className="card p-6 text-gray-300">Failed to render Now Playing.</div>}>
                    <NowPlaying />
                  </ErrorBoundary>
                  <ErrorBoundary fallback={<div className="card p-6 text-gray-300">Failed to render Coming Up.</div>}>
                    <ComingUp />
                  </ErrorBoundary>
                  <ErrorBoundary fallback={<div className="card p-6 text-gray-300">Failed to render Play History.</div>}>
                    <PlayHistory />
                  </ErrorBoundary>
                </div>
              </AuthGuard>
            }
          />
          <Route
            path="/history"
            element={
              <AuthGuard>
                <PlayHistory />
              </AuthGuard>
            }
          />
          <Route
            path="/tts"
            element={
              <AuthGuard>
                <TTSMonitor />
              </AuthGuard>
            }
          />
          <Route
            path="/analytics"
            element={
              <AuthGuard>
                <Analytics />
              </AuthGuard>
            }
          />
          <Route
            path="/auth/callback"
            element={<AuthCallback />}
          />
          {/* DJ Settings route removed - functionality moved to /tts */}
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
        </ErrorBoundary>
      </Layout>
    </div>
  )
}

export default App
