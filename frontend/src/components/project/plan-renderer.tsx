import { useEffect, useState } from "react"

import { ChevronDown, ChevronRight } from "lucide-react"

import type { ParsedImplementationPlan } from "@/types/project"

type PlanRendererProps = {
  plan: ParsedImplementationPlan | null
  isLoading: boolean
}

type StatusMeta = {
  label: string
  className: string
}

const phaseStatusMeta: Record<"pending" | "in_progress" | "complete", StatusMeta> = {
  pending: {
    label: "Pending",
    className: "bg-slate-500/15 text-slate-700 dark:text-slate-300",
  },
  in_progress: {
    label: "In Progress",
    className: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  },
  complete: {
    label: "Complete",
    className: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  },
}

function percentage(done: number, total: number): number {
  if (total <= 0) {
    return 0
  }
  return Math.round((done / total) * 100)
}

export function PlanRenderer({ plan, isLoading }: PlanRendererProps) {
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!plan || plan.phases.length === 0) {
      setExpandedPhases(new Set())
      return
    }

    const next = new Set<string>()
    for (const phase of plan.phases) {
      if (phase.status !== "complete") {
        next.add(phase.name)
      }
    }
    if (next.size === 0) {
      next.add(plan.phases[0].name)
    }
    setExpandedPhases(next)
  }, [plan])

  const togglePhase = (phaseName: string) => {
    setExpandedPhases((current) => {
      const next = new Set(current)
      if (next.has(phaseName)) {
        next.delete(phaseName)
      } else {
        next.add(phaseName)
      }
      return next
    })
  }

  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Implementation Plan</h3>
        <p className="text-sm text-muted-foreground">
          Collapsible phase view with completion state and checklist rendering.
        </p>
      </header>

      {isLoading && !plan ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-muted-foreground">
          Loading implementation plan...
        </div>
      ) : !plan || plan.phases.length === 0 ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-muted-foreground">
          No implementation plan tasks found.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-lg border bg-background/50 p-3">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="font-medium">Overall Progress</span>
              <span className="text-muted-foreground">
                {plan.tasks_done}/{plan.tasks_total}
              </span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200/70 dark:bg-slate-800">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${percentage(plan.tasks_done, plan.tasks_total)}%` }}
              />
            </div>
          </div>

          {plan.phases.map((phase) => {
            const isExpanded = expandedPhases.has(phase.name)
            const statusMeta = phaseStatusMeta[phase.status]

            return (
              <article key={phase.name} className="rounded-lg border bg-background/30">
                <button
                  type="button"
                  onClick={() => togglePhase(phase.name)}
                  className="flex w-full items-start justify-between gap-3 px-3 py-3 text-left"
                >
                  <div className="flex min-w-0 flex-1 gap-2">
                    <span className="mt-0.5 text-muted-foreground">
                      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{phase.name}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {phase.done_count}/{phase.total_count} tasks ({percentage(phase.done_count, phase.total_count)}
                        %)
                      </p>
                    </div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusMeta.className}`}>
                    {statusMeta.label}
                  </span>
                </button>

                <div className="px-3 pb-3">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200/70 dark:bg-slate-800">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${percentage(phase.done_count, phase.total_count)}%` }}
                    />
                  </div>
                </div>

                {isExpanded && (
                  <ul className="space-y-2 border-t px-3 py-3">
                    {phase.tasks.map((task, index) => (
                      <li
                        key={`${phase.name}-${task.id ?? "task"}-${index}`}
                        className="rounded-md bg-background/50 px-2 py-2"
                        style={{ marginLeft: `${Math.min(task.indent, 12)}px` }}
                      >
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={task.done}
                            readOnly
                            disabled
                            className="h-4 w-4 rounded border-slate-300 text-primary"
                          />
                          <span className={task.done ? "text-muted-foreground line-through" : ""}>
                            {task.id ? `${task.id}: ` : ""}
                            {task.description}
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
