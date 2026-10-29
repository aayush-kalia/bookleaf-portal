import { Navigate, Outlet } from 'react-router-dom'
import type { UserRole } from '../../features/auth/types'
import { useCurrentUser } from '../../features/auth/hooks/useCurrentUser'

export function ProtectedRoute({ allowedRoles }: { allowedRoles?: UserRole[] }) {
  const { data: user, isPending, isError } = useCurrentUser()

  if (isPending) {
    return <main className="page-loading">Loading your session</main>
  }

  if (isError || !user) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={user.role === 'admin' ? '/admin' : '/author'} replace />
  }

  return <Outlet />
}
