import { useMemo } from "react"

import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { IterationSummary } from "@/types/project"

type ProgressTimelineChartProps = {
  iterations: IterationSummary[]
  tasksTotal: number
}

type TimelinePoint = {
  timeMs: number
  iteration: number | null
  tasksCumulative: number | null
  tokens: number | null
  projectionTasks: number | null
  errorTasks: number | null
  status: string
  isProjection: boolean
}

type TimelineTooltipProps = {
  active?: boolean
  payload?: Array<{ payload: TimelinePoint }>
}

function parseTimestamp(value: string | null): number | null {
  if (!value) {
    return null
  }
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : null
}

function formatTimestamp(value: number): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}

function formatStatus(status: string): string {
  if (!status) {
    return "Unknown"
  }
  return status.slice(0, 1).toUpperCase() + status.slice(1)
}

function buildTimelineData(iterations: IterationSummary[], tasksTotal: number): TimelinePoint[] {
  const ordered = [...iterations].sort((a, b) => a.number - b.number)
  if (ordered.length === 0) {
    return []
  }

  const completedTaskIds = new Set<string>()
  const points: TimelinePoint[] = []
  let lastTimeMs: number | null = null
  let cumulativeTasks = 0

  for (const iteration of ordered) {
    let timeMs: number =
      parseTimestamp(iteration.end_timestamp) ??
      parseTimestamp(iteration.start_timestamp) ??
      (lastTimeMs === null ? Date.now() : lastTimeMs + 60_000)
    if (lastTimeMs !== null && timeMs <= lastTimeMs) {
      timeMs = lastTimeMs + 60_000
    }
    lastTimeMs = timeMs

    let newTaskCount = 0
    for (const taskId of iteration.tasks_completed) {
      const normalized = taskId.trim()
      if (!normalized || completedTaskIds.has(normalized)) {
        continue
      }
      completedTaskIds.add(normalized)
      newTaskCount += 1
    }
    cumulativeTasks += newTaskCount

    const status = iteration.status ?? (iteration.has_errors ? "error" : "success")
    const hasError = iteration.has_errors || status.toLowerCase() === "error"

    points.push({
      timeMs,
      iteration: iteration.number,
      tasksCumulative: cumulativeTasks,
      tokens: iteration.tokens_used,
      projectionTasks: null,
      errorTasks: hasError ? cumulativeTasks : null,
      status,
      isProjection: false,
    })
  }

  if (points.length < 3) {
    return points
  }

  const firstPoint = points[0]
  const lastPoint = points[points.length - 1]
  const completedTasks = lastPoint.tasksCumulative ?? 0
  const remainingTasks = tasksTotal - completedTasks
  const elapsedMs = lastPoint.timeMs - firstPoint.timeMs
  if (remainingTasks <= 0 || completedTasks <= 0 || elapsedMs <= 0 || tasksTotal <= 0) {
    return points
  }

  const velocityTasksPerMs = completedTasks / elapsedMs
  if (!Number.isFinite(velocityTasksPerMs) || velocityTasksPerMs <= 0) {
    return points
  }

  const projectedDurationMs = remainingTasks / velocityTasksPerMs
  const projectedTimeMs = Math.round(lastPoint.timeMs + projectedDurationMs)
  if (!Number.isFinite(projectedTimeMs) || projectedTimeMs <= lastPoint.timeMs) {
    return points
  }

  const projectionStart: TimelinePoint = {
    ...lastPoint,
    projectionTasks: completedTasks,
  }
  const projectionEnd: TimelinePoint = {
    timeMs: projectedTimeMs,
    iteration: null,
    tasksCumulative: null,
    tokens: null,
    projectionTasks: tasksTotal,
    errorTasks: null,
    status: "projected",
    isProjection: true,
  }

  return [...points.slice(0, -1), projectionStart, projectionEnd]
}

function TimelineTooltip({ active, payload }: TimelineTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const point = payload[0]?.payload
  if (!point) {
    return null
  }

  if (point.isProjection) {
    return (
      <div className="rounded-md border bg-background px-3 py-2 text-xs shadow-lg">
        <p className="font-semibold">Projected Completion</p>
        <p className="text-muted-foreground">{formatTimestamp(point.timeMs)}</p>
        <p className="mt-1">Projected Tasks: {point.projectionTasks ?? 0}</p>
      </div>
    )
  }

  return (
    <div className="rounded-md border bg-background px-3 py-2 text-xs shadow-lg">
      <p className="font-semibold">Iteration {point.iteration ?? "?"}</p>
      <p className="text-muted-foreground">{formatTimestamp(point.timeMs)}</p>
      <p className="mt-1">Tasks (cumulative): {point.tasksCumulative ?? 0}</p>
      <p>Tokens: {point.tokens?.toLocaleString("en-US", { maximumFractionDigits: 2 }) ?? "n/a"}</p>
      <p>Status: {formatStatus(point.status)}</p>
    </div>
  )
}

export function ProgressTimelineChart({ iterations, tasksTotal }: ProgressTimelineChartProps) {
  const data = useMemo(() => buildTimelineData(iterations, tasksTotal), [iterations, tasksTotal])
  const tasksUpperBound = useMemo(() => {
    const pointsMax = data.reduce((max, point) => {
      const current = Math.max(point.tasksCumulative ?? 0, point.projectionTasks ?? 0)
      return Math.max(max, current)
    }, 0)
    return Math.max(tasksTotal, pointsMax, 1)
  }, [data, tasksTotal])

  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Progress Timeline</h3>
        <p className="text-sm text-muted-foreground">
          Tasks completed over time with token consumption and projection.
        </p>
      </header>

      {data.length === 0 ? (
        <div className="flex h-[320px] items-center justify-center rounded-lg border bg-background/40 text-sm text-muted-foreground">
          No iteration data yet.
        </div>
      ) : (
        <div className="h-[320px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 20, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="timeMs"
                type="number"
                scale="time"
                domain={["dataMin", "dataMax"]}
                tick={{ fontSize: 12 }}
                minTickGap={36}
                tickFormatter={formatTimestamp}
              />
              <YAxis yAxisId="tasks" tick={{ fontSize: 12 }} domain={[0, tasksUpperBound]} />
              <YAxis yAxisId="tokens" orientation="right" tick={{ fontSize: 12 }} />
              <Tooltip content={<TimelineTooltip />} />
              <Legend />
              <Area
                yAxisId="tasks"
                type="monotone"
                dataKey="tasksCumulative"
                name="Tasks Completed"
                stroke="#2563EB"
                fill="#2563EB"
                fillOpacity={0.2}
                dot={false}
              />
              <Bar
                yAxisId="tokens"
                dataKey="tokens"
                name="Tokens / Iteration"
                fill="#8B5CF6"
                radius={[4, 4, 0, 0]}
                barSize={14}
              />
              <Line
                yAxisId="tasks"
                type="linear"
                dataKey="projectionTasks"
                name="Projection"
                stroke="#64748B"
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={false}
                connectNulls
              />
              <Scatter yAxisId="tasks" dataKey="errorTasks" name="Errors" fill="#EF4444" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
