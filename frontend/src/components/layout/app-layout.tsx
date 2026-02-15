import { useCallback, useEffect, useState } from "react"

import { FolderPlus, MoonStar, Sun } from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"

import { AddProjectDialog } from "@/components/dashboard/add-project-dialog"
import { AppSidebar } from "@/components/layout/app-sidebar"
import { ToastRegion } from "@/components/ui/toast-region"
import { useTheme } from "@/hooks/use-theme"
import { type WebSocketEnvelope, useWebSocket } from "@/hooks/use-websocket"
import { useProjectsStore } from "@/stores/projects-store"
import type { ProjectStatus } from "@/types/project"

const mobileStatusClass: Record<ProjectStatus, string> = {
  running: "bg-emerald-500",
  paused: "bg-amber-500",
  stopped: "bg-slate-400",
  complete: "bg-teal-500",
  error: "bg-rose-500",
}

export function AppLayout() {
  const [addProjectOpen, setAddProjectOpen] = useState(false)
  const { preference, resolvedTheme, setPreference, toggleTheme } = useTheme()
  const projects = useProjectsStore((state) => state.projects)
  const fetchProjects = useProjectsStore((state) => state.fetchProjects)
  const patchProject = useProjectsStore((state) => state.patchProject)
  const upsertProject = useProjectsStore((state) => state.upsertProject)
  const handleSocketEvent = useCallback(
    (event: WebSocketEnvelope) => {
      if (
        (event.type === "iteration_started" ||
          event.type === "iteration_completed" ||
          event.type === "plan_updated") &&
        event.project
      ) {
        void fetchProjects()
      }

      if (event.type !== "status_changed" || !event.project) {
        return
      }
      if (!event.data || typeof event.data !== "object") {
        return
      }

      const status = (event.data as { status?: string }).status
      if (!status) {
        return
      }

      const validStatuses = new Set<ProjectStatus>(["running", "paused", "stopped", "complete", "error"])
      if (!validStatuses.has(status as ProjectStatus)) {
        return
      }
      patchProject(event.project, { status: status as ProjectStatus })
    },
    [fetchProjects, patchProject],
  )
  const { connected, reconnecting } = useWebSocket({
    projects: projects.map((project) => project.id),
    onEvent: handleSocketEvent,
  })

  useEffect(() => {
    void fetchProjects()
  }, [fetchProjects])

  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-[1200px] gap-4 p-4 md:p-6">
        <AppSidebar
          projects={projects}
          onAddProject={() => setAddProjectOpen(true)}
          resolvedTheme={resolvedTheme}
          toggleTheme={toggleTheme}
          preference={preference}
          setPreference={setPreference}
          connected={connected}
          reconnecting={reconnecting}
        />

        <main className="flex min-h-[80vh] flex-1 flex-col gap-4 p-0 md:p-2">
          <section className="space-y-2 md:hidden">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `rounded-md border px-3 py-2 text-sm font-medium ${
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "bg-background/70 text-muted-foreground"
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-medium ${
                    reconnecting
                      ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                      : connected
                        ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                        : "bg-slate-500/15 text-slate-700 dark:text-slate-300"
                  }`}
                >
                  {reconnecting ? "Reconnecting" : connected ? "Live" : "Offline"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="rounded-full border bg-background/60 p-2 hover:bg-background"
                  title={resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                  aria-label={resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                >
                  {resolvedTheme === "dark" ? (
                    <Sun className="h-4 w-4 text-amber-500" />
                  ) : (
                    <MoonStar className="h-4 w-4 text-slate-600" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setAddProjectOpen(true)}
                  className="flex items-center gap-1 rounded-md border bg-background/70 px-3 py-2 text-sm font-medium text-muted-foreground"
                >
                  <FolderPlus className="h-4 w-4" />
                  Add
                </button>
              </div>
            </div>

            <div className="flex gap-2 overflow-x-auto pb-1">
              {projects.map((project) => (
                <NavLink
                  key={project.id}
                  to={`/project/${project.id}`}
                  className={({ isActive }) =>
                    `flex shrink-0 items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                      isActive
                        ? "bg-primary/15 text-foreground"
                        : "bg-background/60 text-muted-foreground"
                    }`
                  }
                >
                  <span className={`h-2 w-2 rounded-full ${mobileStatusClass[project.status]}`} />
                  <span className="max-w-[160px] truncate">{project.name}</span>
                </NavLink>
              ))}
            </div>
          </section>

          <section className="flex-1">
            <Outlet />
          </section>
        </main>
      </div>

      <AddProjectDialog
        open={addProjectOpen}
        onClose={() => setAddProjectOpen(false)}
        onCreated={upsertProject}
      />
      <ToastRegion />
    </div>
  )
}
