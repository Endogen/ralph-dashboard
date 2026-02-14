import { useEffect } from "react"

import { Settings2 } from "lucide-react"
import { Outlet } from "react-router-dom"

import { AppSidebar } from "@/components/layout/app-sidebar"
import { useProjectsStore } from "@/stores/projects-store"

export function AppLayout() {
  const projects = useProjectsStore((state) => state.projects)
  const fetchProjects = useProjectsStore((state) => state.fetchProjects)

  useEffect(() => {
    void fetchProjects()
  }, [fetchProjects])

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-[1200px] gap-4 p-4 md:p-6">
        <AppSidebar projects={projects} />

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
            <Settings2 className="h-4 w-4 text-muted-foreground" />
          </header>

          <section className="flex-1">
            <Outlet />
          </section>
        </main>
      </div>
    </div>
  )
}
