
import type { Book } from '../types'

interface Props {
  book: Book
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value)
}

function formatLabel(value: string | null | undefined) {
  if (!value) return 'Not specified'

  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export function BookCard({ book }: Props) {
  return (
    <article className="book-card">
      <div className="book-card-header">
        <div>
          <h3>{book.title}</h3>
          <p className="muted">{book.genre || 'Genre not specified'}</p>
        </div>

        <span className="status-badge">{formatLabel(book.status)}</span>
      </div>

      <div className="book-stage">
        <span className="muted">Publishing stage</span>
        <strong>{formatLabel(book.stage)}</strong>
      </div>

      <div className="book-metrics">
        <div>
          <span className="muted">Copies sold</span>
          <strong>{book.copies_sold.toLocaleString('en-IN')}</strong>
        </div>

        <div>
          <span className="muted">Earned</span>
          <strong>{formatCurrency(book.royalty_earned)}</strong>
        </div>

        <div>
          <span className="muted">Pending</span>
          <strong>{formatCurrency(book.royalty_pending)}</strong>
        </div>
      </div>

      {book.available_on && (
        <p className="muted">
          Available on: {book.available_on}
        </p>
      )}
    </article>
  )
}
