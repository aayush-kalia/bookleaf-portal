
import { useState, type FormEvent } from 'react'
import { ApiError } from '../../../api/client'
import { useReplyToTicket, useTicket } from '../hooks/useTickets'
import { useQuery } from '@tanstack/react-query'
import { booksApi } from '../../books/api/booksApi'

interface Props {
  ticketId: string
}

function formatLabel(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function TicketConversation({ ticketId }: Props) {
  const { data: ticket, isPending, isError, error } = useTicket(ticketId)
  const { data: booksData } = useQuery({
    queryKey: ['books'],
    queryFn: booksApi.list,
  })

  const relatedBook = ticket?.book_id
    ? booksData?.books.find((book) => book.id === ticket.book_id)
    : undefined
  const [body, setBody] = useState('')
  const reply = useReplyToTicket(ticketId)

  if (isPending) return <div className="ticket-detail-panel">Loading conversation…</div>

  if (isError || !ticket) {
    return (
      <div className="ticket-detail-panel">
        <p className="form-error">
          {error instanceof ApiError ? error.message : 'Unable to load this ticket.'}
        </p>
      </div>
    )
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    reply.mutate(
      { body: body.trim() },
      { onSuccess: () => setBody('') },
    )
  }

  const canReply = ticket.status !== 'closed'

  return (
    <section className="ticket-detail-panel">
      <div className="ticket-detail-header">
        <span className="ticket-code">{ticket.ticket_code}</span>
        <span className={`ticket-status status-${ticket.status}`}>
          {formatLabel(ticket.status)}
        </span>
      </div>

      <h2>{ticket.subject}</h2>
      {ticket.book_id && (
        <p className="ticket-book-title">
          Related book: {relatedBook?.title ?? 'Loading book title…'}
        </p>
      )}
      <p className="muted">
        {formatLabel(ticket.category)} · {formatLabel(ticket.priority)} priority
      </p>

      <div className="ticket-original-description">
        <p>{ticket.description}</p>
      </div>

      <h3 className="conversation-heading">Conversation</h3>

      <div className="message-list">
        {ticket.messages.length === 0 ? (
          <p className="muted">No replies yet.</p>
        ) : (
          ticket.messages.map((message) => (
            <article className="message-card" key={message.id}>
              <div className="message-meta">
                <strong>
                  {message.sender_role === 'admin' ? 'Support team' : 'You'}
                </strong>
                <time dateTime={message.created_at}>
                  {new Date(message.created_at).toLocaleString('en-IN')}
                </time>
              </div>
              <p>{message.body}</p>
            </article>
          ))
        )}
      </div>

      {canReply ? (
        <form className="reply-form" onSubmit={handleSubmit}>
          <label htmlFor="ticket-reply">Your reply</label>
          <textarea
            id="ticket-reply"
            value={body}
            onChange={(event) => setBody(event.target.value)}
            minLength={1}
            maxLength={10000}
            rows={3}
            required
            placeholder="Write your message…"
          />

          {reply.isError && (
            <p className="form-error">
              {reply.error.message || 'Unable to send your reply.'}
            </p>
          )}

          <button type="submit" disabled={reply.isPending || !body.trim()}>
            {reply.isPending ? 'Sending…' : 'Send reply'}
          </button>
        </form>
      ) : (
        <p className="muted">This ticket is closed and can no longer receive replies.</p>
      )}
    </section>
  )
}
