
import { useState } from 'react'
import { ApiError } from '../../../api/client'
import { CreateTicketForm } from '../components/CreateTicketForm'
import { TicketConversation } from '../components/TicketConversation'
import { TicketList } from '../components/CreateTicketList'
import { useTickets } from '../hooks/useTickets'

export function TicketsPage() {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data, isPending, isError, error, refetch, isFetching } = useTickets()

  function handleCreated(ticketId: string) {
    setShowCreateForm(false)
    setSelectedId(ticketId)
    void refetch()
  }

  return (
    <main className="page-container">
      <header className="page-header">
        <div>
          <p className="eyebrow">AUTHOR WORKSPACE</p>
          <h1>Support tickets</h1>
          <p className="muted">
            Create tickets and follow up on your support requests.
          </p>
        </div>

        <button type="button" onClick={() => setShowCreateForm((value) => !value)}>
          {showCreateForm ? 'Cancel' : '+ New ticket'}
        </button>
      </header>

      {showCreateForm && (
        <div className="ticket-create-panel">
          <CreateTicketForm
            onCreated={handleCreated}
            onCancel={() => setShowCreateForm(false)}
          />
        </div>
      )}

      {isPending ? (
        <p className="muted">Loading tickets…</p>
      ) : isError ? (
        <section className="empty-state">
          <p className="form-error">
            {error instanceof ApiError ? error.message : 'Unable to load tickets.'}
          </p>
          <button type="button" onClick={() => void refetch()}>
            Retry
          </button>
        </section>
      ) : (
        <>
          <div className="section-heading">
            <h2>Your requests</h2>
            <button
              type="button"
              className="text-button"
              onClick={() => void refetch()}
              disabled={isFetching}
            >
              {isFetching ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>

          <div className="tickets-workspace">
            <TicketList
              tickets={data.items}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />

            {selectedId ? (
              <TicketConversation ticketId={selectedId} />
            ) : (
              <div className="ticket-detail-placeholder">
                <h3>Select a ticket</h3>
                <p className="muted">
                  Choose a ticket from the list to view its conversation.
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </main>
  )
}
