import type { StateStorage } from "zustand/middleware"

/** Browser persistence is optional: privacy settings or quota can disable it. */
export function browserStorage(kind: "localStorage" | "sessionStorage"): StateStorage {
  return {
    getItem(name) {
      try { return window[kind]?.getItem(name) ?? null } catch { return null }
    },
    setItem(name, value) {
      try { window[kind]?.setItem(name, value) } catch { /* Keep the in-memory state. */ }
    },
    removeItem(name) {
      try { window[kind]?.removeItem(name) } catch { /* Storage may be blocked. */ }
    },
  }
}
