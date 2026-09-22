import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { apiFetch } from "./client"
import { ensureGenerationPolling } from "./generation"
import { useWizardStore } from "@/stores/wizard-store"

vi.mock("./client", () => ({ apiFetch: vi.fn() }))
vi.mock("@/lib/native-notifications", () => ({ deliverAttentionSignal: vi.fn() }))

beforeEach(() => {
  vi.useFakeTimers()
  useWizardStore.getState().reset()
})
afterEach(async () => {
  useWizardStore.getState().reset()
  await vi.runOnlyPendingTimersAsync()
  vi.useRealTimers()
  vi.resetAllMocks()
})

it.each([404, 503])("ignores a stale polling error (%s) when a new generation has started", async (status) => {
  let reject!: (error: Error) => void
  vi.mocked(apiFetch).mockReturnValueOnce(new Promise((_, fail) => { reject = fail }))
    .mockResolvedValueOnce({ status: "pending" })
  useWizardStore.setState({ activeGenerationRequestId: "old", isGenerating: true })
  ensureGenerationPolling()
  useWizardStore.setState({ activeGenerationRequestId: "new", isGenerating: true })
  reject(new Error(`API request failed (${status})`))
  await vi.advanceTimersByTimeAsync(0)
  expect(useWizardStore.getState()).toMatchObject({ activeGenerationRequestId: "new", isGenerating: true, generateError: null })
  await vi.advanceTimersByTimeAsync(2000)
  expect(apiFetch).toHaveBeenLastCalledWith("/wizard/generate/status/new")
})
