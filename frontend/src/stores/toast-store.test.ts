import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

describe("useToastStore", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(async () => {
    const { useToastStore } = await import("@/stores/toast-store")
    useToastStore.getState().clearToasts()
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it("queues one toast at a time and promotes the next toast after timeout", async () => {
    vi.resetModules()
    const { useToastStore } = await import("@/stores/toast-store")

    useToastStore.getState().pushToast({ title: "First", durationMs: 1_000 })
    useToastStore.getState().pushToast({ title: "Second", durationMs: 1_000 })

    expect(useToastStore.getState().toasts.map((toast) => toast.title)).toEqual(["First"])
    expect(useToastStore.getState().queue.map((toast) => toast.title)).toEqual(["Second"])

    vi.advanceTimersByTime(1_000)
    expect(useToastStore.getState().toasts.map((toast) => toast.title)).toEqual(["Second"])
    expect(useToastStore.getState().queue).toHaveLength(0)

    vi.advanceTimersByTime(1_000)
    expect(useToastStore.getState().toasts).toHaveLength(0)
  })

  it("drops duplicate toasts while an existing toast with the same dedupe key is active", async () => {
    vi.resetModules()
    const { useToastStore } = await import("@/stores/toast-store")

    const firstId = useToastStore.getState().pushToast({
      title: "Build failed",
      dedupeKey: "runtime:error:1",
    })
    const duplicateId = useToastStore.getState().pushToast({
      title: "Build failed again",
      dedupeKey: "runtime:error:1",
    })

    expect(firstId).toBeGreaterThan(0)
    expect(duplicateId).toBe(-1)
    expect(useToastStore.getState().toasts).toHaveLength(1)
    expect(useToastStore.getState().queue).toHaveLength(0)
  })
})
