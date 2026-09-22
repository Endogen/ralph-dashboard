import { afterEach, expect, it, vi } from "vitest"
import { browserStorage } from "./browser-storage"
import { useAuthStore } from "@/stores/auth-store"
import { useWizardStore } from "@/stores/wizard-store"

afterEach(() => {
  useAuthStore.getState().clearTokens()
  useWizardStore.getState().reset()
  vi.unstubAllGlobals()
})

it.each(["missing", "blocked", "full"])("keeps login and wizard edits working when storage is %s", (mode) => {
  const blocked = () => { throw new DOMException("Storage unavailable", "SecurityError") }
  const storage = mode === "missing" ? undefined : {
    getItem: mode === "full" ? () => null : blocked,
    setItem: blocked, removeItem: blocked,
  }
  vi.stubGlobal("localStorage", storage)
  vi.stubGlobal("sessionStorage", storage)
  expect(browserStorage("localStorage").getItem("draft")).toBeNull()
  expect(() => useAuthStore.getState().setTokens("access", "refresh")).not.toThrow()
  expect(useAuthStore.getState().accessToken).toBe("access")
  expect(() => useWizardStore.getState().setProjectName("Draft project")).not.toThrow()
  expect(useWizardStore.getState().projectName).toBe("Draft project")
  expect(() => browserStorage("localStorage").removeItem("draft")).not.toThrow()
})

it("still persists and reads values when browser storage is available", () => {
  const values = new Map<string, string>()
  vi.stubGlobal("localStorage", {
    getItem: (name: string) => values.get(name) ?? null,
    setItem: (name: string, value: string) => values.set(name, value),
    removeItem: (name: string) => values.delete(name),
  })
  useWizardStore.getState().setProjectName("Saved draft")
  const saved = JSON.parse(values.get("ralph-wizard-draft-v1")!)
  expect(saved.state.projectName).toBe("Saved draft")
  expect(browserStorage("localStorage").getItem("ralph-wizard-draft-v1")).toBe(values.get("ralph-wizard-draft-v1"))
})
