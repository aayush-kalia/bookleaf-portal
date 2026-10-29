
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ticketsApi } from '../../tickets/api/ticketsApi'
import type { TicketFilters } from '../../tickets/api/ticketsApi'


export function useAdminTickets(filters: TicketFilters) {
  return useQuery({
    queryKey: ['admin', 'tickets', filters],
    queryFn: () =>
      ticketsApi.list({
        page: 1,
        page_size: 100,
        ...filters,
      }),
  })
}

export function useAdminTicket(ticketId: string | null) {
  return useQuery({
    queryKey: ['admin', 'ticket', ticketId],
    queryFn: () => ticketsApi.getById(ticketId!),
    enabled: Boolean(ticketId),
  })
}

export function useAdminNotes(ticketId: string | null) {
  return useQuery({
    queryKey: ['admin', 'notes', ticketId],
    queryFn: () => ticketsApi.getNotes(ticketId!),
    enabled: Boolean(ticketId),
  })
}

export function useAdminDraft(ticketId: string | null) {
  return useQuery({
    queryKey: ['admin', 'draft', ticketId],
    queryFn: () => ticketsApi.getDraft(ticketId!),
    enabled: Boolean(ticketId),
    retry: false,
  })
}

export function useCreateAdminNote(ticketId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: string) => ticketsApi.createNote(ticketId, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['admin', 'notes', ticketId],
      })
    },
  })
}

export function useUpdateAdminTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      ticketId,
      payload,
    }: {
      ticketId: string
      payload: {
        status?: string
        category?: string
        priority?: string
        assigned_admin_id?: string | null
      }
    }) => ticketsApi.update(ticketId, payload),

    onSuccess: async (_data, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin', 'tickets'] }),
        queryClient.invalidateQueries({
          queryKey: ['admin', 'ticket', variables.ticketId],
        }),
        queryClient.invalidateQueries({ queryKey: ['tickets'] }),
      ])
    },
  })
}
