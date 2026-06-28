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

// ── Request interceptor ────────────────────────────────────────
// Runs before EVERY request.
// Reads the stored token and attaches it as Bearer auth.
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
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
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    // Session expired → clear storage and redirect to login
    if (error.response?.status === 401) {
      localStorage.removeItem(STORAGE_KEYS.AUTH)
      window.location.href = '/login'
    }

    // Extract the most useful error message
    const message =
      error.response?.data?.detail   ??
      error.response?.data?.message  ??
      error.message                  ??
      'An unexpected error occurred'

    return Promise.reject(new Error(message))
  }
)

export default api