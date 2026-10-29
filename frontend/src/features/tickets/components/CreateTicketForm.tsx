
import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { booksApi } from '../../books/api/booksApi'
import { useCreateTicket } from '../hooks/useTickets'
import type { TicketCategory } from '../types'

interface Props {
  onCreated: (ticketId: string) => void
  onCancel: () => void
}

const categories: { value: TicketCategory; label: string }[] = [
  { value: 'royalty_payments', label: 'Royalty payments' },
  { value: 'isbn_metadata', label: 'ISBN and metadata' },
  { value: 'printing_quality', label: 'Printing quality' },
  { value: 'distribution_availability', label: 'Distribution and availability' },
  { value: 'production_status', label: 'Production status' },
  { value: 'general_inquiry', label: 'General inquiry' },
]

export function CreateTicketForm({ onCreated, onCancel }: Props) {
  const createTicket = useCreateTicket()

  const booksQuery = useQuery({
    queryKey: ['books', 'author-ticket-form'],
    queryFn: booksApi.list,
  })

  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] =
    useState<TicketCategory>('general_inquiry')
  const [bookId, setBookId] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    createTicket.mutate(
      {
        subject: subject.trim(),
        description: description.trim(),
        category,
        book_id: bookId || null,
      },
      {
        onSuccess: (ticket) => onCreated(ticket.id),
      },
    )
  }

  return (
    <form className="ticket-form" onSubmit={handleSubmit}>
      <h2>Create a support ticket</h2>

      <label htmlFor="ticket-subject">Subject</label>
      <input
        id="ticket-subject"
        value={subject}
        onChange={(event) => setSubject(event.target.value)}
        minLength={5}
        maxLength={200}
        required
        placeholder="Briefly describe the issue"
      />

      <label htmlFor="ticket-book">Related book</label>
      <select
        id="ticket-book"
        value={bookId}
        onChange={(event) => setBookId(event.target.value)}
        disabled={booksQuery.isPending || booksQuery.isError}
      >
        <option value="">
          {booksQuery.isPending
            ? 'Loading your books…'
            : booksQuery.isError
              ? 'Could not load books'
              : 'Not related to a specific book'}
        </option>

        {booksQuery.data?.books.map((book) => (
          <option key={book.id} value={book.id}>
            {book.title}
          </option>
        ))}
      </select>

      {booksQuery.isError && (
        <p className="form-error">
          Unable to load your books. Refresh the page and try again.
        </p>
      )}

      <label htmlFor="ticket-category">Category</label>
      <select
        id="ticket-category"
        value={category}
        onChange={(event) =>
          setCategory(event.target.value as TicketCategory)
        }
        required
      >
        {categories.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>

      <label htmlFor="ticket-description">Description</label>
      <textarea
        id="ticket-description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        minLength={10}
        maxLength={10000}
        rows={5}
        required
        placeholder="Explain the issue and include relevant details"
      />

      {createTicket.isError && (
        <p className="form-error">
          {createTicket.error.message || 'Unable to create ticket.'}
        </p>
      )}

      <div className="ticket-form-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={onCancel}
        >
          Cancel
        </button>

        <button
          type="submit"
          disabled={
            createTicket.isPending ||
            booksQuery.isPending ||
            booksQuery.isError
          }
        >
          {createTicket.isPending ? 'Creating…' : 'Submit ticket'}
        </button>
      </div>
    </form>
  )
}
