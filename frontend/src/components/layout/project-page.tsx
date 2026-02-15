import { useCallback, useEffect, useRef, useState } from "react"

import { useParams } from "react-router-dom"

import { apiFetch } from "@/api/client"
import { IterationHealthTimeline } from "@/components/charts/iteration-health-timeline"
import { ProgressTimelineChart } from "@/components/charts/progress-timeline-chart"
import { TaskBurndownChart } from "@/components/charts/task-burndown-chart"
import { TokenUsagePhaseChart } from "@/components/charts/token-usage-phase-chart"
import { ProjectControlBar } from "@/components/layout/project-control-bar"
import { ProjectTopBar } from "@/components/layout/project-top-bar"
import { PlanMarkdownEditor } from "@/components/project/plan-markdown-editor"
import { PlanRenderer } from "@/components/project/plan-renderer"
import { RecentActivityFeed } from "@/components/project/recent-activity-feed"
import { IterationsTable } from "@/components/project/iterations-table"
import { SpecFileBrowser } from "@/components/project/spec-file-browser"
import { StatsGrid } from "@/components/project/stats-grid"
import { StatusPanel } from "@/components/project/status-panel"
import { CodeFilesPane } from "@/components/project/code-files-pane"
import { ProjectConfigPanel } from "@/components/project/project-config-panel"
import { ProjectLogViewer } from "@/components/project/project-log-viewer"
import { Skeleton } from "@/components/ui/skeleton"
import { type WebSocketEnvelope, useWebSocket } from "@/hooks/use-websocket"
import { useActiveProjectStore } from "@/stores/active-project-store"
import { useToastStore } from "@/stores/toast-store"
import type {
  IterationListResponse,
  IterationSummary,
  NotificationEntry,
  ParsedImplementationPlan,
  ProjectStats,
} from "@/types/project"

type LiveLogChunk = {
  id: number
  lines: string
}

type TabKey = "overview" | "plan" | "iterations" | "specs" | "code" | "log" | "config"

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "plan", label: "Plan" },
  { key: "iterations", label: "Iterations" },
  { key: "specs", label: "Specs" },
  { key: "code", label: "Code" },
  { key: "log", label: "Log" },
  { key: "config", label: "Config" },
]

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

const TASK_CHECKBOX_RE = /^(\s*-\s+\[)([xX ])(\]\s+.*)$/

function taskOrdinalFromPlan(
  plan: ParsedImplementationPlan,
  phaseIndex: number,
  taskIndex: number,
): number | null {
  if (phaseIndex < 0 || phaseIndex >= plan.phases.length) {
    return null
  }

  let ordinal = 0
  for (const [currentPhaseIndex, phase] of plan.phases.entries()) {
    for (const [currentTaskIndex] of phase.tasks.entries()) {
      if (currentPhaseIndex === phaseIndex && currentTaskIndex === taskIndex) {
        return ordinal
      }
      ordinal += 1
    }
  }
  return null
}

function updateTaskCheckboxInRaw(planRaw: string, taskOrdinal: number, nextDone: boolean): string {
  const lines = planRaw.split(/\r?\n/)
  let currentOrdinal = 0
  let updated = false

  const nextLines = lines.map((line) => {
    const match = line.match(TASK_CHECKBOX_RE)
    if (!match) {
      return line
    }

    if (currentOrdinal === taskOrdinal) {
      updated = true
      currentOrdinal += 1
      return `${match[1]}${nextDone ? "x" : " "}${match[3]}`
    }

    currentOrdinal += 1
    return line
  })

  if (!updated) {
    throw new Error("Failed to locate task checkbox in plan markdown")
  }

  return nextLines.join("\n")
}

function buildTaskMetadata(
  iterations: IterationSummary[],
): Record<string, { iteration: number | null; commit: string | null }> {
  const ordered = [...iterations].sort((left, right) => left.number - right.number)
  const metadata: Record<string, { iteration: number | null; commit: string | null }> = {}

  for (const iteration of ordered) {
    for (const taskId of iteration.tasks_completed) {
      const normalized = taskId.trim()
      if (!normalized || metadata[normalized]) {
        continue
      }
      metadata[normalized] = {
        iteration: iteration.number,
        commit: iteration.commit,
      }
    }
  }

  return metadata
}

function ProjectPageSkeleton() {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border bg-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-2">
            <Skeleton className="h-7 w-56" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-9 w-28" />
        </div>
      </section>

      <section className="rounded-xl border bg-card p-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={`stat-skeleton-${index}`} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="mt-4 h-60 w-full" />
        <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Skeleton className="h-52 w-full" />
          <Skeleton className="h-52 w-full" />
        </div>
      </section>

      <section className="rounded-xl border bg-card p-4">
        <Skeleton className="h-10 w-40" />
        <Skeleton className="mt-3 h-56 w-full" />
      </section>

      <section className="rounded-xl border bg-card p-4">
        <Skeleton className="h-10 w-full" />
      </section>
    </div>
  )
}

export function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const activeProject = useActiveProjectStore((state) => state.activeProject)
  const fetchActiveProject = useActiveProjectStore((state) => state.fetchActiveProject)
  const clearActiveProject = useActiveProjectStore((state) => state.clearActiveProject)
  const projectLoading = useActiveProjectStore((state) => state.isLoading)
  const pushToast = useToastStore((state) => state.pushToast)

  const [iterations, setIterations] = useState<IterationSummary[]>([])
  const [notifications, setNotifications] = useState<NotificationEntry[]>([])
  const [plan, setPlan] = useState<ParsedImplementationPlan | null>(null)
  const [planDraft, setPlanDraft] = useState("")
  const [isRawPlanMode, setIsRawPlanMode] = useState(false)
  const [stats, setStats] = useState<ProjectStats | null>(null)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [overviewError, setOverviewError] = useState<string | null>(null)
  const [isSavingPlanTask, setIsSavingPlanTask] = useState(false)
  const [isSavingPlanRaw, setIsSavingPlanRaw] = useState(false)
  const [overviewRefreshToken, setOverviewRefreshToken] = useState(0)
  const [liveLogChunk, setLiveLogChunk] = useState<LiveLogChunk | null>(null)
  const refreshTimerRef = useRef<number | null>(null)
  const logChunkIdRef = useRef(0)

  // Tab state
  const [activeTab, setActiveTab] = useState<TabKey>("overview")
  const [hasUnreadLog, setHasUnreadLog] = useState(false)

  const queueOverviewRefresh = useCallback(() => {
    if (refreshTimerRef.current !== null) {
      return
    }
    refreshTimerRef.current = window.setTimeout(() => {
      setOverviewRefreshToken((token) => token + 1)
      refreshTimerRef.current = null
    }, 300)
  }, [])

  useEffect(() => {
    void fetchActiveProject(id ?? null)
    return () => {
      clearActiveProject()
    }
  }, [clearActiveProject, fetchActiveProject, id])

  useEffect(() => {
    return () => {
      if (refreshTimerRef.current !== null) {
        window.clearTimeout(refreshTimerRef.current)
      }
    }
  }, [])

  useEffect(() => {
    setLiveLogChunk(null)
    logChunkIdRef.current = 0
    setHasUnreadLog(false)
  }, [id])

  // Clear unread indicator when switching to Log tab
  useEffect(() => {
    if (activeTab === "log") {
      setHasUnreadLog(false)
    }
  }, [activeTab])

  const handleOverviewSocketEvent = useCallback(
    (event: WebSocketEnvelope) => {
      if (!id || event.project !== id) {
        return
      }

      if (event.type === "log_append") {
        if (!event.data || typeof event.data !== "object") {
          return
        }
        const lines = (event.data as { lines?: unknown }).lines
        if (typeof lines !== "string" || lines.length === 0) {
          return
        }
        logChunkIdRef.current += 1
        setLiveLogChunk({ id: logChunkIdRef.current, lines })
        // Mark log as unread (the effect reading activeTab via ref would be stale,
        // so we use functional update and let the "log" tab effect clear it)
        setHasUnreadLog(true)
        return
      }

      const shouldRefresh =
        event.type === "iteration_started" ||
        event.type === "iteration_completed" ||
        event.type === "plan_updated" ||
        event.type === "notification" ||
        event.type === "status_changed"

      if (shouldRefresh) {
        queueOverviewRefresh()
      }
    },
    [id, queueOverviewRefresh],
  )

  useWebSocket({
    enabled: Boolean(id),
    projects: id ? [id] : [],
    onEvent: handleOverviewSocketEvent,
  })

  useEffect(() => {
    let cancelled = false

    const loadOverview = async () => {
      if (!id) {
        setIterations([])
        setNotifications([])
        setPlan(null)
        setPlanDraft("")
        setIsRawPlanMode(false)
        setStats(null)
        setOverviewError(null)
        setOverviewLoading(false)
        return
      }

      setOverviewLoading(true)
      setOverviewError(null)

      try {
        const [iterationsResult, statsResult, notificationsResult, planResult] = await Promise.allSettled([
          apiFetch<IterationListResponse>(`/projects/${id}/iterations?status=all&limit=500`),
          apiFetch<ProjectStats>(`/projects/${id}/stats`),
          apiFetch<NotificationEntry[]>(`/projects/${id}/notifications`),
          apiFetch<ParsedImplementationPlan>(`/projects/${id}/plan`),
        ])
        if (cancelled) {
          return
        }

        const errorMessages: string[] = []

        if (iterationsResult.status === "fulfilled") {
          setIterations(iterationsResult.value.iterations)
        } else {
          setIterations([])
          errorMessages.push("iterations")
        }

        if (statsResult.status === "fulfilled") {
          setStats(statsResult.value)
        } else {
          setStats(null)
          errorMessages.push("stats")
        }

        if (notificationsResult.status === "fulfilled") {
          setNotifications(notificationsResult.value)
        } else {
          setNotifications([])
          errorMessages.push("notifications")
        }

        if (planResult.status === "fulfilled") {
          setPlan(planResult.value)
          if (!isRawPlanMode) {
            setPlanDraft(planResult.value.raw)
          }
        } else {
          setPlan(null)
          if (!isRawPlanMode) {
            setPlanDraft("")
          }
          errorMessages.push("plan")
        }

        if (errorMessages.length > 0) {
          setOverviewError(`Partial data unavailable (${errorMessages.join(", ")}).`)
        }
      } catch (error) {
        if (cancelled) {
          return
        }
        const message = error instanceof Error ? error.message : "Failed to load overview data"
        setOverviewError(message)
        setIterations([])
        setNotifications([])
        setPlan(null)
        setPlanDraft("")
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
  }, [id, isRawPlanMode, overviewRefreshToken])

  useEffect(() => {
    if (plan && !isRawPlanMode) {
      setPlanDraft(plan.raw)
    }
  }, [isRawPlanMode, plan])

  const handleTogglePlanTask = useCallback(
    async (phaseIndex: number, taskIndex: number, nextDone: boolean) => {
      if (!id || !plan) {
        return
      }

      const taskOrdinal = taskOrdinalFromPlan(plan, phaseIndex, taskIndex)
      if (taskOrdinal === null) {
        return
      }

      let nextContent: string
      try {
        nextContent = updateTaskCheckboxInRaw(plan.raw, taskOrdinal, nextDone)
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to update plan markdown"
        setOverviewError(message)
        pushToast({
          title: "Plan update failed",
          description: message,
          tone: "error",
        })
        return
      }

      setIsSavingPlanTask(true)
      try {
        const updatedPlan = await apiFetch<ParsedImplementationPlan>(`/projects/${id}/plan`, {
          method: "PUT",
          body: JSON.stringify({ content: nextContent }),
        })
        setPlan(updatedPlan)
        if (!isRawPlanMode) {
          setPlanDraft(updatedPlan.raw)
        }
        setOverviewError(null)
        queueOverviewRefresh()
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to save plan task"
        setOverviewError(message)
        pushToast({
          title: "Plan task save failed",
          description: message,
          tone: "error",
        })
      } finally {
        setIsSavingPlanTask(false)
      }
    },
    [id, isRawPlanMode, plan, pushToast, queueOverviewRefresh],
  )

  const handleSavePlanRaw = useCallback(async () => {
    if (!id) {
      return
    }

    setIsSavingPlanRaw(true)
    try {
      const updatedPlan = await apiFetch<ParsedImplementationPlan>(`/projects/${id}/plan`, {
        method: "PUT",
        body: JSON.stringify({ content: planDraft }),
      })
      setPlan(updatedPlan)
      setPlanDraft(updatedPlan.raw)
      setIsRawPlanMode(false)
      setOverviewError(null)
      queueOverviewRefresh()
      pushToast({
        title: "Plan saved",
        description: "IMPLEMENTATION_PLAN.md updated",
        tone: "success",
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save plan markdown"
      setOverviewError(message)
      pushToast({
        title: "Plan save failed",
        description: message,
        tone: "error",
      })
    } finally {
      setIsSavingPlanRaw(false)
    }
  }, [id, planDraft, pushToast, queueOverviewRefresh])

  const toggleRawPlanMode = useCallback(() => {
    if (!isRawPlanMode && plan) {
      setPlanDraft(plan.raw)
    }
    setIsRawPlanMode((current) => !current)
  }, [isRawPlanMode, plan])

  const sortedIterations = [...iterations].sort((left, right) => left.number - right.number)
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
  const taskMetadata = buildTaskMetadata(sortedIterations)
  const isInitialLoading =
    (projectLoading || overviewLoading) &&
    !activeProject &&
    iterations.length === 0 &&
    notifications.length === 0 &&
    !stats &&
    !plan

  if (isInitialLoading) {
    return <ProjectPageSkeleton />
  }

  const renderTabContent = () => {
    // Loading/error shown inside the active tab area
    if (projectLoading || overviewLoading) {
      return (
        <p className="py-8 text-center text-sm text-muted-foreground">Loading project details...</p>
      )
    }

    if (overviewError) {
      return (
        <p className="py-8 text-center text-sm text-rose-600 dark:text-rose-400">
          {overviewError}
        </p>
      )
    }

    switch (activeTab) {
      case "overview":
        return (
          <div className="space-y-4">
            <StatusPanel
              status={status}
              iterationLabel={iterationLabel}
              runningFor={runtimeLabel}
              cliLabel="codex"
              modeLabel={modeLabel}
            />

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

            <div className="overflow-hidden">
              <ProgressTimelineChart iterations={sortedIterations} tasksTotal={tasksTotal} />
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <div className="overflow-hidden">
                <TaskBurndownChart iterations={sortedIterations} tasksTotal={tasksTotal} />
              </div>
              <div className="overflow-hidden">
                <TokenUsagePhaseChart data={stats?.tokens_by_phase ?? []} totalTokens={tokensUsed} />
              </div>
            </div>

            <div className="overflow-hidden">
              <IterationHealthTimeline iterations={sortedIterations} />
            </div>

            <RecentActivityFeed iterations={sortedIterations} notifications={notifications} />
          </div>
        )

      case "plan":
        return (
          <div className="space-y-3">
            <div className="flex justify-end">
              <button
                type="button"
                onClick={toggleRawPlanMode}
                className="rounded-md border bg-background px-3 py-1.5 text-sm font-medium hover:bg-background/80"
              >
                {isRawPlanMode ? "Rendered View" : "Raw Markdown Mode"}
              </button>
            </div>

            {isRawPlanMode ? (
              <PlanMarkdownEditor
                value={planDraft}
                onChange={setPlanDraft}
                onSave={handleSavePlanRaw}
                isSaving={isSavingPlanRaw}
              />
            ) : (
              <PlanRenderer
                plan={plan}
                projectId={id}
                taskMetadata={taskMetadata}
                isLoading={overviewLoading}
                onToggleTask={handleTogglePlanTask}
                isSavingTask={isSavingPlanTask || isSavingPlanRaw}
              />
            )}
          </div>
        )

      case "iterations":
        return (
          <div className="max-w-full overflow-x-auto">
            <IterationsTable
              iterations={iterations}
              projectId={id}
              isLoading={overviewLoading}
            />
          </div>
        )

      case "specs":
        return <SpecFileBrowser projectId={id} />

      case "code":
        return (
          <div className="overflow-hidden">
            <CodeFilesPane projectId={id} />
          </div>
        )

      case "log":
        return (
          <div className="overflow-hidden">
            <ProjectLogViewer projectId={id} liveChunk={liveLogChunk} />
          </div>
        )

      case "config":
        return <ProjectConfigPanel projectId={id} projectPath={activeProject?.path ?? null} />

      default:
        return null
    }
  }

  return (
    <div className="flex min-h-0 flex-col gap-4">
      {/* Top bar — always visible */}
      <ProjectTopBar
        projectName={projectName}
        status={status}
        iterationLabel={iterationLabel}
        runtimeLabel={runtimeLabel}
        tokensUsed={tokensUsed}
        estimatedCostUsd={estimatedCostUsd}
      />

      {/* Tab bar */}
      <nav className="-mb-2 overflow-x-auto border-b border-border" aria-label="Project tabs">
        <div className="flex min-w-max">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`relative shrink-0 px-4 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                activeTab === tab.key
                  ? "text-foreground after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary"
                  : "text-muted-foreground hover:text-foreground/80"
              }`}
            >
              {tab.label}
              {/* Unread log dot */}
              {tab.key === "log" && hasUnreadLog && activeTab !== "log" && (
                <span className="absolute -top-0.5 right-1 size-2 rounded-full bg-primary" />
              )}
            </button>
          ))}
        </div>
      </nav>

      {/* Active tab content */}
      <section className="min-h-0 overflow-hidden rounded-xl border bg-card p-4 sm:p-6">
        {renderTabContent()}
      </section>

      {/* Control bar — always visible at bottom */}
      <ProjectControlBar
        status={status}
        iterationLabel={iterationLabel}
        runtimeLabel={runtimeLabel}
        tokensUsed={tokensUsed}
      />
    </div>
  )
}
