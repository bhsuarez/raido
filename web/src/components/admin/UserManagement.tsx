import { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '../../store/authStore';
import { apiHelpers } from '../../utils/api';

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

function CreateUserForm({ onCreated }: { onCreated: () => void }) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('listener');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setLoading(true);
    try {
      await apiHelpers.createUser({ email, password, role, full_name: name || 'Listener' });
      setEmail('');
      setName('');
      setPassword('');
      setRole('listener');
      setSuccess(true);
      onCreated();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Create User</h3>
      {error && <div className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-xl px-3 py-2">{error}</div>}
      {success && <div className="text-green-400 text-sm bg-green-900/20 border border-green-800 rounded-xl px-3 py-2">User created successfully.</div>}
      <div className="flex gap-2 flex-wrap">
        <input
          className="input flex-1 min-w-40"
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
        <input
          className="input flex-1 min-w-40"
          type="text"
          placeholder="Name (optional)"
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <input
          className="input flex-1 min-w-40"
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
        />
        <select
          className="input"
          value={role}
          onChange={e => setRole(e.target.value)}
        >
          <option value="listener">Listener</option>
          <option value="admin">Admin</option>
        </select>
        <button className="btn-primary" type="submit" disabled={loading}>
          {loading ? 'Creating...' : 'Create'}
        </button>
      </div>
    </form>
  );
}

export function UserManagement() {
  const token = useAuthStore(state => state.token) || '';
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    try {
      const res = await apiHelpers.getUsers();
      setUsers(res.data);
      setError(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error loading users');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const doAction = async (url: string, method = 'POST') => {
    setActionError(null);
    try {
      const response = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setActionError(data.detail || `Action failed (${response.status})`);
        return;
      }
      fetchUsers();
    } catch {
      setActionError('Network error');
    }
  };

  const pending = users.filter(u => !u.is_active && !u.is_verified);
  const active = users.filter(u => u.is_active);
  const suspended = users.filter(u => !u.is_active && u.is_verified);

  if (loading) {
    return (
      <div className="card p-8 text-gray-400 flex items-center gap-3">
        <div className="spinner w-5 h-5" />
        Loading users...
      </div>
    );
  }

  if (error) {
    return <div className="card p-8 text-red-400">{error}</div>;
  }

  return (
    <div className="space-y-6 p-6">
      <h2 className="text-2xl font-bold text-white">User Management</h2>

      {actionError && (
        <div className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-xl px-4 py-3">
          {actionError}
        </div>
      )}

      {/* Pending Approval */}
      {pending.length > 0 && (
        <section className="card p-6 space-y-4">
          <h3 className="text-base font-semibold text-yellow-400">
            Pending Approval ({pending.length})
          </h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-left">
                <th className="pb-2 font-medium">Email</th>
                <th className="pb-2 font-medium">Name</th>
                <th className="pb-2 font-medium">Registered</th>
                <th className="pb-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {pending.map(u => (
                <tr key={u.id} className="border-t border-gray-800">
                  <td className="py-2.5 text-white">{u.email}</td>
                  <td className="py-2.5 text-gray-300">{u.full_name}</td>
                  <td className="py-2.5 text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="py-2.5">
                    <button
                      className="btn-primary text-xs px-3 py-1.5"
                      onClick={() => doAction(`/api/v1/admin/users/${u.id}/approve`)}
                    >
                      Approve
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Active Users */}
      <section className="card p-6 space-y-4">
        <h3 className="text-base font-semibold text-green-400">
          Active Users ({active.length})
        </h3>
        {active.length === 0 ? (
          <p className="text-gray-500 text-sm">No active users.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-left">
                <th className="pb-2 font-medium">Email</th>
                <th className="pb-2 font-medium">Role</th>
                <th className="pb-2 font-medium">Since</th>
                <th className="pb-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {active.map(u => (
                <tr key={u.id} className="border-t border-gray-800">
                  <td className="py-2.5 text-white">{u.email}</td>
                  <td className="py-2.5 text-gray-300 capitalize">{u.role}</td>
                  <td className="py-2.5 text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="py-2.5">
                    <button
                      className="text-xs px-3 py-1.5 rounded-xl font-medium transition-colors text-red-400 hover:text-red-300 hover:bg-red-900/20"
                      onClick={() => doAction(`/api/v1/admin/users/${u.id}/suspend`)}
                    >
                      Suspend
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Suspended Users */}
      {suspended.length > 0 && (
        <section className="card p-6 space-y-4">
          <h3 className="text-base font-semibold text-red-400">
            Suspended ({suspended.length})
          </h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-left">
                <th className="pb-2 font-medium">Email</th>
                <th className="pb-2 font-medium">Role</th>
                <th className="pb-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {suspended.map(u => (
                <tr key={u.id} className="border-t border-gray-800">
                  <td className="py-2.5 text-white">{u.email}</td>
                  <td className="py-2.5 text-gray-300 capitalize">{u.role}</td>
                  <td className="py-2.5">
                    <button
                      className="btn-primary text-xs px-3 py-1.5"
                      onClick={() => doAction(`/api/v1/admin/users/${u.id}/approve`)}
                    >
                      Reactivate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Create User Form */}
      <section className="card p-6 border-t border-gray-700">
        <CreateUserForm onCreated={fetchUsers} />
      </section>
    </div>
  );
}
