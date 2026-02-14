import { useEffect, useMemo, useState } from "react"

import { useParams } from "react-router-dom"

import { apiFetch } from "@/api/client"
import { ProgressTimelineChart } from "@/components/charts/progress-timeline-chart"
import { TaskBurndownChart } from "@/components/charts/task-burndown-chart"
import { ProjectControlBar } from "@/components/layout/project-control-bar"
import { ProjectTopBar } from "@/components/layout/project-top-bar"
import { StatsGrid } from "@/components/project/stats-grid"
import { StatusPanel } from "@/components/project/status-panel"
import { useActiveProjectStore } from "@/stores/active-project-store"
import type { IterationListResponse, IterationSummary, ProjectStats } from "@/types/project"

function formatDuration(valueInSeconds: number): string {
  if (!Number.isFinite(valueInSeconds) || valueInSeconds <= 0) {
    return "0m"
  }

  const totalSeconds = Math.round(valueInSeconds)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }
  return `${seconds}s`
}

export function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const activeProject = useActiveProjectStore((state) => state.activeProject)
  const fetchActiveProject = useActiveProjectStore((state) => state.fetchActiveProject)
  const clearActiveProject = useActiveProjectStore((state) => state.clearActiveProject)
  const projectLoading = useActiveProjectStore((state) => state.isLoading)

  const [iterations, setIterations] = useState<IterationSummary[]>([])
  const [stats, setStats] = useState<ProjectStats | null>(null)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [overviewError, setOverviewError] = useState<string | null>(null)

  useEffect(() => {
    void fetchActiveProject(id ?? null)
    return () => {
      clearActiveProject()
    }
  }, [clearActiveProject, fetchActiveProject, id])

  useEffect(() => {
    let cancelled = false

    const loadOverview = async () => {
      if (!id) {
        setIterations([])
        setStats(null)
        setOverviewError(null)
        setOverviewLoading(false)
        return
      }

      setOverviewLoading(true)
      setOverviewError(null)

      try {
        const [iterationsResponse, statsResponse] = await Promise.all([
          apiFetch<IterationListResponse>(`/projects/${id}/iterations?status=all&limit=500`),
          apiFetch<ProjectStats>(`/projects/${id}/stats`),
        ])
        if (cancelled) {
          return
        }
        setIterations(iterationsResponse.iterations)
        setStats(statsResponse)
      } catch (error) {
        if (cancelled) {
          return
        }
        const message = error instanceof Error ? error.message : "Failed to load overview data"
        setOverviewError(message)
        setIterations([])
        setStats(null)
      } finally {
        if (!cancelled) {
          setOverviewLoading(false)
        }
      }
    }

    void loadOverview()

    return () => {
      cancelled = true
    }
  }, [id])

  const sortedIterations = useMemo(
    () => [...iterations].sort((left, right) => left.number - right.number),
    [iterations],
  )
  const latestIteration = sortedIterations[sortedIterations.length - 1]
  const iterationLabel =
    latestIteration && latestIteration.max_iterations
      ? `Iteration ${latestIteration.number}/${latestIteration.max_iterations}`
      : latestIteration
        ? `Iteration ${latestIteration.number}`
        : "Iteration n/a"
  const runtimeLabel = `Running for ${formatDuration(stats?.total_duration_seconds ?? 0)}`

  const tokensUsed = stats?.total_tokens ?? 0
  const estimatedCostUsd = stats?.total_cost_usd ?? 0
  const tasksCompleted = stats?.tasks_done ?? 0
  const tasksTotal = stats?.tasks_total ?? 0
  const iterationsCompleted = stats?.total_iterations ?? 0
  const errorCount = stats?.errors_count ?? 0
  const successRate =
    iterationsCompleted > 0 ? ((iterationsCompleted - errorCount) / iterationsCompleted) * 100 : 0

  const projectName = activeProject?.name ?? id ?? "Unknown Project"
  const status = activeProject?.status ?? "stopped"
  const modeLabel = status === "running" || status === "paused" ? "BUILDING" : "READY"

  return (
    <div className="space-y-4">
      <ProjectTopBar
        projectName={projectName}
        status={status}
        iterationLabel={iterationLabel}
        runtimeLabel={runtimeLabel}
        tokensUsed={tokensUsed}
        estimatedCostUsd={estimatedCostUsd}
      />

      <section className="rounded-xl border bg-card p-6">
        <StatusPanel
          status={status}
          iterationLabel={iterationLabel}
          runningFor={runtimeLabel}
          cliLabel="codex"
          modeLabel={modeLabel}
        />

        <div className="mt-4">
          <StatsGrid
            totalTokens={tokensUsed}
            estimatedCostUsd={estimatedCostUsd}
            iterationsCompleted={iterationsCompleted}
            averageIterationDuration={formatDuration(stats?.avg_iteration_duration_seconds ?? 0)}
            tasksCompleted={tasksCompleted}
            tasksTotal={tasksTotal}
            errorCount={errorCount}
            successRate={successRate}
          />
        </div>

        <div className="mt-4">
          <ProgressTimelineChart iterations={sortedIterations} tasksTotal={tasksTotal} />
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
          <TaskBurndownChart iterations={sortedIterations} tasksTotal={tasksTotal} />

          <section className="rounded-xl border bg-background/50 p-4">
            <h3 className="text-base font-semibold">Token Usage by Phase</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Phase-token donut visualization is queued in task 11.5.
            </p>
          </section>
        </div>

        <div className="mt-4 rounded-xl border bg-background/50 p-4">
          <h3 className="text-base font-semibold">Next Overview Widgets</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Iteration health timeline and recent activity feed are queued in tasks 11.6 and 11.7.
          </p>
        </div>
        {(projectLoading || overviewLoading) && (
          <p className="mt-3 text-sm text-muted-foreground">Loading project details...</p>
        )}
        {overviewError && (
          <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">
            Failed to load overview metrics ({overviewError}).
          </p>
        )}
      </section>

      <ProjectControlBar
        status={status}
        iterationLabel={iterationLabel}
        runtimeLabel={runtimeLabel}
        tokensUsed={tokensUsed}
      />
    </div>
  )
}
