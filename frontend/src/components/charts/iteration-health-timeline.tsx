import { useMemo } from "react"

import { ITERATION_HEALTH_TIMELINE_CLASS, evaluateIterationHealth } from "@/lib/iteration-health"
import type { IterationSummary } from "@/types/project"

type IterationHealthTimelineProps = {
  iterations: IterationSummary[]
  onSelectIteration?: (iterationNumber: number) => void
}

type HealthPoint = {
  iteration: number
  health: "productive" | "partial" | "failed"
  label: string
  score: number
}

function classifyHealth(iteration: IterationSummary): HealthPoint {
  const summary = evaluateIterationHealth(iteration)
  return {
    iteration: iteration.number,
    health: summary.level,
    label: summary.label,
    score: summary.score,
  }
}

function healthClassName(health: "productive" | "partial" | "failed"): string {
  return ITERATION_HEALTH_TIMELINE_CLASS[health]
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
    <section className="max-w-full overflow-hidden rounded-xl border bg-card p-4">
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
                title={`Iteration ${point.iteration}: ${point.label} (${point.score})`}
                aria-label={`Iteration ${point.iteration}: ${point.label} (${point.score})`}
                className={`h-6 w-4 shrink-0 rounded-sm transition-colors ${healthClassName(point.health)}`}
              />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
