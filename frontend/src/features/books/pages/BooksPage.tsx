
import { ApiError } from '../../../api/client'
import { BookCard } from '../components/BookCard'
import { RoyaltySummary } from '../components/RoyaltySummary'
import { useBooks } from '../components/hooks/useBooks'

export function BooksPage() {
  const { data, isPending, isError, error, refetch, isFetching } = useBooks()

  if (isPending) {
    return <main className="page-container">Loading your books…</main>
  }

  if (isError) {
    const message =
      error instanceof ApiError
        ? error.message
        : 'Unable to load your books. Please try again.'

    return (
      <main className="page-container">
        <h1>Your books</h1>
        <p className="form-error">{message}</p>
        <button type="button" onClick={() => void refetch()}>
          Retry
        </button>
      </main>
    )
  }

  return (
    <main className="page-container">
      <header className="page-header">
        <div>
          <p className="eyebrow">AUTHOR PORTAL</p>
          <h1>Your books</h1>
          <p className="muted">
            Track your publications and royalty earnings.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
        >
          {isFetching ? 'Refreshing…' : 'Refresh'}
        </button>
      </header>

      <RoyaltySummary summary={data.royalty_summary} />

      <section className="books-section">
        <div className="section-heading">
          <h2>Your publications</h2>
          <span className="muted">{data.books.length} books</span>
        </div>

        {data.books.length === 0 ? (
          <div className="empty-state">
            <h3>No books found</h3>
            <p className="muted">
              Your publications will appear here when available.
            </p>
          </div>
        ) : (
          <div className="books-grid">
            {data.books.map((book) => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
