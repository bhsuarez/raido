// web/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'

import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import NowPlayingPage from './pages/NowPlayingPage'
import TTSMonitor from './components/TTSMonitor'
import Analytics from './components/Analytics'
import LoginPage from './components/LoginPage'
import LibraryPage from './pages/LibraryPage'

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Navigate to="/now-playing" replace />} />

        {/* Full-screen immersive view */}
        <Route
          path="/now-playing"
          element={
            <Layout fullscreen>
              <NowPlayingPage />
            </Layout>
          }
        />

        {/* DJ Admin — per station */}
        <Route
          path="/raido/admin"
          element={
            <Layout>
              <TTSMonitor />
            </Layout>
          }
        />
        <Route
          path="/:station/admin"
          element={
            <Layout>
              <TTSMonitor />
            </Layout>
          }
        />

        {/* Library — browse + enrich */}
        <Route
          path="/library"
          element={
            <Layout>
              <LibraryPage />
            </Layout>
          }
        />

        {/* Media track deep-link — renders LibraryPage so MediaLibrary can handle the trackId */}
        <Route
          path="/media/tracks/:trackId"
          element={
            <Layout>
              <LibraryPage />
            </Layout>
          }
        />

        {/* Analytics */}
        <Route
          path="/analytics"
          element={
            <Layout>
              <Analytics />
            </Layout>
          }
        />

        {/* Auth */}
        <Route
          path="/login"
          element={
            <Layout>
              <LoginPage />
            </Layout>
          }
        />

        {/* Legacy redirects */}
        <Route path="/tts" element={<Navigate to="/raido/admin" replace />} />
        <Route path="/media" element={<Navigate to="/library" replace />} />
        <Route path="/raido/enrich" element={<Navigate to="/library?tab=enrich" replace />} />
        <Route path="/stations" element={<Navigate to="/now-playing" replace />} />
        <Route path="/transcripts" element={<Navigate to="/raido/admin" replace />} />
        <Route path="/history" element={<Navigate to="/now-playing" replace />} />

        {/* 404 */}
        <Route
          path="*"
          element={
            <Layout>
              <div className="card p-12 flex flex-col items-center gap-2 text-center mt-8">
                <p className="text-4xl font-bold" style={{ color: '#1a1a32' }}>404</p>
                <p className="text-sm font-medium" style={{ color: '#404060' }}>Page not found</p>
              </div>
            </Layout>
          }
        />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
