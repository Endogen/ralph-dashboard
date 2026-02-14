import { create } from "zustand"
import { persist } from "zustand/middleware"

type AuthState = {
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: () => boolean
  setTokens: (accessToken: string, refreshToken: string) => void
  clearTokens: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: () => Boolean(get().accessToken),
      setTokens: (accessToken: string, refreshToken: string) => set({ accessToken, refreshToken }),
      clearTokens: () => set({ accessToken: null, refreshToken: null }),
    }),
    {
      name: "ralph-dashboard-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    },
  ),
)
