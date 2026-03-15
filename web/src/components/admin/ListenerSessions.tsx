import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '../../store/authStore';

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatRelative(dt: string | null): string {
  if (!dt) return '—';
  const date = new Date(dt);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return date.toLocaleDateString();
}

interface ActiveSession {
  session_id: number;
  user_id: number;
  email: string;
  station: string;
  city: string | null;
  country: string | null;
  country_code: string | null;
  device_type: string | null;
  browser: string | null;
  started_at: string;
  duration_seconds: number;
}

interface SummaryRow {
  user_id: number;
  email: string;
  total_sessions: number;
  total_duration_seconds: number;
  last_seen_at: string | null;
}

interface SessionRow {
  session_id: number;
  email: string;
  city: string | null;
  country: string | null;
  device_type: string | null;
  browser: string | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
}

export function ListenerSessions() {
  const token = useAuthStore(state => state.token) || '';
  const [active, setActive] = useState<ActiveSession[]>([]);
  const [summary, setSummary] = useState<SummaryRow[]>([]);
  const [history, setHistory] = useState<SessionRow[]>([]);
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'active' | 'summary' | 'history'>('active');

  const fetchActive = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/admin/listeners/active', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setActive(await res.json());
    } catch {}
  }, [token]);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/admin/listeners/summary', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setSummary(await res.json());
    } catch {}
  }, [token]);

  const fetchHistory = useCallback(async () => {
    const params = new URLSearchParams({ limit: '50' });
    if (fromDt) params.set('from_dt', new Date(fromDt).toISOString());
    if (toDt) params.set('to_dt', new Date(toDt).toISOString());
    try {
      const res = await fetch(`/api/v1/admin/listeners/sessions?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setHistory(await res.json());
    } catch {}
  }, [token, fromDt, toDt]);

  useEffect(() => {
    Promise.all([fetchActive(), fetchSummary(), fetchHistory()]).finally(() => setLoading(false));
    const interval = setInterval(fetchActive, 30000);
    return () => clearInterval(interval);
  }, [fetchActive, fetchSummary, fetchHistory]);

  if (loading) {
    return (
      <div className="card p-8 text-gray-400 flex items-center gap-3">
        <div className="spinner w-5 h-5" />
        Loading...
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <h2 className="text-2xl font-bold text-white">Listener Analytics</h2>

      {/* Tab buttons */}
      <div className="flex gap-2">
        {(['active', 'summary', 'history'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              tab === t
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {t === 'active' ? `Active (${active.length})` : t === 'summary' ? 'Per User' : 'History'}
          </button>
        ))}
      </div>

      {tab === 'active' && (
        <section className="card p-6 space-y-4">
          <p className="text-gray-400 text-sm">Auto-refreshes every 30 seconds</p>
          {active.length === 0 ? (
            <p className="text-gray-500 text-sm">No active listeners</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 text-left">
                  <th className="pb-2 font-medium">Email</th>
                  <th className="pb-2 font-medium">Location</th>
                  <th className="pb-2 font-medium">Device</th>
                  <th className="pb-2 font-medium">Browser</th>
                  <th className="pb-2 font-medium">Since</th>
                  <th className="pb-2 font-medium">Duration</th>
                </tr>
              </thead>
              <tbody>
                {active.map(s => (
                  <tr key={s.session_id} className="border-t border-gray-800">
                    <td className="py-2.5 text-white">{s.email}</td>
                    <td className="py-2.5 text-gray-300">
                      {[s.city, s.country].filter(Boolean).join(', ') || '—'}
                    </td>
                    <td className="py-2.5 text-gray-300">{s.device_type || '—'}</td>
                    <td className="py-2.5 text-gray-300">{s.browser || '—'}</td>
                    <td className="py-2.5 text-gray-400">{formatRelative(s.started_at)}</td>
                    <td className="py-2.5 text-gray-400">{formatDuration(s.duration_seconds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {tab === 'summary' && (
        <section className="card p-6 space-y-4">
          <h3 className="text-base font-semibold text-gray-200">Per-User Summary</h3>
          {summary.length === 0 ? (
            <p className="text-gray-500 text-sm">No data available</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 text-left">
                  <th className="pb-2 font-medium">Email</th>
                  <th className="pb-2 font-medium">Sessions</th>
                  <th className="pb-2 font-medium">Total Time</th>
                  <th className="pb-2 font-medium">Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {summary.map(s => (
                  <tr key={s.user_id} className="border-t border-gray-800">
                    <td className="py-2.5 text-white">{s.email}</td>
                    <td className="py-2.5 text-gray-300">{s.total_sessions}</td>
                    <td className="py-2.5 text-gray-300">{formatDuration(s.total_duration_seconds)}</td>
                    <td className="py-2.5 text-gray-400">
                      {s.last_seen_at ? formatRelative(s.last_seen_at) : 'Never'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {tab === 'history' && (
        <section className="card p-6 space-y-4">
          <div className="flex gap-3 items-end flex-wrap">
            <div>
              <label className="text-gray-400 text-xs block mb-1">From</label>
              <input
                type="datetime-local"
                className="input text-sm"
                value={fromDt}
                onChange={e => setFromDt(e.target.value)}
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs block mb-1">To</label>
              <input
                type="datetime-local"
                className="input text-sm"
                value={toDt}
                onChange={e => setToDt(e.target.value)}
              />
            </div>
            <button className="btn-primary px-4 py-2 rounded-xl text-sm" onClick={fetchHistory}>
              Apply
            </button>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-left">
                <th className="pb-2 font-medium">Email</th>
                <th className="pb-2 font-medium">Location</th>
                <th className="pb-2 font-medium">Device</th>
                <th className="pb-2 font-medium">Started</th>
                <th className="pb-2 font-medium">Duration</th>
              </tr>
            </thead>
            <tbody>
              {history.map(s => (
                <tr key={s.session_id} className="border-t border-gray-800">
                  <td className="py-2.5 text-white">{s.email}</td>
                  <td className="py-2.5 text-gray-300">
                    {[s.city, s.country].filter(Boolean).join(', ') || '—'}
                  </td>
                  <td className="py-2.5 text-gray-300">{s.device_type || '—'}</td>
                  <td className="py-2.5 text-gray-400">{new Date(s.started_at).toLocaleString()}</td>
                  <td className="py-2.5 text-gray-400">{formatDuration(s.duration_seconds)}</td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-4 text-gray-500 text-center text-sm">
                    No sessions found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
