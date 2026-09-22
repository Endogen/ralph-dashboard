import { ensureGenerationPolling } from "@/api/generation"

import { useCallback, useEffect, useMemo, useState } from "react"

import { FolderPlus, MoonStar, Sun } from "lucide-react"
import { NavLink, Outlet, useNavigate } from "react-router-dom"

import { AddProjectDialog } from "@/components/dashboard/add-project-dialog"
import { AppSidebar } from "@/components/layout/app-sidebar"
import { ErrorBoundary } from "@/components/ui/error-boundary"
import { ToastRegion } from "@/components/ui/toast-region"
import { useTheme } from "@/hooks/use-theme"
import { useWebSocket } from "@/hooks/use-websocket"
import { useLiveEvent } from "@/hooks/use-live-event"
import type { LiveEvent } from "@/lib/live-events"
import { deliverAttentionSignal } from "@/lib/native-notifications"
import { useActiveProjectStore } from "@/stores/active-project-store"
import { useProjectsStore } from "@/stores/projects-store"
export function AppLayout() {
  const navigate = useNavigate()
  const [addProjectOpen, setAddProjectOpen] = useState(false)
  const { preference, resolvedTheme, setPreference, toggleTheme } = useTheme()
  const projects = useProjectsStore((state) => state.projects)
  const fetchProjects = useProjectsStore((state) => state.fetchProjects)
  const patchProject = useProjectsStore((state) => state.patchProject)
  const upsertProject = useProjectsStore((state) => state.upsertProject)
  const activeProjectId = useActiveProjectStore((state) => state.activeProjectId)
  const patchActiveProject = useActiveProjectStore((state) => state.patchActiveProject)
  const subscribedProjects = useMemo(() => {
    const ids = new Set(projects.map((project) => project.id))
    if (activeProjectId) {
      ids.add(activeProjectId)
    }
    return Array.from(ids)
  }, [activeProjectId, projects])
  const handleSocketEvent = useCallback(
    (event: LiveEvent) => {
      const projectName = event.project
        ? (projects.find((project) => project.id === event.project)?.name ?? event.project)
        : null

      if (
        (event.type === "reconnected" ||
          event.type === "watcher_projects_refreshed" ||
          event.type === "iteration_started" ||
          event.type === "iteration_completed" ||
          event.type === "plan_updated")
      ) {
        void fetchProjects()
      }

      if (event.type === "notification") {
        const data = event.data
        const eventId = data.event_id.trim()
        const prefix = (data.prefix ?? "").trim().toUpperCase()
        const kind = data.kind.trim().toLowerCase()
        const severity = data.severity.trim().toLowerCase()
        const message = data.message.trim()
        const details = (data.details ?? "").trim()
        const iteration = data.iteration

        if (!prefix || !message || prefix === "PROGRESS" || kind === "progress") {
          return
        }

        const titleMap: Record<string, string> = {
          ERROR: `${projectName ?? "Project"} - Error`,
          BLOCKED: `${projectName ?? "Project"} - Blocked`,
          DECISION: `${projectName ?? "Project"} - Decision needed`,
          DONE: `${projectName ?? "Project"} complete`,
          PLANNING_COMPLETE: `${projectName ?? "Project"} ready for building`,
        }
        const toneMap = {
          ERROR: "error",
          BLOCKED: "error",
          DECISION: "info",
          DONE: "success",
          PLANNING_COMPLETE: "info",
        } as const
        if (!(prefix in titleMap)) {
          return
        }
        const supportedPrefix =
          prefix as "ERROR" | "BLOCKED" | "DECISION" | "DONE" | "PLANNING_COMPLETE"

        const description = details || message
        const tone =
          severity === "error"
            ? "error"
            : severity === "success"
              ? "success"
              : toneMap[supportedPrefix]
        const dedupeKey =
          eventId ||
          [
            "runtime-alert",
            event.project,
            prefix,
            iteration ?? "none",
            event.timestamp ?? "no-ts",
            message,
          ].join(":")
        void deliverAttentionSignal({
          title: titleMap[supportedPrefix],
          description,
          tone,
          durationMs: prefix === "DONE" ? 6000 : 5000,
          dedupeKey,
          browserTag: eventId || `ralph-runtime-${event.project}-${prefix.toLowerCase()}`,
          onClick: () => {
            navigate(`/project/${event.project}`)
          },
        })
        return
      }

      if (event.type === "status_changed") {
        // The layout owns shared project state; views only refresh their own data.
        patchProject(event.project, { status: event.data.status })
        patchActiveProject(event.project, { status: event.data.status })
      }
    },
    [fetchProjects, navigate, patchProject, patchActiveProject, projects],
  )
  useLiveEvent(handleSocketEvent)
  const { connected, reconnecting } = useWebSocket({
    projects: subscribedProjects,
  })

  useEffect(() => {
    void fetchProjects()
    ensureGenerationPolling()
  }, [fetchProjects])

  return (
    <div className="min-h-screen overflow-x-clip bg-background text-foreground">
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

        <main className="flex min-h-[80vh] min-w-0 flex-1 flex-col gap-4 p-0 md:p-2">
          <section className="flex flex-wrap items-center justify-between gap-2 md:hidden">
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
              <NavLink
                to="/archive"
                className={({ isActive }) =>
                  `rounded-md border px-3 py-2 text-sm font-medium ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "bg-background/70 text-muted-foreground"
                  }`
                }
              >
                Archive
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
                {reconnecting ? "Reconnecting" : connected ? "Connected" : "Offline"}
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
          </section>

          <section className="min-w-0 flex-1">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
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
