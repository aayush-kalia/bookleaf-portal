import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <main className="login-page">
      <section className="login-card">
        <p className="eyebrow">404 — PAGE NOT FOUND</p>
        <h1>Nothing here.</h1>
        <p className="muted">
          The page you're looking for doesn't exist or may have moved.
        </p>
        <Link to="/login">
          <button type="button">Back to sign in</button>
        </Link>
      </section>
    </main>
  )
}