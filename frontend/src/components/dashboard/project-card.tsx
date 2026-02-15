import { Clock3, Coins, GitBranch } from "lucide-react"

import { Button } from "@/components/ui/button"
import { displayTokens } from "@/lib/utils"
import type { ProjectStatus } from "@/types/project"

type IterationHealth = "productive" | "partial" | "failed"

type ProjectCardProps = {
  id: string
  name: string
  status: ProjectStatus
  currentIteration: number
  maxIterations: number
  totalTokens: number
  estimatedCostUsd: number
  lastActivityLabel: string
  healthStrip: IterationHealth[]
  onOpen?: (projectId: string) => void
}

const statusLabel: Record<ProjectStatus, string> = {
  running: "Running",
  paused: "Paused",
  stopped: "Stopped",
  complete: "Complete",
  error: "Error",
}

const statusClassName: Record<ProjectStatus, string> = {
  running: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  paused: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  stopped: "bg-slate-500/15 text-slate-700 dark:text-slate-300",
  complete: "bg-teal-500/15 text-teal-700 dark:text-teal-300",
  error: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
}

const healthCellClass: Record<IterationHealth, string> = {
  productive: "bg-emerald-500/80",
  partial: "bg-amber-500/80",
  failed: "bg-rose-500/80",
}

function formatTokens(tokens: number): string {
  // Convert from k-tokens to actual tokens for display
  return new Intl.NumberFormat("en-US").format(displayTokens(tokens))
}

function formatUsd(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function ProjectCard({
  id,
  name,
  status,
  currentIteration,
  maxIterations,
  totalTokens,
  estimatedCostUsd,
  lastActivityLabel,
  healthStrip,
  onOpen,
}: ProjectCardProps) {
  const progress = maxIterations > 0 ? Math.min((currentIteration / maxIterations) * 100, 100) : 0

  return (
    <article className="rounded-xl border bg-card p-4 shadow-sm transition hover:shadow-md">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">{name}</h3>
          <p className="text-xs text-muted-foreground">ID: {id}</p>
        </div>
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClassName[status]}`}>
          {statusLabel[status]}
        </span>
      </header>

      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Iteration {currentIteration}/{maxIterations}
          </span>
          <span>{progress.toFixed(0)}%</span>
        </div>
        <div className="h-2 rounded-full bg-muted">
          <div className="h-full rounded-full bg-primary" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg border bg-background/60 px-2 py-2">
          <dt className="flex items-center gap-1 text-xs text-muted-foreground">
            <Coins className="h-3 w-3" />
            Tokens
          </dt>
          <dd className="mt-1 font-medium">{formatTokens(totalTokens)}</dd>
        </div>
        <div className="rounded-lg border bg-background/60 px-2 py-2">
          <dt className="flex items-center gap-1 text-xs text-muted-foreground">
            <GitBranch className="h-3 w-3" />
            Cost
          </dt>
          <dd className="mt-1 font-medium">{formatUsd(estimatedCostUsd)}</dd>
        </div>
      </dl>

      <div className="mt-4">
        <p className="mb-2 flex items-center gap-1 text-xs text-muted-foreground">
          <Clock3 className="h-3 w-3" />
          {lastActivityLabel}
        </p>
        <div className="flex gap-1">
          {healthStrip.map((health, index) => (
            <span key={`${id}-health-${index}`} className={`h-2 flex-1 rounded-sm ${healthCellClass[health]}`} />
          ))}
        </div>
      </div>

      <Button className="mt-4 w-full" variant="outline" onClick={() => onOpen?.(id)}>
        Open Project
      </Button>
    </article>
  )
}
