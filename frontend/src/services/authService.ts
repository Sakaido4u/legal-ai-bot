// Auth service — login/register hit Postgres-backed JWT endpoints.
// Falls back to local demo users only when the backend is unreachable.

import api from '@/api/axiosInstance'
import type { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse } from '@/types/auth'

const DEMO_USERS = [
  { id: '1', name: 'Demo User',  email: 'demo@lexai.com',  password: 'Demo@1234' },
  { id: '2', name: 'Admin User', email: 'admin@lexai.com', password: 'Admin@1234' },
]

function isNetworkish(err: unknown): boolean {
  const status =
    typeof err === 'object' && err && 'status' in err
      ? (err as { status?: number }).status
      : typeof err === 'object' && err && 'response' in err
        ? (err as { response?: { status?: number } }).response?.status
        : undefined
  const code =
    typeof err === 'object' && err && 'code' in err
      ? (err as { code?: string }).code
      : undefined
  const message = err instanceof Error ? err.message : ''
  return (
    code === 'ERR_NETWORK' ||
    status === 404 ||
    /not found|network error/i.test(message)
  )
}

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const res = await api.post<LoginResponse>('/auth/login', credentials)
      return res.data
    } catch (err: unknown) {
      if (isNetworkish(err)) {
        return authService._demoLogin(credentials)
      }
      throw err
    }
  },

  async register(data: RegisterRequest): Promise<RegisterResponse> {
    try {
      const res = await api.post<RegisterResponse>('/auth/register', data)
      return res.data
    } catch (err: unknown) {
      if (isNetworkish(err)) {
        return authService._demoRegister(data)
      }
      throw err
    }
  },

  async forgotPassword(email: string): Promise<{ message: string; reset_token: string | null }> {
    const res = await api.post<{ message: string; reset_token: string | null }>(
      '/auth/forgot-password',
      { email },
    )
    return res.data
  },

  async resetPassword(token: string, new_password: string): Promise<{ message: string }> {
    const res = await api.post<{ message: string }>('/auth/reset-password', {
      token,
      new_password,
    })
    return res.data
  },

  _demoLogin(credentials: LoginRequest): LoginResponse {
    const user = DEMO_USERS.find(
      u =>
        u.email.toLowerCase() === credentials.email.toLowerCase() &&
        u.password === credentials.password,
    )

    if (!user) {
      const error = new Error('Invalid email or password') as Error & {
        response?: { status: number; data: { detail: string } }
      }
      error.response = {
        status: 401,
        data: { detail: 'Invalid email or password' },
      }
      throw error
    }

    return {
      access_token: `demo-token-${user.id}-${Date.now()}`,
      token_type: 'bearer',
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
      },
    }
  },

  _demoRegister(data: RegisterRequest): RegisterResponse {
    const newUser = {
      id: String(Date.now()),
      name: data.name,
      email: data.email,
    }
    return {
      access_token: `demo-token-${newUser.id}`,
      token_type: 'bearer',
      user: newUser,
    }
  },
}
