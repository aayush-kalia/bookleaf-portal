
import { apiRequest } from '../../../api/client'
import type { Book, BooksResponse } from '../types'

export const booksApi = {
  list: async (): Promise<BooksResponse> => {
    return apiRequest<BooksResponse>('/books')
  },

  getById: async (bookId: string): Promise<Book> => {
    return apiRequest<Book>(`/books/${bookId}`)
  },
}
