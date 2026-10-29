import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi } from '../features/auth/api/authApi'
import { currentUserKey, useCurrentUser } from '../features/auth/hooks/useCurrentUser'

export function AuthorLayout() {
  const { data: user } = useCurrentUser()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const logout = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.setQueryData(currentUserKey, null)
      navigate('/login', { replace: true })
    },
  })

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/author">Bookleaf</Link>
        <nav>
          <NavLink to="/author/books">My books</NavLink>
          <NavLink to="/author/tickets">Support tickets</NavLink>
        </nav>
        <div className="topbar-user">
          <span>{user?.name}</span>
          <button className="button-secondary" onClick={() => logout.mutate()} disabled={logout.isPending}>
            {logout.isPending ? 'Signing out' : 'Sign out'}
          </button>
        </div>
      </header>
      <main className="page-container"><Outlet /></main>
    </div>
  )
}
