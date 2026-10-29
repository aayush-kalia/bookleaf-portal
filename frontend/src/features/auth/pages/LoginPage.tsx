import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../../../api/client'
import { authApi } from '../api/authApi'
import { currentUserKey, useCurrentUser } from '../hooks/useCurrentUser'

export function LoginPage() {
  const queryClient = useQueryClient()
  const { data: user, isPending } = useCurrentUser()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const login = useMutation({
    mutationFn: () => authApi.login(email.trim(), password),
    onSuccess: (loggedInUser) => {
      queryClient.setQueryData(currentUserKey, loggedInUser)
    },
  })

  if (isPending) return <main className="page-loading">Loading</main>

  if (user) {
    return <Navigate to={user.role === 'admin' ? '/admin' : '/author'} replace />
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    login.mutate()
  }

  const errorMessage =
    login.error instanceof ApiError
      ? login.error.message
      : login.error instanceof Error
        ? login.error.message
        : null

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="brand-mark">B</div>
        <p className="eyebrow">BOOKLEAF PUBLISHING</p>
        <h1>Welcome back</h1>
        <p className="muted">Sign in to manage your publishing support.</p>

        <form onSubmit={handleSubmit} className="form-stack">
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <button type="submit" disabled={login.isPending}>
            {login.isPending ? 'Signing in' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}
