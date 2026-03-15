import { Routes, Route, Navigate } from 'react-router-dom'

// Components
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import NowPlaying from './components/NowPlaying'
import CommentaryTranscript from './components/CommentaryTranscript'
import ComingUp from './components/ComingUp'
import PlayHistory from './components/PlayHistory'
import TTSMonitor from './components/TTSMonitor'
import Analytics from './components/Analytics'
import StationControlPanel from './components/StationControlPanel'
import MediaLibrary from './components/MediaLibrary'
import LoginPage from './components/LoginPage'
import MBEnrich from './components/MBEnrich'
import CommentaryBrowser from './components/CommentaryBrowser'
import { RequireAuth } from './components/RequireAuth'
import { RequireAdmin } from './components/RequireAdmin'
import RegisterPage from './components/RegisterPage'
// import DJSettings from './components/DJSettings' // Removed - functionality moved to TTSMonitor

function App() {

  return (
    <div className="min-h-screen">
      <ErrorBoundary>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* All authenticated routes */}
          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/now-playing" replace />} />
              <Route
                path="/now-playing"
                element={
                  <div className="space-y-6">
                    <ErrorBoundary fallback={<div className="card p-6 text-gray-300">Failed to render Now Playing.</div>}>
                      <NowPlaying />
                    </ErrorBoundary>
                    <CommentaryTranscript />
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
                path="/analytics"
                element={<Analytics />}
              />
              <Route
                path="/transcripts"
                element={<CommentaryBrowser />}
              />

              {/* Admin-only routes */}
              <Route element={<RequireAdmin />}>
                <Route
                  path="/raido/admin"
                  element={<TTSMonitor />}
                />
                <Route
                  path="/:station/admin"
                  element={<TTSMonitor />}
                />
                <Route
                  path="/stations"
                  element={<StationControlPanel />}
                />
                <Route
                  path="/media"
                  element={<MediaLibrary />}
                />
                <Route
                  path="/media/tracks/:trackId"
                  element={<MediaLibrary />}
                />
                <Route
                  path="/raido/enrich"
                  element={<MBEnrich />}
                />
                <Route
                  path="/admin/users"
                  element={<div className="card p-8 text-gray-400">User Management — coming soon</div>}
                />
                <Route
                  path="/admin/listeners"
                  element={<div className="card p-8 text-gray-400">Listener Analytics — coming soon</div>}
                />
              </Route>

              {/* 404 fallback */}
              <Route
                path="*"
                element={
                  <div className="card p-12 flex flex-col items-center gap-2 text-center">
                    <p className="text-4xl font-bold text-gray-700">404</p>
                    <p className="text-gray-400 font-medium mt-1">Page not found</p>
                    <p className="text-gray-600 text-sm">The page you're looking for doesn't exist.</p>
                  </div>
                }
              />
            </Route>
          </Route>
        </Routes>
      </ErrorBoundary>
    </div>
  )
}

export default App
