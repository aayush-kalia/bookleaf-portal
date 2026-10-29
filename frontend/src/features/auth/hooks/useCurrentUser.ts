import { useQuery } from '@tanstack/react-query'
import { ApiError } from '../../../api/client'
import { authApi } from '../api/authApi'

export const currentUserKey = ['auth', 'me']

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserKey,
    queryFn: authApi.me,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 401) {
        return false
      }
      return failureCount < 1
    },
  })
}
