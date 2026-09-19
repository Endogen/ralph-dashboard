import { beforeEach, expect, it, vi } from "vitest"
import { apiFetch } from "./client"
import { fetchIterationHistory } from "./iterations"
import { sampleTimeline } from "@/lib/chart-sampling"
vi.mock("./client", () => ({ apiFetch: vi.fn() }))
beforeEach(() => vi.clearAllMocks())
it("loads history beyond 500 iterations without losing the latest record", async () => {
  vi.mocked(apiFetch).mockResolvedValueOnce({ total: 601, iterations: Array.from({length:500}, (_, i) => ({number:i+1})) })
    .mockResolvedValueOnce({ total: 601, iterations: Array.from({length:101}, (_, i) => ({number:i+501})) })
  const result = await fetchIterationHistory("fixture")
  expect(result.iterations).toHaveLength(601)
  expect(result.iterations.at(-1)?.number).toBe(601)
  expect(vi.mocked(apiFetch).mock.calls[1][0]).toContain("offset=500")
})
it("samples cumulative chart points while retaining both endpoints", () => {
  const points = Array.from({length:10000}, (_, total) => ({total}))
  const result = sampleTimeline(points)
  expect(result).toHaveLength(500)
  expect(result[0].total).toBe(0)
  expect(result.at(-1)?.total).toBe(9999)
})
