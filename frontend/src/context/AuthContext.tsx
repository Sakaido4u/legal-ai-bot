import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from 'react'
import { STORAGE_KEYS } from '@/constants/app'
import type { AuthUser } from '@/types/auth'

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (user: AuthUser, token: string) => void
  updateUser: (user: AuthUser) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readAuth(): { user: AuthUser | null; token: string | null } {
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.AUTH)
    if (!stored) return { user: null, token: null }
    const parsed: { user: AuthUser; token?: string } = JSON.parse(stored)
    if (parsed?.user?.id && parsed?.user?.email) {
      return { user: parsed.user, token: parsed.token ?? null }
    }
    return { user: null, token: null }
  } catch {
    localStorage.removeItem(STORAGE_KEYS.AUTH)
    return { user: null, token: null }
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const initial = readAuth()
  const [user, setUser] = useState<AuthUser | null>(initial.user)
  const [token, setToken] = useState<string | null>(initial.token)
  const [isLoading] = useState(false)

  const login = (nextUser: AuthUser, nextToken: string) => {
    setUser(nextUser)
    setToken(nextToken)
    localStorage.setItem(
      STORAGE_KEYS.AUTH,
      JSON.stringify({ user: nextUser, token: nextToken }),
    )
  }

  const updateUser = (nextUser: AuthUser) => {
    setUser(nextUser)
    const current = readAuth().token ?? token
    if (!current) {
      localStorage.setItem(STORAGE_KEYS.AUTH, JSON.stringify({ user: nextUser }))
      return
    }
    setToken(current)
    localStorage.setItem(
      STORAGE_KEYS.AUTH,
      JSON.stringify({ user: nextUser, token: current }),
    )
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem(STORAGE_KEYS.AUTH)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        updateUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
