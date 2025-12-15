import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient, User } from '@/lib/api'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  signup: (email: string, password: string, name?: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  setUser: (user: User, token: string) => void
}

export const useAuthStore = create<AuthState>()(  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (email: string, password: string) => {
        const response = await apiClient.login(email, password)
        if (response.success && response.data) {
          const { user, token } = response.data
          apiClient.setToken(token)
          set({ user, token, isAuthenticated: true })
          return { success: true }
        }
        return { success: false, error: response.error || 'Login failed' }
      },

      signup: async (email: string, password: string, name?: string) => {
        const response = await apiClient.signup(email, password, name)
        if (response.success && response.data) {
          const { user, token } = response.data
          apiClient.setToken(token)
          set({ user, token, isAuthenticated: true })
          return { success: true }
        }
        return { success: false, error: response.error || 'Signup failed' }
      },

      logout: () => {
        apiClient.clearToken()
        set({ user: null, token: null, isAuthenticated: false })
      },

      setUser: (user: User, token: string) => {
        apiClient.setToken(token)
        set({ user, token, isAuthenticated: true })
      },
    }),
    {
      name: 'auth-storage',
    }
  )
)
