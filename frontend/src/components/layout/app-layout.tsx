import { useEffect, useState } from "react"

import { Settings2 } from "lucide-react"
import { Outlet } from "react-router-dom"

import { AddProjectDialog } from "@/components/dashboard/add-project-dialog"
import { AppSidebar } from "@/components/layout/app-sidebar"
import { useWebSocket } from "@/hooks/use-websocket"
import { useProjectsStore } from "@/stores/projects-store"

export function AppLayout() {
  const [addProjectOpen, setAddProjectOpen] = useState(false)
  const projects = useProjectsStore((state) => state.projects)
  const fetchProjects = useProjectsStore((state) => state.fetchProjects)
  const upsertProject = useProjectsStore((state) => state.upsertProject)
  const { connected, reconnecting } = useWebSocket({ projects: projects.map((project) => project.id) })

  useEffect(() => {
    void fetchProjects()
  }, [fetchProjects])

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-[1200px] gap-4 p-4 md:p-6">
        <AppSidebar projects={projects} onAddProject={() => setAddProjectOpen(true)} />

        <main className="flex min-h-[80vh] flex-1 flex-col gap-4 rounded-2xl border bg-card/30 p-4 md:p-6">
          <header className="flex items-center justify-between rounded-xl border bg-background/70 px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Workspace
              </h2>
              <p className="text-sm text-muted-foreground">
                Sidebar, routing shell, and content area are now active.
              </p>
            </div>
            <div className="flex items-center gap-3">
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
              <Settings2 className="h-4 w-4 text-muted-foreground" />
            </div>
          </header>

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
    </div>
  )
}
