// Central source of truth for all app constants

export const APP_NAME    = 'LexAI' as const
export const APP_TAGLINE = 'Intelligent Legal Research & Compliance Analysis' as const
export const APP_VERSION = '1.0.0' as const

// Vite exposes env vars on import.meta.env — typed in vite-env.d.ts
export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export const ROUTES = {
  HOME:      '/',
  LOGIN:     '/login',
  REGISTER:  '/register',
  FORGOT:    '/forgot-password',
  DASHBOARD: '/dashboard',
  ANALYZE:   '/analyze',
  RESULTS:   '/results/:id',
  CITATIONS: '/citations/:id',
  REPORTS:   '/reports',
  DOCUMENTS: '/documents',
  ADMIN:     '/admin',
  SETTINGS:  '/settings',
  ABOUT:     '/about',
  NOT_FOUND: '*',
} as const

export const RISK_LEVELS = {
  HIGH:   'high',
  MEDIUM: 'medium',
  LOW:    'low',
  NONE:   'none',
} as const

export type RiskLevel = typeof RISK_LEVELS[keyof typeof RISK_LEVELS]

export const STORAGE_KEYS = {
  THEME:   'lexai-theme',
  AUTH:    'lexai-auth',
  SIDEBAR: 'lexai-sidebar-collapsed',
} as const