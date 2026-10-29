
import { useQuery } from '@tanstack/react-query'
import { booksApi } from '../../books/api/booksApi'
import type { Ticket } from '../types'

interface Props {
  tickets: Ticket[]
  selectedId: string | null
  onSelect: (id: string) => void
}

function formatLabel(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function TicketList({ tickets, selectedId, onSelect }: Props) {
  const { data: booksData } = useQuery({
    queryKey: ['books'],
    queryFn: booksApi.list,
  })

  const bookTitles = new Map(
    (booksData?.books ?? []).map((book) => [book.id, book.title]),
  )

  if (tickets.length === 0) {
    return (
      <div className="empty-state">
        <h3>No support tickets yet</h3>
        <p className="muted">
          Create a ticket if you need help with a publication.
        </p>
      </div>
    )
  }

  return (
    <div className="ticket-list">
      {tickets.map((ticket) => (
        <button
          type="button"
          key={ticket.id}
          className={`ticket-list-item ${selectedId === ticket.id ? 'selected' : ''}`}
          onClick={() => onSelect(ticket.id)}
        >
          <div className="ticket-list-top">
            <span className="ticket-code">{ticket.ticket_code}</span>
            <span className={`ticket-status status-${ticket.status}`}>
              {formatLabel(ticket.status)}
            </span>
          </div>

          <h3>{ticket.subject}</h3>

          {ticket.book_id && (
            <p className="ticket-book-title">
              Book: {bookTitles.get(ticket.book_id) ?? 'Loading book title…'}
            </p>
          )}

          <div className="ticket-list-bottom">
            <span>{formatLabel(ticket.category)}</span>
            <span>{formatDate(ticket.created_at)}</span>
          </div>
        </button>
      ))}
    </div>
  )
}
