import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export function RequireAdmin() {
  const role = useAuthStore((state) => state.role)

  if (role !== 'admin') {
    return <Navigate to="/now-playing" replace />
  }

  return <Outlet />
}
