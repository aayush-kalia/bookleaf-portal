
export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'

export type TicketCategory =
  | 'royalty_payments'
  | 'isbn_metadata'
  | 'printing_quality'
  | 'distribution_availability'
  | 'production_status'
  | 'general_inquiry'

export type TicketPriority = 'critical' | 'high' | 'medium' | 'low'

export interface Ticket {
  id: string
  ticket_code: string
  author_id: string
  book_id: string | null
  subject: string
  description: string
  status: TicketStatus
  category: TicketCategory
  priority: TicketPriority
  classification_source: string
  ai_status: string
  ai_category: string | null
  ai_priority: string | null
  ai_reason: string | null
  assigned_admin_id: string | null
  last_author_message_at: string | null
  created_at: string
  updated_at: string
  resolved_at: string | null
  closed_at: string | null
}

export interface TicketMessage {
  id: string
  sender_user_id: string
  sender_role: string
  body: string
  used_ai_draft: boolean
  created_at: string
}

export interface TicketDetail extends Ticket {
  messages: TicketMessage[]
  events: unknown[]
}

export interface TicketListResponse {
  items: Ticket[]
  total: number
  page: number
  page_size: number
}

export interface CreateTicketPayload {
  subject: string
  description: string
  book_id?: string | null
  category: TicketCategory
}

export interface CreateMessagePayload {
  body: string
}
