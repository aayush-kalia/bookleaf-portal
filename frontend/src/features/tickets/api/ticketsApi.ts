
import { apiRequest } from '../../../api/client'
import type {
  CreateMessagePayload,
  CreateTicketPayload,
  TicketDetail,
  TicketListResponse,
} from '../types'

export interface TicketFilters {
  page?: number
  page_size?: number
  status?: string
  category?: string
  priority?: string
}

export const ticketsApi = {
  list: (filters: TicketFilters = {}) => {
    const params = new URLSearchParams()

    if (filters.page) params.set('page', String(filters.page))
    if (filters.page_size) params.set('page_size', String(filters.page_size))
    if (filters.status) params.set('status', filters.status)
    if (filters.category) params.set('category', filters.category)
    if (filters.priority) params.set('priority', filters.priority)

    const query = params.toString()

    return apiRequest<TicketListResponse>(
      `/tickets${query ? `?${query}` : ''}`,
    )
  },
  update: (
    ticketId: string,
    payload: {
      status?: string
      category?: string
      priority?: string
      assigned_admin_id?: string | null
    },
  ) =>
    apiRequest<TicketDetail>(`/tickets/${ticketId}`, {
      method: 'PATCH',
      body: payload,
    }),

  getById: (ticketId: string) =>
    apiRequest<TicketDetail>(`/tickets/${ticketId}`),

  create: (payload: CreateTicketPayload) =>
    apiRequest<TicketDetail>('/tickets', {
      method: 'POST',
      body: payload,
    }),

  reply: (ticketId: string, payload: CreateMessagePayload) =>
    apiRequest<TicketMessageResponse>(
      `/tickets/${ticketId}/messages`,
      {
        method: 'POST',
        body: payload,
      },
    ),
    
  getNotes: (ticketId: string) =>
    apiRequest<unknown>(`/tickets/${ticketId}/notes`),

  createNote: (ticketId: string, body: string) =>
    apiRequest<unknown>(`/tickets/${ticketId}/notes`, {
      method: 'POST',
      body: { body },
    }),

  getDraft: (ticketId: string, forceRegenerate = false) =>
    apiRequest<unknown>(
      `/tickets/${ticketId}/draft${
        forceRegenerate ? '?force_regenerate=true' : ''
      }`,
    ),

}


interface TicketMessageResponse {
  id: string
  sender_user_id: string
  sender_role: string
  body: string
  used_ai_draft: boolean
  created_at: string
}
