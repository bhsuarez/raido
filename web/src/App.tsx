import React from 'react'
import { Routes, Route } from 'react-router-dom'

// Components
import Layout from './components/Layout'
import NowPlaying from './components/NowPlaying'
import ComingUp from './components/ComingUp'
import PlayHistory from './components/PlayHistory'
import AdminPanel from './components/AdminPanel'
import TTSMonitor from './components/TTSMonitor'

function App() {

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900">
      <Layout>
        <Routes>
          <Route 
            path="/" 
            element={
              <div className="space-y-6">
                <NowPlaying />
                <ComingUp />
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
            path="/tts" 
            element={<TTSMonitor />} 
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