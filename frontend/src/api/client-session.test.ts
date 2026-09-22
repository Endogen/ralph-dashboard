import { afterEach, expect, it, vi } from "vitest"
import { apiFetch, refreshAccessToken } from "./client"
import { useAuthStore } from "@/stores/auth-store"

function deferredResponse() {
  let resolve!: (response: Response) => void
  const promise = new Promise<Response>((done) => { resolve = done })
  return { promise, resolve }
}
const refreshed = (token: string) => new Response(JSON.stringify({ access_token: token, token_type: "bearer" }))

afterEach(() => {
  useAuthStore.getState().clearTokens()
  vi.unstubAllGlobals()
})

it("does not restore credentials when a refresh finishes after sign-out", async () => {
  const pending = deferredResponse()
  vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending.promise))
  useAuthStore.getState().setTokens("old-access", "old-refresh")
  const request = refreshAccessToken()
  useAuthStore.getState().clearTokens()
  pending.resolve(refreshed("late-access"))
  expect(await request).toBeNull()
  expect(useAuthStore.getState().accessToken).toBeNull()
})

it.each([200, 401, 503])("ignores an old refresh response (%s) after a new login", async (status) => {
  const pending = deferredResponse()
  vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending.promise))
  useAuthStore.getState().setTokens("old-access", "old-refresh")
  const request = refreshAccessToken()
  useAuthStore.getState().setTokens("new-access", "new-refresh")
  pending.resolve(status === 200 ? refreshed("late-access") : new Response("", { status }))
  expect(await request).toBeNull()
  expect(useAuthStore.getState()).toMatchObject({ accessToken: "new-access", refreshToken: "new-refresh" })
})

it("lets a new session refresh without joining the previous session's request", async () => {
  const old = deferredResponse()
  const current = deferredResponse()
  const fetcher = vi.fn().mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  vi.stubGlobal("fetch", fetcher)
  useAuthStore.getState().setTokens("old-access", "old-refresh")
  const first = refreshAccessToken()
  useAuthStore.getState().setTokens("new-access", "new-refresh")
  const second = refreshAccessToken()
  old.resolve(refreshed("late-access"))
  const oldResult = await first
  const joined = refreshAccessToken()
  current.resolve(refreshed("current-access"))
  expect(oldResult).toBeNull()
  expect(await Promise.all([second, joined])).toEqual(["current-access", "current-access"])
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(useAuthStore.getState().refreshToken).toBe("new-refresh")
})

it("shares one refresh among concurrent callers in the same session", async () => {
  const pending = deferredResponse()
  const fetcher = vi.fn().mockReturnValue(pending.promise)
  vi.stubGlobal("fetch", fetcher)
  useAuthStore.getState().setTokens("old-access", "refresh")
  const requests = [refreshAccessToken(), refreshAccessToken(), refreshAccessToken()]
  pending.resolve(refreshed("fresh-access"))
  expect(await Promise.all(requests)).toEqual(["fresh-access", "fresh-access", "fresh-access"])
  expect(fetcher).toHaveBeenCalledOnce()
})

it("invalidates pending refreshes even if a new login receives identical tokens", async () => {
  const pending = deferredResponse()
  vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending.promise))
  useAuthStore.getState().setTokens("access", "refresh")
  const request = refreshAccessToken()
  useAuthStore.getState().clearTokens()
  useAuthStore.getState().setTokens("access", "refresh")
  pending.resolve(refreshed("late-access"))
  expect(await request).toBeNull()
  expect(useAuthStore.getState().accessToken).toBe("access")
})


it("does not retry an old unauthorized request under a newer login", async () => {
  const pending = deferredResponse()
  const fetcher = vi.fn().mockReturnValueOnce(pending.promise)
  vi.stubGlobal("fetch", fetcher)
  useAuthStore.getState().setTokens("old-access", "old-refresh")
  const request = apiFetch("/projects/a/start", { method: "POST" })
  useAuthStore.getState().setTokens("new-access", "new-refresh")
  pending.resolve(new Response("", { status: 401 }))
  await expect(request).rejects.toThrow("401")
  expect(fetcher).toHaveBeenCalledOnce()
  expect(useAuthStore.getState().accessToken).toBe("new-access")
})
