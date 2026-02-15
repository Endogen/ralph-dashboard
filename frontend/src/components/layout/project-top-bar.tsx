import { Clock3, Coins, LoaderCircle, Wallet } from "lucide-react"

import { displayTokens } from "@/lib/utils"
import type { ProjectStatus } from "@/types/project"

type ProjectTopBarProps = {
  projectName: string
  status: ProjectStatus
  iterationLabel: string
  runtimeLabel: string
  tokensUsed: number
  estimatedCostUsd: number
}

type StatusMeta = {
  label: string
  className: string
}

const statusMeta: Record<ProjectStatus, StatusMeta> = {
  running: {
    label: "Running",
    className: "border-emerald-500/40 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  },
  paused: {
    label: "Paused",
    className: "border-amber-500/40 bg-amber-500/15 text-amber-700 dark:text-amber-300",
  },
  stopped: {
    label: "Stopped",
    className: "border-slate-500/40 bg-slate-500/15 text-slate-700 dark:text-slate-300",
  },
  complete: {
    label: "Complete",
    className: "border-teal-500/40 bg-teal-500/15 text-teal-700 dark:text-teal-300",
  },
  error: {
    label: "Error",
    className: "border-rose-500/40 bg-rose-500/15 text-rose-700 dark:text-rose-300",
  },
}

function formatCost(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function formatTokens(value: number): string {
  // Convert from k-tokens to actual tokens for display
  return new Intl.NumberFormat("en-US").format(displayTokens(value))
}

export function ProjectTopBar({
  projectName,
  status,
  iterationLabel,
  runtimeLabel,
  tokensUsed,
  estimatedCostUsd,
}: ProjectTopBarProps) {
  const meta = statusMeta[status]

  return (
    <header className="rounded-xl bg-background/50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{projectName}</h1>
          <p className="text-sm text-muted-foreground">Live project controls and analysis</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${meta.className}`}>
          {meta.label}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2 xl:grid-cols-4">
        <div className="flex items-center gap-2 rounded-lg bg-card/40 px-3 py-2">
          <LoaderCircle className="h-4 w-4 text-primary" />
          <span>{iterationLabel}</span>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-card/40 px-3 py-2">
          <Clock3 className="h-4 w-4 text-primary" />
          <span>{runtimeLabel}</span>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-card/40 px-3 py-2">
          <Coins className="h-4 w-4 text-primary" />
          <span>{formatTokens(tokensUsed)} tokens</span>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-card/40 px-3 py-2">
          <Wallet className="h-4 w-4 text-primary" />
          <span>{formatCost(estimatedCostUsd)}</span>
        </div>
      </div>
    </header>
  )
}
