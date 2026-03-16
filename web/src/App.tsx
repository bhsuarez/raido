import { Routes, Route, Navigate } from 'react-router-dom'

import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import NowPlayingPage from './pages/NowPlayingPage'
import TTSMonitor from './components/TTSMonitor'
import Analytics from './components/Analytics'
import LoginPage from './components/LoginPage'
import LibraryPage from './pages/LibraryPage'
import { RequireAuth } from './components/RequireAuth'
import { RequireAdmin } from './components/RequireAdmin'
import RegisterPage from './components/RegisterPage'
import { UserManagement } from './components/admin/UserManagement'
import { ListenerSessions } from './components/admin/ListenerSessions'
import ProfilePage from './pages/ProfilePage'
import ListenPage from './pages/ListenPage'

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/listen" element={<ListenPage />} />

        {/* All authenticated routes */}
        <Route element={<RequireAuth />}>

          {/* Full-screen immersive now playing */}
          <Route
            path="/"
            element={<Navigate to="/now-playing" replace />}
          />
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
            element={<Layout><TTSMonitor /></Layout>}
          />
          <Route
            path="/:station/admin"
            element={<Layout><TTSMonitor /></Layout>}
          />

          {/* Library — browse + enrich */}
          <Route
            path="/library"
            element={<Layout><LibraryPage /></Layout>}
          />
          <Route
            path="/media/tracks/:trackId"
            element={<Layout><LibraryPage /></Layout>}
          />

          {/* Analytics */}
          <Route
            path="/analytics"
            element={<Layout><Analytics /></Layout>}
          />

          {/* Profile */}
          <Route path="/profile" element={<Layout><ProfilePage /></Layout>} />

          {/* Admin-only routes */}
          <Route element={<RequireAdmin />}>
            <Route path="/admin/users" element={<Layout><UserManagement /></Layout>} />
            <Route path="/admin/listeners" element={<Layout><ListenerSessions /></Layout>} />
          </Route>

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
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}

export default App
