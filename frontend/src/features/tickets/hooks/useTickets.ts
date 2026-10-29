
import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { ticketsApi } from '../api/ticketsApi'
import type {
  CreateMessagePayload,
  CreateTicketPayload,
} from '../types'

export const ticketsQueryKey = ['tickets']

export function useTickets() {
  return useQuery({
    queryKey: ticketsQueryKey,
    queryFn: () => ticketsApi.list({ page: 1, page_size: 50 }),
  })
}

export function useTicket(ticketId: string | null) {
  return useQuery({
    queryKey: [...ticketsQueryKey, ticketId],
    queryFn: () => ticketsApi.getById(ticketId!),
    enabled: Boolean(ticketId),
    refetchInterval: 2000,
  })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateTicketPayload) =>
      ticketsApi.create(payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ticketsQueryKey }),
  })
}

export function useReplyToTicket(ticketId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateMessagePayload) =>
      ticketsApi.reply(ticketId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: [...ticketsQueryKey, ticketId],
        }),
        queryClient.invalidateQueries({ queryKey: ticketsQueryKey }),
      ])
    },
  })
}
