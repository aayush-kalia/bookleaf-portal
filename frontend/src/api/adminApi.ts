import { apiRequest } from "./client"

export interface AdminUser {
  id: string
  name: string
  email: string
  role: 'admin'
}

export const adminApi = {
  list: () => apiRequest<AdminUser[]>('/auth/admins'),
}