import { CircleDot, FolderPlus, Gauge, PlayCircle, Square, TriangleAlert } from "lucide-react"
import { NavLink } from "react-router-dom"

import { Button } from "@/components/ui/button"
import type { ProjectStatus } from "@/types/project"

type SidebarProject = {
  id: string
  name: string
  status: ProjectStatus
}

type AppSidebarProps = {
  projects: SidebarProject[]
  onAddProject?: () => void
}

type StatusMeta = {
  label: string
  dotClass: string
}

const statusMeta: Record<ProjectStatus, StatusMeta> = {
  running: { label: "Running", dotClass: "bg-emerald-500 animate-pulse" },
  paused: { label: "Paused", dotClass: "bg-amber-500" },
  stopped: { label: "Stopped", dotClass: "bg-slate-400" },
  complete: { label: "Complete", dotClass: "bg-emerald-700" },
  error: { label: "Error", dotClass: "bg-rose-600" },
}

const projectIcon: Record<ProjectStatus, typeof PlayCircle> = {
  running: PlayCircle,
  paused: CircleDot,
  stopped: Square,
  complete: Gauge,
  error: TriangleAlert,
}

export function AppSidebar({ projects, onAddProject }: AppSidebarProps) {
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive
        ? "bg-primary text-primary-foreground shadow-sm"
        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
    }`

  return (
    <aside className="hidden w-72 flex-col rounded-2xl border bg-card/70 p-4 shadow-sm md:flex">
      <header className="space-y-1 border-b pb-4">
        <h1 className="text-lg font-semibold tracking-tight">Ralph Dashboard</h1>
        <p className="text-xs text-muted-foreground">Projects</p>
      </header>

      <nav className="mt-4">
        <NavLink to="/" className={navClass} end>
          <Gauge className="h-4 w-4" />
          Dashboard
        </NavLink>
      </nav>

      <div className="mt-4 flex-1 space-y-2">
        {projects.map((project) => {
          const meta = statusMeta[project.status]
          const Icon = projectIcon[project.status]
          return (
            <NavLink key={project.id} to={`/project/${project.id}`} className={navClass}>
              <span className={`h-2 w-2 rounded-full ${meta.dotClass}`} />
              <Icon className="h-4 w-4" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{project.name}</p>
                <p className="text-[11px] text-muted-foreground">{meta.label}</p>
              </div>
            </NavLink>
          )
        })}
      </div>

      <footer className="mt-4 border-t pt-4">
        <Button className="w-full justify-start gap-2" onClick={onAddProject} variant="outline">
          <FolderPlus className="h-4 w-4" />
          Add Project
        </Button>
      </footer>
    </aside>
  )
}
