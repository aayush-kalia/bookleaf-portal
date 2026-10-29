
import { useQuery } from '@tanstack/react-query'
import { booksApi } from '../../api/booksApi'

export const booksQueryKey = ['books']

export function useBooks() {
  return useQuery({
    queryKey: booksQueryKey,
    queryFn: booksApi.list,
  })
}
