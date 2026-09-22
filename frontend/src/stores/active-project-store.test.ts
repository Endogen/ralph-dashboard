import { afterEach, expect, it, vi } from "vitest"
import { useActiveProjectStore } from "./active-project-store"

const project = (id: string) => ({ id, name: id, path: `/${id}`, status: "stopped" })
function deferred() {
  let resolve!: (value: Response) => void
  let reject!: (error: Error) => void
  const promise = new Promise<Response>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
afterEach(() => {
  useActiveProjectStore.getState().clearActiveProject()
  vi.unstubAllGlobals()
})

it.each(["success", "failure"])("ignores a late %s from the project we navigated away from", async (outcome) => {
  const old = deferred()
  vi.stubGlobal("fetch", vi.fn().mockReturnValueOnce(old.promise)
    .mockResolvedValueOnce(new Response(JSON.stringify(project("b")))))
  const oldRequest = useActiveProjectStore.getState().fetchActiveProject("a")
  await useActiveProjectStore.getState().fetchActiveProject("b")
  if (outcome === "success") old.resolve(new Response(JSON.stringify(project("a"))))
  else old.reject(new Error("Old project unavailable"))
  await oldRequest
  expect(useActiveProjectStore.getState()).toMatchObject({ activeProjectId: "b", activeProject: project("b"), error: null, isLoading: false })
})

it("does not restore a project after leaving its page", async () => {
  const pending = deferred()
  vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending.promise))
  const request = useActiveProjectStore.getState().fetchActiveProject("a")
  useActiveProjectStore.getState().clearActiveProject()
  pending.resolve(new Response(JSON.stringify(project("a"))))
  await request
  expect(useActiveProjectStore.getState()).toMatchObject({ activeProjectId: null, activeProject: null, isLoading: false })
})

it("keeps the newest refresh when requests for the same project finish out of order", async () => {
  const old = deferred()
  vi.stubGlobal("fetch", vi.fn().mockReturnValueOnce(old.promise)
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...project("a"), status: "running" }))))
  const oldRequest = useActiveProjectStore.getState().fetchActiveProject("a")
  await useActiveProjectStore.getState().fetchActiveProject("a")
  old.resolve(new Response(JSON.stringify(project("a"))))
  await oldRequest
  expect(useActiveProjectStore.getState().activeProject?.status).toBe("running")
})

it("clears the previous project while loading a different one", async () => {
  const pending = deferred()
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify(project("a"))))
    .mockReturnValueOnce(pending.promise))
  await useActiveProjectStore.getState().fetchActiveProject("a")
  const request = useActiveProjectStore.getState().fetchActiveProject("b")
  expect(useActiveProjectStore.getState()).toMatchObject({ activeProjectId: "b", activeProject: null, isLoading: true })
  pending.resolve(new Response(JSON.stringify(project("b"))))
  await request
})
