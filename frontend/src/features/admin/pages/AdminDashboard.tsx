
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../../../api/client'
import { booksApi } from '../../books/api/booksApi'
import { useQuery } from '@tanstack/react-query'
import { useAdminUsers } from '../hooks/useAdminUsers'
import { ticketsApi } from '../../tickets/api/ticketsApi'
import type {
  TicketCategory,
  TicketPriority,
  TicketStatus,
} from '../../tickets/types'
import {
  useAdminDraft,
  useAdminNotes,
  useAdminTicket,
  useAdminTickets,
  useCreateAdminNote,
  useUpdateAdminTicket,
} from '../hooks/useAdminTickets'

const statuses: TicketStatus[] = ['open', 'in_progress', 'resolved', 'closed']
const priorities: TicketPriority[] = ['critical', 'high', 'medium', 'low']
const categories: TicketCategory[] = [
  'royalty_payments',
  'isbn_metadata',
  'printing_quality',
  'distribution_availability',
  'production_status',
  'general_inquiry',
]

function label(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function displayDate(value: string) {
  return new Date(value).toLocaleString('en-IN')
}

function displayUnknown(value: unknown): string {
  if (typeof value === 'string') return value
  if (value == null) return 'No content available.'
  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>
    for (const key of ['draft', 'body', 'content', 'text', 'message']) {
      if (typeof obj[key] === 'string') return obj[key] as string
    }
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}
function isFallbackDraft(value: unknown): boolean {
  return (
    typeof value === 'object' &&
    value !== null &&
    'ai_available' in value &&
    value.ai_available === false
  )
}
export function AdminDashboard() {
  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const [priority, setPriority] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const filters = useMemo(() => ({
    ...(status ? { status } : {}),
    ...(category ? { category } : {}),
    ...(priority ? { priority } : {}),
  }), [status, category, priority])

  const {
    data,
    isPending,
    isError,
    error,
    refetch,
    isFetching,
  } = useAdminTickets(filters)

  const { data: ticketDetail, isPending: detailPending } =
    useAdminTicket(selectedId)
  const { data: notesData, isPending: notesPending } =
    useAdminNotes(selectedId)
  const { data: draftData, isPending: draftPending, isError: draftError } =
    useAdminDraft(selectedId)

  const { data: booksData } = useQuery({
    queryKey: ['books'],
    queryFn: booksApi.list,
  })
  const {
    data: admins = [],
    isPending: adminsPending,
    isError: adminsError,
  } = useAdminUsers()

  const queryClient = useQueryClient()
  const updateTicket = useUpdateAdminTicket()

  const [editStatus, setEditStatus] = useState<TicketStatus>('open')
  const [editCategory, setEditCategory] =
    useState<TicketCategory>('general_inquiry')
  const [editPriority, setEditPriority] = useState<TicketPriority>('medium')
  const [assignedAdminId, setAssignedAdminId] = useState('')
  const [noteBody, setNoteBody] = useState('')
  const [replyBody, setReplyBody] = useState('')
  const [draftRetryPending, setDraftRetryPending] = useState(false)
  const [draftRetryError, setDraftRetryError] = useState('')

  const replyMutation = useMutation({
    mutationFn: ({ ticketId, body }: { ticketId: string; body: string }) =>
      ticketsApi.reply(ticketId, { body }),
    onSuccess: async (_result, variables) => {
      setReplyBody('')
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['admin', 'ticket', variables.ticketId],
        }),
        queryClient.invalidateQueries({ queryKey: ['admin', 'tickets'] }),
      ])
    },
  })

  const tickets = data?.items ?? []

  // Apply client-side filters as well, so the visible results always match.
  const visibleTickets = tickets.filter((ticket) =>
    (!status || ticket.status === status) &&
    (!category || ticket.category === category) &&
    (!priority || ticket.priority === priority)
  )

  const selectedTicket = visibleTickets.find((ticket) => ticket.id === selectedId)
  const activeTicket = ticketDetail ?? selectedTicket

  useEffect(() => {
    if (!selectedId || !ticketDetail || ticketDetail.id !== selectedId) return

    setEditStatus(ticketDetail.status)
    setEditCategory(ticketDetail.category)
    setEditPriority(ticketDetail.priority)
    setAssignedAdminId(ticketDetail.assigned_admin_id ?? '')
  }, [selectedId, ticketDetail])

  // Keep the selection valid when filters change.
  useEffect(() => {
    if (selectedId && !visibleTickets.some((ticket) => ticket.id === selectedId)) {
      setSelectedId(null)
    }
  }, [selectedId, visibleTickets])

  const notes = Array.isArray(notesData)
    ? notesData
    : notesData && typeof notesData === 'object' &&
        'items' in notesData && Array.isArray((notesData as { items: unknown[] }).items)
      ? (notesData as { items: unknown[] }).items
      : []
  async function handleUseAIDraft() {
    if (!selectedId || draftPending || draftRetryPending) return

    setDraftRetryError('')

    const isFallback =
      typeof draftData === 'object' &&
      draftData !== null &&
      'ai_available' in draftData &&
      draftData.ai_available === false

    if (!isFallback) {
      const text = displayUnknown(draftData)
      if (text) setReplyBody(text)
      return
    }

    setDraftRetryPending(true)

    try {
      const result = await ticketsApi.getDraft(selectedId, true)

      const isAvailable =
        typeof result === 'object' &&
        result !== null &&
        'ai_available' in result &&
        result.ai_available === true

      const text = displayUnknown(result)

      if (isAvailable) {
        setReplyBody(text)
      } else {
        setReplyBody(text)
        setDraftRetryError(
          'AI generation failed again. The fallback response is available.',
        )
      }

      await queryClient.invalidateQueries({
        queryKey: ['admin', 'draft', selectedId],
      })
    } catch {
      setDraftRetryError(
        'Unable to retry AI generation. The existing fallback response is still available.',
      )
    } finally {
      setDraftRetryPending(false)
    }
  }
  function saveChanges(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedId) return

    updateTicket.mutate({
      ticketId: selectedId,
      payload: {
        status: editStatus,
        category: editCategory,
        priority: editPriority,
        assigned_admin_id: assignedAdminId.trim() || null,
      },
    })
  }

  function addInternalNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedId || !noteBody.trim()) return

    // Mutation hook is bound to the selected ticket.
    createNoteMutation.mutate(noteBody.trim(), {
      onSuccess: () => setNoteBody(''),
    })
  }

  const createNoteMutation = useCreateAdminNote(selectedId ?? '')

  function sendReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedId || !replyBody.trim()) return

    replyMutation.mutate({
      ticketId: selectedId,
      body: replyBody.trim(),
    })
  }

  return (
    <main>
      <header className="page-header">
        <div>
          <p className="eyebrow">SUPPORT WORKSPACE</p>
          <h1>Ticket queue</h1>
          <p className="muted">Review, assign and respond to author support tickets.</p>
        </div>
        <button type="button" onClick={() => void refetch()} disabled={isFetching}>
          {isFetching ? 'Refreshing…' : 'Refresh queue'}
        </button>
      </header>

      <section className="admin-filters">
        <select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {statuses.map((item) => <option key={item} value={item}>{label(item)}</option>)}
        </select>

        <select aria-label="Filter by category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((item) => <option key={item} value={item}>{label(item)}</option>)}
        </select>

        <select aria-label="Filter by priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="">All priorities</option>
          {priorities.map((item) => <option key={item} value={item}>{label(item)}</option>)}
        </select>

        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            setStatus('')
            setCategory('')
            setPriority('')
          }}
        >
          Clear filters
        </button>
      </section>

      {updateTicket.isError && (
        <p className="form-error">
          {updateTicket.error instanceof ApiError
            ? updateTicket.error.message
            : 'Unable to save ticket changes.'}
        </p>
      )}
      {updateTicket.isSuccess && (
        <p className="success-message">Ticket changes saved.</p>
      )}

      {isPending ? (
        <p className="muted">Loading ticket queue…</p>
      ) : isError ? (
        <section className="empty-state">
          <p className="form-error">
            {error instanceof Error ? error.message : 'Unable to load tickets.'}
          </p>
          <button type="button" onClick={() => void refetch()}>Retry</button>
        </section>
      ) : (
        <div className="admin-ticket-layout">
          <section className="admin-ticket-list">
            <div className="section-heading">
              <h2>Tickets</h2>
              <span className="muted">{visibleTickets.length} shown</span>
            </div>

            {visibleTickets.length === 0 ? (
              <div className="empty-state">No tickets match these filters.</div>
            ) : visibleTickets.map((ticket) => {
              const book = booksData?.books.find((item) => item.id === ticket.book_id)

              return (
                <button
                  type="button"
                  key={ticket.id}
                  className={`ticket-list-item ${selectedId === ticket.id ? 'selected' : ''}`}
                  onClick={() => setSelectedId(ticket.id)}
                >
                  <div className="ticket-card-header">
                    <span className="ticket-code">{ticket.ticket_code}</span>
                    <span className={`ticket-status status-${ticket.status}`}>
                      {label(ticket.status)}
                    </span>
                  </div>

                  <h3 className="ticket-card-title">{ticket.subject}</h3>

                  {ticket.book_id && (
                    <p className="ticket-book-title">
                      {book?.title ?? 'Loading book...'}
                    </p>
                  )}

                  <div className="ticket-card-footer">
                    <span className="ticket-category">
                      {label(ticket.category)}
                    </span>

                    <span className={`ticket-priority priority-${ticket.priority}`}>
                      <span className="priority-dot" />
                      {label(ticket.priority)}
                    </span>
                  </div>
                </button>

              )
            })}
          </section>

          <section className="admin-ticket-detail">
            {!selectedId ? (
              <div className="ticket-detail-placeholder">
                <h3>Select a ticket</h3>
                <p className="muted">Messages, notes and administrative controls will appear here.</p>
              </div>
            ) : detailPending || !activeTicket ? (
              <p className="muted">Loading ticket details…</p>
            ) : (
              <>
                <div className="ticket-detail-header">
                  <span className="ticket-code">{activeTicket.ticket_code}</span>
                  <span className={`ticket-status status-${activeTicket.status}`}>
                    {label(activeTicket.status)}
                  </span>
                </div>

                <h2>{activeTicket.subject}</h2>
                {activeTicket.book_id && (
                  <p className="ticket-book-title">
                    Related book: {
                      booksData?.books.find((book) => book.id === activeTicket.book_id)?.title
                      ?? 'Unknown book'
                    }
                  </p>
                )}
                <p className="muted">{activeTicket.description}</p>

                <form className="admin-edit-fields" onSubmit={saveChanges}>
                  <h3>Administrative overrides</h3>

                  <label>
                    Status
                    <select value={editStatus} onChange={(e) => setEditStatus(e.target.value as TicketStatus)}>
                      {statuses.map((item) => <option key={item} value={item}>{label(item)}</option>)}
                    </select>
                  </label>

                  <label>
                    Priority
                    <select value={editPriority} onChange={(e) => setEditPriority(e.target.value as TicketPriority)}>
                      {priorities.map((item) => <option key={item} value={item}>{label(item)}</option>)}
                    </select>
                  </label>

                  <label>
                    Category
                    <select value={editCategory} onChange={(e) => setEditCategory(e.target.value as TicketCategory)}>
                      {categories.map((item) => <option key={item} value={item}>{label(item)}</option>)}
                    </select>
                  </label>

                  <label>
                    Assigned admin
                    <select
                      value={assignedAdminId}
                      onChange={(e) => setAssignedAdminId(e.target.value)}
                      disabled={adminsPending}
                    >
                      <option value="">
                        {adminsPending ? 'Loading admins...' : 'Unassigned'}
                      </option>

                      {admins.map((admin) => (
                        <option key={admin.id} value={admin.id}>
                          {admin.name} ({admin.email})
                        </option>
                      ))}
                    </select>
                  </label>

                  {adminsError && (
                    <p className="form-error">Failed to load admin users.</p>
                  )}

                  <button type="submit" disabled={updateTicket.isPending}>
                    {updateTicket.isPending ? 'Saving…' : 'Save changes'}
                  </button>
                </form>

                <section className="admin-content-section">
                  <h3>Conversation</h3>
                  {ticketDetail?.messages?.length ? (
                    <div className="message-list">
                      {ticketDetail.messages.map((message) => (
                        <article className="message-card" key={message.id}>
                          <div className="message-meta">
                            <strong>{message.sender_role === 'admin' ? 'Support team' : 'Author'}</strong>
                            <time dateTime={message.created_at}>{displayDate(message.created_at)}</time>
                          </div>
                          <p>{message.body}</p>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">No messages yet.</p>
                  )}

                 {activeTicket.status !== 'closed' && (
                  <form className="reply-form" onSubmit={sendReply}>
                    <label htmlFor="admin-reply">Reply to author</label>

                    <button
                      type="button"
                      onClick={handleUseAIDraft}
                      disabled={!draftData || draftPending || draftRetryPending}
                    >
                      {draftPending || draftRetryPending
                        ? 'Generating...'
                        : 'Use AI Draft'}
                    </button>
                    {draftRetryError && (
                      <p className="form-error" role="alert">
                        {draftRetryError}
                      </p>
                    )}
                    {isFallbackDraft(draftData) && (
                      <div role="alert" className="ai-fallback-notice">
                        <strong>AI generation failed</strong>
                        <p>
                          AI drafting is currently unavailable. A fallback response
                          is provided below. Review and edit it before sending it
                          to the author.
                        </p>
                      </div>
                    )}
                    <textarea
                      id="admin-reply"
                      value={replyBody}
                      onChange={(e) => setReplyBody(e.target.value)}
                      rows={3}
                      maxLength={10000}
                      required
                    />

                    {replyMutation.isError && (
                      <p className="form-error">
                        {replyMutation.error.message}
                      </p>
                    )}

                    <button
                      type="submit"
                      disabled={replyMutation.isPending || !replyBody.trim()}
                    >
                      {replyMutation.isPending ? 'Sending…' : 'Send reply'}
                    </button>
                  </form>
                )}
                </section>

                <section className="admin-content-section">
                  <h3>Internal notes</h3>
                  <p className="muted">Visible to admins only, not to the author.</p>

                  {notesPending ? (
                    <p className="muted">Loading notes…</p>
                  ) : notes.length === 0 ? (
                    <p className="muted">No internal notes yet.</p>
                  ) : (
                    <div className="message-list">
                      {notes.map((note, index) => (
                        <article className="message-card" key={index}>
                          <p>{displayUnknown(note)}</p>
                        </article>
                      ))}
                    </div>
                  )}

                  <form className="reply-form" onSubmit={addInternalNote}>
                    <label htmlFor="internal-note">Add internal note</label>
                    <textarea
                      id="internal-note"
                      value={noteBody}
                      onChange={(e) => setNoteBody(e.target.value)}
                      rows={3}
                      maxLength={10000}
                      required
                    />
                    {createNoteMutation.isError && (
                      <p className="form-error">{createNoteMutation.error.message}</p>
                    )}
                    <button type="submit" disabled={createNoteMutation.isPending || !noteBody.trim()}>
                      {createNoteMutation.isPending ? 'Saving note…' : 'Add note'}
                    </button>
                  </form>
                </section>
              </>
            )}
          </section>
        </div>
      )}
    </main>
  )
}
