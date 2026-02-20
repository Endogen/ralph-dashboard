import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { useLocation, useNavigate, useParams } from "react-router-dom"

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
import { ControlFilesPane } from "@/components/project/control-files-pane"
import { StatsGrid } from "@/components/project/stats-grid"
import { StatusPanel } from "@/components/project/status-panel"
import { CodeFilesPane } from "@/components/project/code-files-pane"
import { ProjectConfigPanel } from "@/components/project/project-config-panel"
import { SystemPanel } from "@/components/project/system-panel"
import { ProjectLogViewer } from "@/components/project/project-log-viewer"
import { Skeleton } from "@/components/ui/skeleton"
import { type WebSocketEnvelope, useWebSocket } from "@/hooks/use-websocket"
import { requestNotificationPermission, showBrowserNotification } from "@/lib/browser-notifications"
import { useActiveProjectStore } from "@/stores/active-project-store"
import { useToastStore } from "@/stores/toast-store"
import type {
  IterationListResponse,
  IterationSummary,
  LoopConfig,
  NotificationEntry,
  ParsedImplementationPlan,
  ProjectStatus,
  ProjectStats,
} from "@/types/project"

type LiveLogChunk = {
  id: number
  lines: string
}

type TabKey = "overview" | "plan" | "iterations" | "specs" | "code" | "log" | "config" | "system"

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "plan", label: "Plan" },
  { key: "iterations", label: "Iterations" },
  { key: "specs", label: "Specs" },
  { key: "code", label: "Code" },
  { key: "log", label: "Log" },
  { key: "config", label: "Config" },
  { key: "system", label: "System" },
]
const VALID_PROJECT_STATUSES = new Set<ProjectStatus>([
  "running",
  "paused",
  "stopped",
  "complete",
  "error",
])

function parseTabFromSearch(search: string): TabKey | null {
  const value = new URLSearchParams(search).get("tab")
  if (!value) {
    return null
  }
  return TABS.some((tab) => tab.key === value) ? (value as TabKey) : null
}

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
  const location = useLocation()
  const navigate = useNavigate()
  const activeProject = useActiveProjectStore((state) => state.activeProject)
  const fetchActiveProject = useActiveProjectStore((state) => state.fetchActiveProject)
  const patchActiveProject = useActiveProjectStore((state) => state.patchActiveProject)
  const clearActiveProject = useActiveProjectStore((state) => state.clearActiveProject)
  const projectLoading = useActiveProjectStore((state) => state.isLoading)
  const pushToast = useToastStore((state) => state.pushToast)

  const [iterations, setIterations] = useState<IterationSummary[]>([])
  const [notifications, setNotifications] = useState<NotificationEntry[]>([])
  const [plan, setPlan] = useState<ParsedImplementationPlan | null>(null)
  const [planDraft, setPlanDraft] = useState("")
  const [isRawPlanMode, setIsRawPlanMode] = useState(false)
  const isRawPlanModeRef = useRef(false)
  const [stats, setStats] = useState<ProjectStats | null>(null)
  const [cliLabel, setCliLabel] = useState("codex")
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [overviewError, setOverviewError] = useState<string | null>(null)
  const isSavingPlanTask = false // read-only; toggling disabled
  const [isSavingPlanRaw, setIsSavingPlanRaw] = useState(false)
  const [overviewRefreshToken, setOverviewRefreshToken] = useState(0)
  const [liveLogChunk, setLiveLogChunk] = useState<LiveLogChunk | null>(null)
  const refreshTimerRef = useRef<number | null>(null)
  const logChunkIdRef = useRef(0)
  const initialFetchDoneRef = useRef(false)

  // Tab state
  const initialTab = parseTabFromSearch(location.search) ?? "overview"
  const [activeTab, setActiveTab] = useState<TabKey>(initialTab)
  const activeTabRef = useRef<TabKey>(initialTab)
  const [hasUnreadLog, setHasUnreadLog] = useState(false)
  const selectedCommitHash = useMemo(() => {
    const value = new URLSearchParams(location.search).get("commit")
    const trimmed = value?.trim() ?? ""
    return trimmed.length > 0 ? trimmed : null
  }, [location.search])

  // Track whether we've already fired a browser notification for completion
  const completionNotifiedRef = useRef(false)

  // Ref for activeProject name to avoid stale closures in socket handler
  const projectNameRef = useRef(activeProject?.name)
  useEffect(() => {
    projectNameRef.current = activeProject?.name
  }, [activeProject?.name])

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
    initialFetchDoneRef.current = false
    completionNotifiedRef.current = false
  }, [id])

  // Clear unread indicator when switching to Log tab
  useEffect(() => {
    activeTabRef.current = activeTab
    if (activeTab === "log") {
      setHasUnreadLog(false)
    }
  }, [activeTab])

  useEffect(() => {
    const requestedTab = parseTabFromSearch(location.search) ?? "overview"
    if (requestedTab !== activeTabRef.current) {
      setActiveTab(requestedTab)
    }
  }, [location.search])

  // Request browser notification permission on first project page visit
  useEffect(() => {
    void requestNotificationPermission()
  }, [])

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
        if (activeTabRef.current !== "log") {
          setHasUnreadLog(true)
        }
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

      if (event.type === "status_changed" && event.data && typeof event.data === "object") {
        const status = (event.data as { status?: string }).status
        if (status && VALID_PROJECT_STATUSES.has(status as ProjectStatus)) {
          patchActiveProject(id, { status: status as ProjectStatus })
        }
      }

      // Browser notification on project completion
      if (!completionNotifiedRef.current && event.data && typeof event.data === "object") {
        const data = event.data as Record<string, unknown>
        const isComplete =
          (event.type === "plan_updated" && typeof data.status === "string" && data.status.toUpperCase() === "COMPLETE") ||
          (event.type === "notification" && data.prefix === "DONE")

        if (isComplete) {
          completionNotifiedRef.current = true
          const name = projectNameRef.current ?? id ?? "Project"
          void showBrowserNotification({
            title: `✅ ${name} — Complete`,
            body: "All tasks finished successfully.",
            tag: `ralph-complete-${id}`,
            onClick: () => window.focus(),
          })
          pushToast({
            title: `${name} complete!`,
            description: "All tasks in the implementation plan are done.",
            tone: "success",
          })
        }
      }
    },
    [id, queueOverviewRefresh, pushToast, patchActiveProject],
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

      // Only show loading spinner on the initial fetch — background
      // refreshes (triggered by WebSocket events) update data silently
      // so child components keep their local state (expanded rows, etc.)
      const isBackgroundRefresh = initialFetchDoneRef.current
      if (!isBackgroundRefresh) {
        setOverviewLoading(true)
      }
      setOverviewError(null)

      try {
        const [iterationsResult, statsResult, notificationsResult, planResult, configResult] = await Promise.allSettled([
          apiFetch<IterationListResponse>(`/projects/${id}/iterations?status=all&limit=500`),
          apiFetch<ProjectStats>(`/projects/${id}/stats`),
          apiFetch<NotificationEntry[]>(`/projects/${id}/notifications`),
          apiFetch<ParsedImplementationPlan>(`/projects/${id}/plan`),
          apiFetch<LoopConfig>(`/projects/${id}/config`),
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

        if (configResult.status === "fulfilled") {
          setCliLabel(configResult.value.cli || "codex")
        }

        if (planResult.status === "fulfilled") {
          setPlan(planResult.value)
          if (!isRawPlanModeRef.current) {
            setPlanDraft(planResult.value.raw)
          }
        } else {
          setPlan(null)
          if (!isRawPlanModeRef.current) {
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
          initialFetchDoneRef.current = true
          if (!isBackgroundRefresh) {
            setOverviewLoading(false)
          }
        }
      }
    }

    void loadOverview()

    return () => {
      cancelled = true
    }
  }, [id, overviewRefreshToken])

  useEffect(() => {
    if (plan && !isRawPlanMode) {
      setPlanDraft(plan.raw)
    }
  }, [isRawPlanMode, plan])

  // Plan task checkboxes are read-only — toggling is disabled to avoid
  // conflicts with an actively running Ralph loop that manages the plan file.

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
    setIsRawPlanMode((current) => {
      const next = !current
      isRawPlanModeRef.current = next
      return next
    })
  }, [isRawPlanMode, plan])

  const handleTabChange = useCallback(
    (tab: TabKey) => {
      setActiveTab(tab)
      const params = new URLSearchParams(location.search)
      params.set("tab", tab)
      if (tab !== "code") {
        params.delete("commit")
      }
      const nextSearch = params.toString()
      const currentSearch = location.search.startsWith("?") ? location.search.slice(1) : location.search
      if (nextSearch !== currentSearch) {
        navigate(
          {
            pathname: id ? `/project/${id}` : location.pathname,
            search: nextSearch ? `?${nextSearch}` : "",
          },
          { replace: false },
        )
      }
      // Reset scroll position to prevent left-clipping on mobile
      window.scrollTo({ left: 0 })
    },
    [id, location.pathname, location.search, navigate],
  )

  const sortedIterations = [...iterations].sort((left, right) => left.number - right.number)
  const latestIteration = sortedIterations[sortedIterations.length - 1]
  const iterationLabel =
    latestIteration
      ? latestIteration.max_iterations === 0
        ? `Iteration ${latestIteration.number}/∞`
        : latestIteration.max_iterations
          ? `Iteration ${latestIteration.number}/${latestIteration.max_iterations}`
          : `Iteration ${latestIteration.number}`
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

  // --- Control bar handlers ---
  const handleStart = useCallback(async () => {
    if (!id) return
    try {
      await apiFetch(`/projects/${id}/start`, { method: "POST", body: JSON.stringify({}) })
      pushToast({ title: "Loop started", description: "Ralph loop is starting…", tone: "success" })
      queueOverviewRefresh()
      void fetchActiveProject(id)
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to start loop"
      pushToast({ title: "Start failed", description: msg, tone: "error" })
    }
  }, [id, pushToast, queueOverviewRefresh, fetchActiveProject])

  const handleStop = useCallback(async () => {
    if (!id) return
    try {
      const result = await apiFetch<{ stopped: boolean }>(`/projects/${id}/stop`, { method: "POST" })
      if (result.stopped) {
        pushToast({ title: "Loop stopped", description: "Process terminated", tone: "success" })
      } else {
        pushToast({ title: "Nothing to stop", description: "No running process found", tone: "info" })
      }
      queueOverviewRefresh()
      void fetchActiveProject(id)
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to stop loop"
      pushToast({ title: "Stop failed", description: msg, tone: "error" })
    }
  }, [id, pushToast, queueOverviewRefresh, fetchActiveProject])

  const handlePause = useCallback(async () => {
    if (!id) return
    try {
      await apiFetch(`/projects/${id}/pause`, { method: "POST" })
      pushToast({ title: "Loop paused", description: "Will pause after current iteration", tone: "success" })
      queueOverviewRefresh()
      void fetchActiveProject(id)
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to pause loop"
      pushToast({ title: "Pause failed", description: msg, tone: "error" })
    }
  }, [id, pushToast, queueOverviewRefresh, fetchActiveProject])

  const handleResume = useCallback(async () => {
    if (!id) return
    try {
      await apiFetch(`/projects/${id}/resume`, { method: "POST" })
      pushToast({ title: "Loop resumed", description: "Resuming iterations", tone: "success" })
      queueOverviewRefresh()
      void fetchActiveProject(id)
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to resume loop"
      pushToast({ title: "Resume failed", description: msg, tone: "error" })
    }
  }, [id, pushToast, queueOverviewRefresh, fetchActiveProject])

  const handleInject = useCallback(async (message: string) => {
    if (!id) return
    try {
      await apiFetch(`/projects/${id}/inject`, { method: "POST", body: JSON.stringify({ message }) })
      pushToast({ title: "Instruction injected", description: "Will be picked up next iteration", tone: "success" })
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to inject message"
      pushToast({ title: "Inject failed", description: msg, tone: "error" })
    }
  }, [id, pushToast])
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
              cliLabel={cliLabel}
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
              tokenPricePer1k={stats?.cost_per_1k_tokens}
            />
          </div>
        )

      case "specs":
        return (
          <div className="space-y-4">
            <ControlFilesPane projectId={id} />
            <SpecFileBrowser projectId={id} />
          </div>
        )

      case "code":
        return (
          <div className="overflow-hidden">
            <CodeFilesPane projectId={id} initialCommitHash={selectedCommitHash} />
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

      case "system":
        return <SystemPanel projectId={id} />

      default:
        return null
    }
  }

  return (
    <div className="flex min-h-0 min-w-0 max-w-full flex-col gap-4">
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
        <div className="flex">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleTabChange(tab.key)}
              className={`relative shrink-0 px-3 py-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:px-4 sm:py-2.5 sm:text-sm ${
                activeTab === tab.key
                  ? "text-foreground after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary"
                  : "text-muted-foreground hover:text-foreground/80"
              }`}
            >
              {tab.label}
              {/* Unread log dot */}
              {tab.key === "log" && hasUnreadLog && activeTab !== "log" && (
                <span className="absolute right-0.5 top-1 size-2 rounded-full bg-primary" />
              )}
            </button>
          ))}
        </div>
      </nav>

      {/* Active tab content */}
      <section className="min-h-0 overflow-hidden p-0 pb-4 sm:p-0 sm:pb-4">
        {renderTabContent()}
      </section>

      {/* Control bar — always visible at bottom */}
      <ProjectControlBar
        status={status}
        iterationLabel={iterationLabel}
        runtimeLabel={runtimeLabel}
        tokensUsed={tokensUsed}
        onStart={handleStart}
        onStop={handleStop}
        onPause={handlePause}
        onResume={handleResume}
        onInject={handleInject}
      />
    </div>
  )
}
