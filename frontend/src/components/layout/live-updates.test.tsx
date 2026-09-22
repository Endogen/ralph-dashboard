import { act, StrictMode } from "react"
import { createRoot, type Root } from "react-dom/client"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { AppLayout } from "./app-layout"
import { ProjectPage } from "./project-page"
import { useAuthStore } from "@/stores/auth-store"
import { useProjectsStore } from "@/stores/projects-store"
import { useActiveProjectStore } from "@/stores/active-project-store"
import { deliverAttentionSignal } from "@/lib/native-notifications"
import { useLiveEvent } from "@/hooks/use-live-event"
import { liveEvents, type LiveEventListener } from "@/lib/live-events"

vi.mock("@/api/generation", () => ({ ensureGenerationPolling: vi.fn() }))
vi.mock("@/lib/native-notifications", () => ({ deliverAttentionSignal: vi.fn() }))
vi.mock("@/components/dashboard/add-project-dialog", () => ({ AddProjectDialog: () => null }))

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
  message(payload: unknown) { this.onmessage?.({ data: JSON.stringify(payload) }) }
}

let root: Root
let container: HTMLDivElement
let fetcher: ReturnType<typeof vi.fn>
let logText: string
const originalScrollTo = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollTo")
const project = { id: "a", name: "Alpha", path: "/a", status: "stopped", pause_requested: false,
  ralph_dir: "/a/.ralph", plan_file: null, log_file: "/a/.ralph/ralph.log" }

beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true)
  vi.stubGlobal("WebSocket", FakeSocket)
  vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener() {}, removeEventListener() {} }))
  Object.defineProperty(HTMLElement.prototype, "scrollTo", { configurable: true, value: vi.fn() })
  FakeSocket.instances = []
  useAuthStore.getState().setTokens(`header.${btoa(JSON.stringify({ exp: 9999999999 }))}.signature`, "refresh")
  logText = "initial log\n"
  fetcher = vi.fn(async (input: string) => {
    const url = new URL(input, "http://localhost")
    let result: unknown
    if (url.pathname === "/api/projects") result = [project]
    else if (url.pathname === "/api/projects/a") result = project
    else if (url.pathname.endsWith("/iterations")) result = { iterations: [], total: 0 }
    else if (url.pathname.endsWith("/notifications")) result = []
    else if (url.pathname.endsWith("/plan")) result = { raw: "", phases: [], tasks_done: 0, tasks_total: 0, status: null }
    else if (url.pathname.endsWith("/config")) result = { cli: "codex" }
    else if (url.pathname.endsWith("/stats")) result = null
    else if (url.pathname.endsWith("/log")) {
      const offset = Number(url.searchParams.get("offset") ?? 0)
      result = { text: logText.slice(offset), offset: logText.length, generation: "fixture", reset: offset === 0, has_more: false }
    } else throw new Error(`Unexpected request ${input}`)
    return new Response(JSON.stringify(result), { headers: { "Content-Type": "application/json" } })
  })
  vi.stubGlobal("fetch", fetcher)
  container = document.createElement("div")
  document.body.append(container)
  root = createRoot(container)
})

afterEach(async () => {
  await act(async () => root.unmount())
  container.remove()
  useAuthStore.getState().clearTokens()
  vi.restoreAllMocks()
  if (originalScrollTo) Object.defineProperty(HTMLElement.prototype, "scrollTo", originalScrollTo)
  else Reflect.deleteProperty(HTMLElement.prototype, "scrollTo")
  useProjectsStore.setState(useProjectsStore.getInitialState(), true)
  useActiveProjectStore.setState(useActiveProjectStore.getInitialState(), true)
  vi.clearAllMocks()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

async function mountProject() {
  await act(async () => root.render(
    <MemoryRouter initialEntries={["/project/a?tab=log"]}>
      <Routes><Route element={<AppLayout />}><Route path="/project/:id" element={<ProjectPage />} /></Route></Routes>
    </MemoryRouter>,
  ))
  expect(FakeSocket.instances).toHaveLength(1)
  const socket = FakeSocket.instances[0]
  await act(async () => { socket.onopen?.(); socket.message({ type: "authenticated" }) })
  await act(async () => { await vi.advanceTimersByTimeAsync(300) })
  return socket
}

it("fans out live updates through one socket and patches shared status only once", async () => {
  // Install before mounting so both consumers capture this instrumented action.
  const activePatch = vi.spyOn(useActiveProjectStore.getState(), "patchActiveProject")
  const socket = await mountProject()
  expect(container.textContent).toContain("initial log")
  expect(socket.send).toHaveBeenCalledWith(JSON.stringify({ action: "subscribe", projects: ["a"] }))
  await act(async () => socket.message({ type: "status_changed", project: "a", data: { status: "running" } }))
  expect(activePatch).toHaveBeenCalledTimes(1)
  expect(useActiveProjectStore.getState().activeProject?.status).toBe("running")
  expect(useProjectsStore.getState().projects[0].status).toBe("running")
  expect(container.textContent).toContain("Running")

  logText += "streamed tail\n"
  const requestsBefore = fetcher.mock.calls.length
  await act(async () => socket.message({ type: "log_append", project: "elsewhere", data: { lines: "foreign", offset: 7 } }))
  expect(fetcher.mock.calls).toHaveLength(requestsBefore)
  await act(async () => socket.message({ type: "log_append", project: "a", data: { lines: "streamed tail\n", offset: logText.length } }))
  expect(container.textContent).toContain("streamed tail")
  await act(async () => socket.message({ type: "notification", project: "a", timestamp: "2026-09-20T12:00:00Z", data: {
    event_id: "attention", prefix: "ERROR", kind: "error", severity: "error", active: true,
    message: "Action needed", iteration: 1, details: null, status: "error", source: "runner",
  } }))
  expect(deliverAttentionSignal).toHaveBeenCalledOnce()
  expect(deliverAttentionSignal).toHaveBeenCalledWith(expect.objectContaining({ title: "Alpha - Error" }))
  await act(async () => { window.dispatchEvent(new CustomEvent("ralph-live-event", { detail: { type: "status_changed", project: "a", data: { status: "error" } } })) })
  expect(useActiveProjectStore.getState().activeProject?.status).toBe("running")
  const calls = fetcher.mock.calls.length
  await act(async () => {
    socket.message({ type: "status_changed", project: "a", data: { status: "invalid" } })
    socket.message(null)
  })
  expect(fetcher.mock.calls).toHaveLength(calls)
})

it("refreshes both views after reconnect and ignores the retired socket", async () => {
  const socket = await mountProject()
  fetcher.mockClear()
  await act(async () => socket.close())
  logText += "written while disconnected\n"
  await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
  expect(FakeSocket.instances).toHaveLength(2)
  const replacement = FakeSocket.instances[1]
  await act(async () => { replacement.onopen?.(); replacement.message({ type: "authenticated" }) })
  await act(async () => { await vi.advanceTimersByTimeAsync(300) })
  expect(fetcher.mock.calls.some(([url]) => url === "/api/projects")).toBe(true)
  expect(fetcher.mock.calls.some(([url]) => String(url).includes("/iterations?"))).toBe(true)
  expect(replacement.send).toHaveBeenCalledWith(JSON.stringify({ action: "subscribe", projects: ["a"] }))
  await act(async () => socket.message({ type: "status_changed", project: "a", data: { status: "error" } }))
  expect(useActiveProjectStore.getState().activeProject?.status).toBe("stopped")
  await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
  expect(container.textContent).toContain("written while disconnected")
})

it("cleans up subscriptions under StrictMode and uses the latest handler", async () => {
  function Subscriber({ receive }: { receive: LiveEventListener }) { useLiveEvent(receive); return null }
  const first = vi.fn()
  const second = vi.fn()
  await act(async () => root.render(<StrictMode><Subscriber receive={first} /></StrictMode>))
  liveEvents.publish({ type: "reconnected" })
  expect(first).toHaveBeenCalledOnce()
  await act(async () => root.render(<StrictMode><Subscriber receive={second} /></StrictMode>))
  liveEvents.publish({ type: "reconnected" })
  expect(first).toHaveBeenCalledOnce()
  expect(second).toHaveBeenCalledOnce()
  await act(async () => root.render(null))
  liveEvents.publish({ type: "reconnected" })
  expect(second).toHaveBeenCalledOnce()
})
