import type { IterationSummary } from "@/types/project"

export type IterationHealthLevel = "productive" | "partial" | "failed"

export type IterationHealthSummary = {
  level: IterationHealthLevel
  label: string
  score: number
}

export const ITERATION_HEALTH_BADGE_CLASS: Record<IterationHealthLevel, string> = {
  productive: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  partial: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  failed: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
}

export const ITERATION_HEALTH_TIMELINE_CLASS: Record<IterationHealthLevel, string> = {
  productive: "bg-emerald-500/90 hover:bg-emerald-500",
  partial: "bg-amber-400/90 hover:bg-amber-400",
  failed: "bg-rose-500/90 hover:bg-rose-500",
}

export function evaluateIterationHealth(iteration: IterationSummary): IterationHealthSummary {
  const hasTasks = iteration.tasks_completed.length > 0
  const hasCommit = Boolean(iteration.commit)
  const hasErrors = iteration.has_errors || iteration.status === "error"
  const testsFailed = iteration.test_passed === false

  if (hasErrors || (testsFailed && !hasTasks)) {
    return {
      level: "failed",
      label: "Failed",
      score: 20,
    }
  }

  if (hasTasks && iteration.test_passed !== false) {
    return {
      level: "productive",
      label: "Productive",
      score: iteration.test_passed ? 95 : 85,
    }
  }

  if (hasTasks || hasCommit) {
    return {
      level: "partial",
      label: "Partial",
      score: testsFailed ? 50 : 65,
    }
  }

  return {
    level: "partial",
    label: "Partial",
    score: 55,
  }
}
