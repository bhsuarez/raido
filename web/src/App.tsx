import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

// Components
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import NowPlaying from './components/NowPlaying'
import ComingUp from './components/ComingUp'
import PlayHistory from './components/PlayHistory'
import TTSMonitor from './components/TTSMonitor'
import Analytics from './components/Analytics'
import StationControlPanel from './components/StationControlPanel'
// import DJSettings from './components/DJSettings' // Removed - functionality moved to TTSMonitor

function App() {

  return (
    <div className="min-h-screen">
      <Layout>
        <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Navigate to="/stations" replace />} />
          <Route 
            path="/now-playing" 
            element={
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
            } 
          />
          <Route 
            path="/history" 
            element={<PlayHistory />} 
          />
          <Route path="/tts" element={<Navigate to="/raido/admin" replace />} />
          <Route
            path="/raido/admin"
            element={<TTSMonitor />}
          />
          <Route
            path="/analytics"
            element={<Analytics />}
          />
          <Route
            path="/stations"
            element={<StationControlPanel />}
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
