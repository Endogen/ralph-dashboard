import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"

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
      // Use sessionStorage instead of localStorage — tokens are not
      // accessible after the tab is closed and are scoped per tab,
      // reducing the XSS attack surface.
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    },
  ),
)
