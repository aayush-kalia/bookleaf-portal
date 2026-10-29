import { apiRequest } from '../../../api/client'
import type { User } from '../types'

export const authApi = {
  me: () => apiRequest<User>('/auth/me'),

  login: (email: string, password: string) =>
    apiRequest<User>('/auth/login', {
      method: 'POST',
      body: { email, password },
    }),

  logout: () =>
    apiRequest<{ message: string }>('/auth/logout', {
      method: 'POST',
    }),
}
