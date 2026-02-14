import { useMemo } from "react"

import type { IterationSummary } from "@/types/project"

type IterationHealthTimelineProps = {
  iterations: IterationSummary[]
  onSelectIteration?: (iterationNumber: number) => void
}

type HealthLevel = "productive" | "partial" | "failed"

type HealthPoint = {
  iteration: number
  health: HealthLevel
  label: string
}

function classifyHealth(iteration: IterationSummary): HealthPoint {
  const hasTasks = iteration.tasks_completed.length > 0
  const hasCommit = Boolean(iteration.commit)
  const hasErrors = iteration.has_errors || iteration.status === "error"
  const testsFailed = iteration.test_passed === false

  if (hasErrors || (testsFailed && !hasTasks)) {
    return {
      iteration: iteration.number,
      health: "failed",
      label: "Failed",
    }
  }

  if (hasTasks && iteration.test_passed !== false) {
    return {
      iteration: iteration.number,
      health: "productive",
      label: "Productive",
    }
  }

  if (hasTasks || hasCommit) {
    return {
      iteration: iteration.number,
      health: "partial",
      label: "Partial",
    }
  }

  return {
    iteration: iteration.number,
    health: "partial",
    label: "Partial",
  }
}

function healthClassName(health: HealthLevel): string {
  if (health === "productive") {
    return "bg-emerald-500/90 hover:bg-emerald-500"
  }
  if (health === "failed") {
    return "bg-rose-500/90 hover:bg-rose-500"
  }
  return "bg-amber-400/90 hover:bg-amber-400"
}

export function IterationHealthTimeline({
  iterations,
  onSelectIteration,
}: IterationHealthTimelineProps) {
  const points = useMemo(
    () => [...iterations].sort((left, right) => left.number - right.number).map(classifyHealth),
    [iterations],
  )

  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Iteration Health Timeline</h3>
        <p className="text-sm text-muted-foreground">
          Productive (green), partial (yellow), and failed (red) iteration outcomes.
        </p>
      </header>

      {points.length === 0 ? (
        <div className="flex h-[96px] items-center justify-center rounded-lg border bg-background/40 text-sm text-muted-foreground">
          No iteration health data yet.
        </div>
      ) : (
        <>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
              Productive
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-sm bg-amber-400" />
              Partial
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-sm bg-rose-500" />
              Failed
            </span>
          </div>

          <div className="mt-3 flex items-center gap-1 overflow-x-auto pb-1">
            {points.map((point) => (
              <button
                key={point.iteration}
                type="button"
                onClick={() => onSelectIteration?.(point.iteration)}
                title={`Iteration ${point.iteration}: ${point.label}`}
                aria-label={`Iteration ${point.iteration}: ${point.label}`}
                className={`h-6 w-4 shrink-0 rounded-sm transition-colors ${healthClassName(point.health)}`}
              />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
