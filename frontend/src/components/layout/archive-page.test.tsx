import { act } from "react"
import { createRoot, type Root } from "react-dom/client"
import { Link, MemoryRouter, Route, Routes } from "react-router-dom"
import { afterEach, expect, it, vi } from "vitest"
import { ArchivePage } from "./archive-page"
import { DashboardPage } from "./dashboard-page"
import { useProjectsStore } from "@/stores/projects-store"
import { useToastStore } from "@/stores/toast-store"

let root: Root | undefined
let container: HTMLDivElement | undefined
afterEach(async () => {
  await act(async () => root?.unmount())
  root = undefined
  container?.remove()
  useProjectsStore.setState(useProjectsStore.getInitialState(), true)
  useToastStore.getState().clearToasts()
  vi.unstubAllGlobals()
})

it("shows a restored project when returning to the dashboard without reloading", async () => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true)
  const project = { id: "a", name: "Restored project", path: "/a", status: "stopped" }
  let archived = true
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    let data: unknown
    if (url === "/api/projects/archived") data = archived ? [project] : []
    else if (url === "/api/projects/archive/settings") data = { auto_archive_enabled: false, auto_archive_after_days: 30 }
    else if (url === "/api/projects/a/unarchive") { archived = false; data = { unarchived: true } }
    else if (url === "/api/projects") data = archived ? [] : [project]
    else if (url === "/api/projects/overview") data = {}
    else throw new Error(`Unexpected request ${url}`)
    return new Response(JSON.stringify(data))
  }))
  container = document.createElement("div")
  document.body.append(container)
  await act(async () => {
    root = createRoot(container!)
    root.render(<MemoryRouter initialEntries={["/archive"]}>
      <Link to="/">Dashboard</Link>
      <Routes><Route path="/archive" element={<ArchivePage />} /><Route path="/" element={<DashboardPage />} /></Routes>
    </MemoryRouter>)
  })
  await act(async () => {
    const button = [...container!.querySelectorAll("button")].find(item => item.textContent?.includes("Unarchive"))!
    button.click()
  })
  expect(container.textContent).toContain("No archived projects")
  await act(async () => container!.querySelector("a")!.click())
  expect(container.textContent).toContain("Restored project")
  expect(container.textContent).not.toContain("No projects yet")
})

it("keeps projects usable and reports a statistics request failure", async () => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true)
  useProjectsStore.setState({ projects: [{ id: "a", name: "Available project", path: "/a", status: "stopped" }] })
  vi.stubGlobal("fetch", vi.fn(async () => new Response("Service unavailable", { status: 503 })))
  container = document.createElement("div")
  document.body.append(container)
  await act(async () => {
    root = createRoot(container!)
    root.render(<MemoryRouter><DashboardPage /></MemoryRouter>)
  })
  expect(container.textContent).toContain("Available project")
  expect(useToastStore.getState().toasts).toEqual(expect.arrayContaining([
    expect.objectContaining({ title: "Failed to load project statistics", tone: "error" }),
  ]))
})
