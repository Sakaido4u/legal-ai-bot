import api from '@/api/axiosInstance'
import type { AdminUser } from '@/types/auth'

export const adminService = {
  async listUsers(): Promise<{ users: AdminUser[]; total: number }> {
    const res = await api.get<{ users: AdminUser[]; total: number }>('/admin/users')
    return res.data
  },

  async deactivate(userId: string): Promise<void> {
    await api.post(`/admin/users/${userId}/deactivate`)
  },

  async activate(userId: string): Promise<void> {
    await api.post(`/admin/users/${userId}/activate`)
  },

  async deleteUser(userId: string): Promise<void> {
    await api.delete(`/admin/users/${userId}`)
  },
}
