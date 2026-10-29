import { useEffect, useState } from 'react'
import './App.css'

type User = {
  id: string
  email: string
  name: string
  role: 'author' | 'admin'
}

type Book = {
  id: string
  author_id: string
  title: string
  isbn: string | null
  genre: string | null
  status: string
  stage: string | null
  mrp: number | string | null
  royalty_per_copy: number | string | null
  copies_sold: number
  royalty_earned: number | string
  royalty_paid: number | string
  royalty_pending: number | string
  available_on: string[] | null
}

type BookList = {
  books: Book[]
  royalty_summary: {
    total_earned: number
    total_paid: number
    total_pending: number
    below_threshold: boolean
  }
}

const API = import.meta.env.VITE_API_URL || '/api/v1'

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function getCookie(name: string): string | null {
  const prefix = `${name}=`
  const item = document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith(prefix))

  return item ? decodeURIComponent(item.slice(prefix.length)) : null
}

function money(value: number | string | null | undefined): string {
  if (value == null) return '—'

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(Number(value))
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [email, setEmail] = useState('priya.sharma@email.com')
  const [password, setPassword] = useState('Author@123')
  const [books, setBooks] = useState<Book[]>([])
  const [summary, setSummary] = useState<BookList['royalty_summary'] | null>(
    null,
  )
  const [selectedBook, setSelectedBook] = useState<Book | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function loadSession() {
    try {
      const currentUser = await request<User>('/auth/me')
      setUser(currentUser)
      await loadBooks()
    } catch {
      setUser(null)
    }
  }

  async function loadBooks() {
    setError('')
    try {
      const result = await request<BookList>('/books')
      setBooks(result.books)
      setSummary(result.royalty_summary)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load books')
    }
  }

  useEffect(() => {
    void loadSession()
  }, [])

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')

    try {
      await request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })

      const currentUser = await request<User>('/auth/me')
      setUser(currentUser)
      await loadBooks()
      setMessage(`Logged in as ${currentUser.role}.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

async function handleLogout() {
  setError('')

  try {
    const csrfToken = getCookie('csrf_token')

    if (!csrfToken) {
      throw new Error(
        'CSRF cookie missing. Please log out and log in again.',
      )
    }

    await request('/auth/logout', {
      method: 'POST',
      headers: {
        'X-CSRF-Token': csrfToken,
      },
    })

    setUser(null)
    setBooks([])
    setSummary(null)
    setSelectedBook(null)
    setMessage('Logged out successfully.')
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Logout failed')
  }
}

  async function openBook(bookId: string) {
    setError('')
    try {
      const book = await request<Book>(
        `/books/${encodeURIComponent(bookId)}`,
      )
      setSelectedBook(book)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load book')
    }
  }

  return (
    <main className="container">
      <header className="topbar">
        <div>
          <p className="eyebrow">BOOKLEAF PUBLISHING</p>
          <h1>Author Portal</h1>
        </div>
        {user && (
          <div className="user-box">
            <span>{user.name}</span>
            <span className="role">{user.role}</span>
            <button className="secondary" onClick={handleLogout}>
              Logout
            </button>
          </div>
        )}
      </header>

      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}

      {!user ? (
        <section className="panel login-panel">
          <h2>Sign in</h2>
          <p className="muted">
            Use a seeded author or admin account to test authentication.
          </p>

          <form onSubmit={handleLogin}>
            <label htmlFor="email">Email</label>
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

            <button type="submit" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="muted small">
            Demo author: priya.sharma@email.com / Author@123
          </p>
          <p className="muted small">
            Demo admin: admin1@bookleaf.test / Admin@123
          </p>
        </section>
      ) : (
        <>
          <section className="welcome">
            <div>
              <p className="eyebrow">SIGNED IN AS</p>
              <h2>{user.name}</h2>
              <p className="muted">{user.email}</p>
            </div>
            <button onClick={() => void loadBooks()}>Refresh books</button>
          </section>

          {summary && (
            <section className="summary-grid">
              <SummaryCard label="Total earned" value={money(summary.total_earned)} />
              <SummaryCard label="Total paid" value={money(summary.total_paid)} />
              <SummaryCard label="Total pending" value={money(summary.total_pending)} />
              <SummaryCard
                label="Payout threshold"
                value={summary.below_threshold ? 'Below ₹1,000' : 'Reached'}
              />
            </section>
          )}

          <section className="panel">
            <div className="section-heading">
              <div>
                <h2>{user.role === 'admin' ? 'All Books' : 'My Books'}</h2>
                <p className="muted">{books.length} books returned by the API</p>
              </div>
            </div>

            {books.length === 0 ? (
              <p className="muted">No books found.</p>
            ) : (
              <div className="book-list">
                {books.map((book) => (
                  <article className="book-row" key={book.id}>
                    <div className="book-info">
                      <h3>{book.title}</h3>
                      <p className="muted">
                        {book.id} · {book.genre ?? 'Genre unavailable'}
                      </p>
                      <span
                        className={
                          book.status === 'Published & Live'
                            ? 'status published'
                            : 'status production'
                        }
                      >
                        {book.status}
                      </span>
                      {book.stage && book.stage !== 'Published & Live' && (
                        <p className="muted">Stage: {book.stage}</p>
                      )}
                    </div>

                    <div className="book-stats">
                      <span className="muted small">Royalty pending</span>
                      <strong>
                        {book.status === 'Published & Live'
                          ? money(book.royalty_pending)
                          : 'Available after publication'}
                      </strong>
                      <button
                        className="secondary"
                        onClick={() => void openBook(book.id)}
                      >
                        View details
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          {selectedBook && (
            <section className="panel detail-panel">
              <div className="section-heading">
                <h2>{selectedBook.title}</h2>
                <button
                  className="secondary"
                  onClick={() => setSelectedBook(null)}
                >
                  Close
                </button>
              </div>
              <p><strong>Book ID:</strong> {selectedBook.id}</p>
              <p><strong>Author ID:</strong> {selectedBook.author_id}</p>
              <p><strong>ISBN:</strong> {selectedBook.isbn ?? '—'}</p>
              <p><strong>Status:</strong> {selectedBook.status}</p>
              <p><strong>Stage:</strong> {selectedBook.stage ?? '—'}</p>
              <p><strong>MRP:</strong> {money(selectedBook.mrp)}</p>
              <p>
                <strong>Royalty per copy:</strong>{' '}
                {selectedBook.status === 'Published & Live'
                  ? money(selectedBook.royalty_per_copy)
                  : 'Available after publication'}
              </p>
              <p><strong>Copies sold:</strong> {selectedBook.copies_sold}</p>
              <p>
                <strong>Royalty earned:</strong>{' '}
                {selectedBook.status === 'Published & Live'
                  ? money(selectedBook.royalty_earned)
                  : 'Available after publication'}
              </p>
              <p><strong>Royalty paid:</strong> {money(selectedBook.royalty_paid)}</p>
              <p>
                <strong>Available on:</strong>{' '}
                {selectedBook.available_on?.join(', ') ?? '—'}
              </p>
            </section>
          )}
        </>
      )}
    </main>
  )
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="panel summary-card">
      <p className="muted">{label}</p>
      <strong>{value}</strong>
    </article>
  )
}