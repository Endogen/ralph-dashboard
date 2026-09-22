import { afterEach, expect, it, vi } from "vitest"
import { useActiveProjectStore } from "./active-project-store"
import { useProjectsStore } from "./projects-store"

const project = { id: "a", name: "Alpha", path: "/a", status: "stopped" as const }
afterEach(() => {
  useActiveProjectStore.setState(useActiveProjectStore.getInitialState(), true)
  useProjectsStore.setState(useProjectsStore.getInitialState(), true)
})

it("only notifies project subscribers when a patch changes their data", () => {
  useProjectsStore.getState().setProjects([project])
  useActiveProjectStore.setState({ activeProject: { ...project, pause_requested: false, ralph_dir: "/a/.ralph", plan_file: null, log_file: null } })
  const listChanged = vi.fn()
  const activeChanged = vi.fn()
  const stops = [useProjectsStore.subscribe(listChanged), useActiveProjectStore.subscribe(activeChanged)]
  try {
    for (const status of ["running", "running"] as const) {
      useProjectsStore.getState().patchProject("a", { status })
      useActiveProjectStore.getState().patchActiveProject("a", { status })
    }
    useProjectsStore.getState().patchProject("missing", { status: "error" })
    useActiveProjectStore.getState().patchActiveProject("missing", { status: "error" })
    expect(listChanged).toHaveBeenCalledOnce()
    expect(activeChanged).toHaveBeenCalledOnce()
    expect(useProjectsStore.getState().projects[0].status).toBe("running")
    expect(useActiveProjectStore.getState().activeProject?.status).toBe("running")
  } finally { stops.forEach(stop => stop()) }
})
