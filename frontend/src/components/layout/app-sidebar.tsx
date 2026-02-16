import { Archive, CircleDot, FolderPlus, Gauge, MoonStar, PlayCircle, Square, Sun, TriangleAlert } from "lucide-react"
import { NavLink } from "react-router-dom"

import { Button } from "@/components/ui/button"
import type { ProjectStatus, ProjectSummary } from "@/types/project"

type AppSidebarProps = {
  projects: ProjectSummary[]
  onAddProject?: () => void
  resolvedTheme?: string
  toggleTheme?: () => void
  preference?: string
  setPreference?: (pref: "light" | "dark" | "system") => void
  connected?: boolean
  reconnecting?: boolean
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

export function AppSidebar({ projects, onAddProject, resolvedTheme, toggleTheme, preference, setPreference, connected, reconnecting }: AppSidebarProps) {
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive
        ? "bg-primary text-primary-foreground shadow-sm"
        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
    }`

  return (
    <aside className="hidden w-72 flex-col rounded-2xl border bg-card/75 p-4 shadow-xl shadow-slate-200/35 backdrop-blur-sm dark:shadow-slate-950/35 md:flex">
      <header className="space-y-1 border-b pb-4">
        <h1 className="text-lg font-semibold tracking-tight">Ralph Dashboard</h1>
        <p className="text-xs text-muted-foreground">Projects</p>
      </header>

      <nav className="mt-4 space-y-1">
        <NavLink to="/" className={navClass} end>
          <Gauge className="h-4 w-4" />
          Dashboard
        </NavLink>
        <NavLink to="/archive" className={navClass}>
          <Archive className="h-4 w-4" />
          Archive
        </NavLink>
      </nav>

      <div className="mt-4 flex-1 space-y-2">
        {projects.length === 0 && (
          <p className="rounded-lg border border-dashed px-3 py-4 text-xs text-muted-foreground">
            No registered projects yet.
          </p>
        )}
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

      <footer className="mt-4 space-y-3 border-t pt-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {toggleTheme && (
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
            )}
            {setPreference && (
              <button
                type="button"
                onClick={() => setPreference("system")}
                disabled={preference === "system"}
                className="rounded-md border bg-background/60 px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-background disabled:cursor-not-allowed disabled:opacity-60"
                title="Use system theme preference"
              >
                Auto
              </button>
            )}
          </div>
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
        <Button className="w-full justify-start gap-2" onClick={onAddProject} variant="outline">
          <FolderPlus className="h-4 w-4" />
          Add Project
        </Button>
      </footer>
    </aside>
  )
}
