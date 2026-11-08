import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import * as auth from '../api/auth'
import type { User } from '../data/types'

interface AuthValue {
  user: User | null
  /** false, пока не узнали у сервера, есть ли сессия */
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    auth
      .getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true))
  }, [])

  const value: AuthValue = {
    user,
    ready,
    login: async (email, password) => setUser(await auth.login(email, password)),
    register: async (name, email, password) => setUser(await auth.register(name, email, password)),
    logout: async () => {
      await auth.logout()
      setUser(null)
    },
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth вне AuthProvider')
  return ctx
}
