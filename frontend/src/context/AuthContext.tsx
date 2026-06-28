import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from 'react'
import { STORAGE_KEYS } from '@/constants/app'

interface User {
  id: string
  name: string
  email: string
  avatar?: string
}

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (user: User, token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.AUTH)
      if (!stored) return null
      const parsed: { user: User } = JSON.parse(stored)
      if (parsed?.user?.id && parsed?.user?.email) return parsed.user
      return null
    } catch {
      localStorage.removeItem(STORAGE_KEYS.AUTH)
      return null
    }
  })

  const [isLoading] = useState(false)

  const login = (user: User, token: string) => {
    setUser(user)
    localStorage.setItem(STORAGE_KEYS.AUTH, JSON.stringify({ user, token }))
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem(STORAGE_KEYS.AUTH)
  }

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, isLoading, login, logout }}
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