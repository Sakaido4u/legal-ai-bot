// Auth service — handles login and register API calls.
// Falls back to mock validation when backend is unreachable,
// so the app works in demo mode without a running server.

import api from '@/api/axiosInstance'
import type { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse } from '@/types/auth'

// ── Demo credentials for when backend is not running ──────────
// Remove this block when deploying with a real backend
const DEMO_USERS = [
  { id: '1', name: 'Demo User',  email: 'demo@lexai.com',  password: 'Demo@1234' },
  { id: '2', name: 'Admin User', email: 'admin@lexai.com', password: 'Admin@1234' },
]

export const authService = {

  // POST /auth/login  (or /v1/auth/login — adjust to match your FastAPI route)
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      // Attempt real backend login
      const res = await api.post<LoginResponse>('/auth/login', credentials)
      return res.data
    } catch (err: unknown) {
      // If backend is unreachable (network error / 404), fall back to demo validation
      const isNetworkError =
        !err ||
        (typeof err === 'object' &&
          'code' in err &&
          (err as { code?: string }).code === 'ERR_NETWORK') ||
        (typeof err === 'object' &&
          'response' in err &&
          (err as { response?: { status?: number } }).response?.status === 404)

      if (isNetworkError) {
        // Demo mode — validate against hardcoded users
        return authService._demoLogin(credentials)
      }

      // Real error from backend (401, 422, etc.) — re-throw so UI shows the message
      throw err
    }
  },

  // POST /auth/register
  async register(data: RegisterRequest): Promise<RegisterResponse> {
    try {
      const res = await api.post<RegisterResponse>('/auth/register', data)
      return res.data
    } catch (err: unknown) {
      const isNetworkError =
        !err ||
        (typeof err === 'object' &&
          'code' in err &&
          (err as { code?: string }).code === 'ERR_NETWORK') ||
        (typeof err === 'object' &&
          'response' in err &&
          (err as { response?: { status?: number } }).response?.status === 404)

      if (isNetworkError) {
        return authService._demoRegister(data)
      }
      throw err
    }
  },

  // ── Demo mode helpers (private) ────────────────────────────
  _demoLogin(credentials: LoginRequest): LoginResponse {
    const user = DEMO_USERS.find(
      u =>
        u.email.toLowerCase() === credentials.email.toLowerCase() &&
        u.password === credentials.password
    )

    if (!user) {
      // Mimic a 401 response shape so the UI error handling works identically
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
      token_type:   'bearer',
      user: {
        id:    user.id,
        name:  user.name,
        email: user.email,
      },
    }
  },

  _demoRegister(data: RegisterRequest): RegisterResponse {
    // In demo mode, any registration succeeds
    const newUser = {
      id:    String(Date.now()),
      name:  data.name,
      email: data.email,
    }
    return {
      access_token: `demo-token-${newUser.id}`,
      token_type:   'bearer',
      user:         newUser,
    }
  },
}