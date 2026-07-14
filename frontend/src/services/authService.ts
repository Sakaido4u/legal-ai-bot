// Auth service — login/register hit Postgres-backed JWT endpoints.
// No silent demo fallback: unreachable API surfaces a clear network error.

import api from '@/api/axiosInstance'
import type { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse } from '@/types/auth'

function isNetworkError(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const e = err as {
    code?: string
    status?: number
    message?: string
    response?: unknown
  }
  if (e.code === 'ERR_NETWORK' || e.code === 'ECONNABORTED') return true
  if (e.response == null && typeof e.message === 'string') {
    return /network error|timeout|failed to fetch/i.test(e.message)
  }
  return false
}

function networkError(): Error & { status?: number; code?: string } {
  const error = new Error(
    "Can't reach the server — check that the API is running and try again shortly.",
  ) as Error & { status?: number; code?: string }
  error.code = 'ERR_NETWORK'
  return error
}

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const res = await api.post<LoginResponse>('/auth/login', credentials)
      return res.data
    } catch (err: unknown) {
      if (isNetworkError(err)) throw networkError()
      throw err
    }
  },

  async register(data: RegisterRequest): Promise<RegisterResponse> {
    try {
      const res = await api.post<RegisterResponse>('/auth/register', data)
      return res.data
    } catch (err: unknown) {
      if (isNetworkError(err)) throw networkError()
      throw err
    }
  },

  async forgotPassword(email: string): Promise<{ message: string; reset_token: string | null }> {
    try {
      const res = await api.post<{ message: string; reset_token: string | null }>(
        '/auth/forgot-password',
        { email },
      )
      return res.data
    } catch (err: unknown) {
      if (isNetworkError(err)) throw networkError()
      throw err
    }
  },

  async resetPassword(token: string, new_password: string): Promise<{ message: string }> {
    try {
      const res = await api.post<{ message: string }>('/auth/reset-password', {
        token,
        new_password,
      })
      return res.data
    } catch (err: unknown) {
      if (isNetworkError(err)) throw networkError()
      throw err
    }
  },
}
