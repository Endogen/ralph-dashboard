import { afterEach, expect, it, vi } from "vitest"
import { deliverAttentionSignal } from "./native-notifications"
import { useToastStore } from "@/stores/toast-store"

const visibility = Object.getOwnPropertyDescriptor(document, "visibilityState")
afterEach(() => {
  if (visibility) Object.defineProperty(document, "visibilityState", visibility)
  else Reflect.deleteProperty(document, "visibilityState")
  useToastStore.getState().clearToasts()
  vi.unstubAllGlobals()
})

it("falls back to a toast when requesting notification permission rejects", async () => {
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" })
  vi.stubGlobal("Notification", {
    permission: "default",
    requestPermission: vi.fn().mockRejectedValue(new DOMException("Blocked", "NotAllowedError")),
  })
  expect(await deliverAttentionSignal({ title: "Loop failed" })).toBe("toast")
  expect(useToastStore.getState().toasts[0].title).toBe("Loop failed")
})
