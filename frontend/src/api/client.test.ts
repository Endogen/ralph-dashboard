import { afterEach, expect, it, vi } from "vitest"
import { apiFetch, apiRevision } from "./client"

afterEach(() => vi.unstubAllGlobals())

it("keeps the draft's version when background reads discover a newer file", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ raw: "Original" }), { headers: { ETag: '"original"' } }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ raw: "Changed on disk" }), { headers: { ETag: '"changed"' } }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "File changed" }), { status: 412 }))
  vi.stubGlobal("fetch", fetchMock)
  const draft = await apiFetch<{ raw: string }>("/projects/test/plan")
  await apiFetch("/projects/test/plan")
  await expect(apiFetch("/projects/test/plan", {
    method: "PUT",
    headers: { "If-Match": apiRevision(draft) },
    body: JSON.stringify({ content: "User's unsaved draft" }),
  })).rejects.toThrow("412")
  expect(fetchMock.mock.calls[2][1].headers.get("If-Match")).toBe('"original"')
})
