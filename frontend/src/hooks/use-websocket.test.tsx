import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { refreshAccessToken } from "@/api/client"
import { useAuthStore } from "@/stores/auth-store"
import { useWebSocket } from "./use-websocket"

class FakeSocket {
  static OPEN = 1
  static instances: FakeSocket[] = []
  readyState = 1
  onopen: (() => void) | null = null
  onclose: ((event: { code: number }) => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  send = vi.fn()
  constructor() { FakeSocket.instances.push(this) }
  close() { this.onclose?.({ code: 1000 }) }
}

let root: Root | undefined
let container: HTMLDivElement
const token = `header.${btoa(JSON.stringify({ exp: 9999999999 }))}.signature`

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true)
  vi.stubGlobal("WebSocket", FakeSocket)
  vi.useFakeTimers()
  FakeSocket.instances = []
  useAuthStore.getState().setTokens(token, "refresh")
  container = document.createElement("div")
  document.body.append(container)
})
afterEach(async () => {
  await act(async () => root?.unmount())
  root = undefined
  container.remove()
  useAuthStore.getState().clearTokens()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

it("keeps credentials on a refresh server error and clears them on rejection", async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(new Response("", { status: 503 }))
    .mockResolvedValueOnce(new Response("", { status: 401 }))
  vi.stubGlobal("fetch", fetcher)
  await expect(refreshAccessToken()).rejects.toThrow("503")
  expect(useAuthStore.getState().refreshToken).toBe("refresh")
  expect(await refreshAccessToken()).toBeNull()
  expect(useAuthStore.getState().accessToken).toBeNull()
})

it("retries refresh during an outage without reconnecting with the rejected token", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response("", { status: 503 }))
  vi.stubGlobal("fetch", fetcher)
  function Consumer() { useWebSocket(); return null }
  await act(async () => { root = createRoot(container); root.render(<Consumer />) })
  expect(FakeSocket.instances).toHaveLength(1)
  await act(async () => { FakeSocket.instances[0].onclose?.({ code: 1008 }) })
  for (let i = 0; i < 4; i++) {
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
  }
  expect(fetcher).toHaveBeenCalledTimes(5)
  expect(FakeSocket.instances).toHaveLength(1)
  expect(useAuthStore.getState().accessToken).toBe(token)
  fetcher.mockResolvedValue(new Response(JSON.stringify({ access_token: token })))
  await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
  expect(FakeSocket.instances).toHaveLength(2)
  await act(async () => { FakeSocket.instances[1].onopen?.() })
  expect(FakeSocket.instances[1].send).toHaveBeenCalledWith(JSON.stringify({ action: "authenticate", token }))
})
