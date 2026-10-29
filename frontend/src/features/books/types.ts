
export interface Book {
  id: string
  author_id: string
  title: string
  isbn: string | null
  genre: string | null
  status: string
  stage: string | null
  mrp: number
  royalty_per_copy: number
  copies_sold: number
  royalty_earned: number
  royalty_paid: number
  royalty_pending: number
  available_on: string | null
}

export interface RoyaltySummary {
  total_earned: number
  total_paid: number
  total_pending: number
  below_threshold: boolean
}

export interface BooksResponse {
  books: Book[]
  royalty_summary: RoyaltySummary
}
