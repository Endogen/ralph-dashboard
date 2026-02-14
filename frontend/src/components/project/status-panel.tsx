import { Activity, Clock3, Cpu, Repeat2 } from "lucide-react"

import type { ProjectStatus } from "@/types/project"

type StatusPanelProps = {
  status: ProjectStatus
  iterationLabel: string
  runningFor: string
  cliLabel: string
  modeLabel: string
}

type StatusMeta = {
  label: string
  badgeClass: string
}

const statusMeta: Record<ProjectStatus, StatusMeta> = {
  running: {
    label: "Running",
    badgeClass: "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300",
  },
  paused: {
    label: "Paused",
    badgeClass: "bg-amber-500/20 text-amber-700 dark:text-amber-300",
  },
  stopped: {
    label: "Stopped",
    badgeClass: "bg-slate-500/20 text-slate-700 dark:text-slate-300",
  },
  complete: {
    label: "Complete",
    badgeClass: "bg-teal-500/20 text-teal-700 dark:text-teal-300",
  },
  error: {
    label: "Error",
    badgeClass: "bg-rose-500/20 text-rose-700 dark:text-rose-300",
  },
}

export function StatusPanel({ status, iterationLabel, runningFor, cliLabel, modeLabel }: StatusPanelProps) {
  const meta = statusMeta[status]

  return (
    <section className="rounded-xl border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Overview Status</h2>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${meta.badgeClass}`}>
          {meta.label}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-lg border bg-background/70 p-3">
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <Repeat2 className="h-3.5 w-3.5" />
            Iteration
          </p>
          <p className="mt-1 text-sm font-medium">{iterationLabel}</p>
        </div>
        <div className="rounded-lg border bg-background/70 p-3">
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock3 className="h-3.5 w-3.5" />
            Running Time
          </p>
          <p className="mt-1 text-sm font-medium">{runningFor}</p>
        </div>
        <div className="rounded-lg border bg-background/70 p-3">
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <Cpu className="h-3.5 w-3.5" />
            CLI
          </p>
          <p className="mt-1 text-sm font-medium">{cliLabel}</p>
        </div>
        <div className="rounded-lg border bg-background/70 p-3">
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <Activity className="h-3.5 w-3.5" />
            Mode
          </p>
          <p className="mt-1 text-sm font-medium">{modeLabel}</p>
        </div>
      </div>
    </section>
  )
}
