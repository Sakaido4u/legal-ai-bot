// Centralized Axios instance.
// ALL API calls go through this — never use raw fetch() or axios directly in components.

import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { API_BASE_URL, STORAGE_KEYS } from '@/constants/app'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept:         'application/json',
  },
})

function normalizeApiDetail(detail: unknown): string | undefined {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map(item => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object' && 'msg' in item) {
        return String((item as { msg: unknown }).msg)
      }
      return null
    }).filter(Boolean)
    return parts.length ? parts.join('; ') : undefined
  }
  return undefined
}

// ── Request interceptor ────────────────────────────────────────
// Runs before EVERY request.
// Reads the stored token and attaches it as Bearer auth.
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Let the browser set multipart boundary; default JSON Content-Type breaks FormData.
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      if (typeof config.headers.delete === 'function') {
        config.headers.delete('Content-Type')
      } else {
        delete config.headers['Content-Type']
      }
    }

    try {
      const stored = localStorage.getItem(STORAGE_KEYS.AUTH)
      if (stored) {
        const parsed: { token?: string } = JSON.parse(stored)
        if (parsed.token) {
          config.headers.Authorization = `Bearer ${parsed.token}`
        }
      }
    } catch {
      // If storage read fails, continue without token
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// ── Response interceptor ──────────────────────────────────────
// Runs after EVERY response.
// Handles 401 (expired session) and normalizes error messages.
api.interceptors.response.use(
  response => response,
  (error: AxiosError<{ detail?: unknown; message?: string }>) => {
    // Session expired → clear storage and redirect to login.
    // Do not redirect on /auth/* 401s (invalid credentials during login/register).
    const requestUrl = error.config?.url ?? ''
    const isAuthRoute = requestUrl.includes('/auth/')
    if (error.response?.status === 401 && !isAuthRoute) {
      localStorage.removeItem(STORAGE_KEYS.AUTH)
      window.location.href = '/login'
    }

    // Preserve status/code so callers can branch on network vs HTTP errors.
    const message =
      normalizeApiDetail(error.response?.data?.detail) ??
      error.response?.data?.message ??
      error.message ??
      'An unexpected error occurred'

    const wrapped = new Error(
      typeof message === 'string' ? message : String(message),
    ) as Error & {
      status?: number
      code?: string
      response?: AxiosError['response']
    }
    wrapped.status = error.response?.status
    wrapped.code = error.code
    wrapped.response = error.response
    return Promise.reject(wrapped)  }
)

export default api