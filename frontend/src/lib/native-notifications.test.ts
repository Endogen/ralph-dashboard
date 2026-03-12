import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/browser-notifications", () => ({
  showBrowserNotification: vi.fn(),
}))

function setVisibilityState(value: DocumentVisibilityState) {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value,
  })
}

describe("deliverAttentionSignal", () => {
  afterEach(async () => {
    const { useToastStore } = await import("@/stores/toast-store")
    useToastStore.getState().clearToasts()
    setVisibilityState("visible")
    vi.clearAllMocks()
  })

  it("shows a toast while the document is visible and suppresses duplicate deliveries", async () => {
    vi.resetModules()
    setVisibilityState("visible")

    const { useToastStore } = await import("@/stores/toast-store")
    const { deliverAttentionSignal } = await import("@/lib/native-notifications")
    const { showBrowserNotification } = await import("@/lib/browser-notifications")

    const firstResult = await deliverAttentionSignal({
      title: "Project error",
      description: "Tests failed",
      dedupeKey: "notif-visible",
    })
    const duplicateResult = await deliverAttentionSignal({
      title: "Project error",
      description: "Tests failed",
      dedupeKey: "notif-visible",
    })

    expect(firstResult).toBe("toast")
    expect(duplicateResult).toBe("none")
    expect(useToastStore.getState().toasts).toHaveLength(1)
    expect(vi.mocked(showBrowserNotification)).not.toHaveBeenCalled()
  })

  it("uses a browser notification when the document is hidden and browser delivery succeeds", async () => {
    vi.resetModules()
    setVisibilityState("hidden")

    const { useToastStore } = await import("@/stores/toast-store")
    const { deliverAttentionSignal } = await import("@/lib/native-notifications")
    const { showBrowserNotification } = await import("@/lib/browser-notifications")
    vi.mocked(showBrowserNotification).mockResolvedValue(true)

    const result = await deliverAttentionSignal({
      title: "Project complete",
      description: "All tasks complete",
      dedupeKey: "notif-hidden",
    })

    expect(result).toBe("browser")
    expect(vi.mocked(showBrowserNotification)).toHaveBeenCalledTimes(1)
    expect(useToastStore.getState().toasts).toHaveLength(0)
  })
})
