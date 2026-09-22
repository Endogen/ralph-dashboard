import { browserStorage } from "@/lib/browser-storage"
import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"

type AuthState = {
  accessToken: string | null
  refreshToken: string | null
  sessionVersion: number
  setTokens: (accessToken: string, refreshToken: string) => void
  clearTokens: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      sessionVersion: 0,
      setTokens: (accessToken: string, refreshToken: string) =>
        set((state) => ({ accessToken, refreshToken, sessionVersion: state.sessionVersion + 1 })),
      clearTokens: () =>
        set((state) => ({ accessToken: null, refreshToken: null, sessionVersion: state.sessionVersion + 1 })),
    }),
    {
      name: "ralph-dashboard-auth",
      // Use sessionStorage instead of localStorage — tokens are not
      // accessible after the tab is closed and are scoped per tab,
      // reducing the XSS attack surface.
      storage: createJSONStorage(() => browserStorage("sessionStorage")),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    },
  ),
)
