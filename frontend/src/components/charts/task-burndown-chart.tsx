import { useMemo } from "react"

import {
  Area,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { IterationSummary } from "@/types/project"

type TaskBurndownChartProps = {
  iterations: IterationSummary[]
  tasksTotal: number
}

type BurndownPoint = {
  timeMs: number
  iteration: number
  actualRemaining: number
  idealRemaining: number
  behindBase: number
  behindGap: number
  aheadBase: number
  aheadGap: number
}

type BurndownTooltipProps = {
  active?: boolean
  payload?: Array<{ payload: BurndownPoint }>
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

function buildBurndownData(iterations: IterationSummary[], tasksTotal: number): BurndownPoint[] {
  if (tasksTotal <= 0) {
    return []
  }

  const ordered = [...iterations].sort((left, right) => left.number - right.number)
  if (ordered.length === 0) {
    return []
  }

  const completedTaskIds = new Set<string>()
  const points: BurndownPoint[] = []
  let lastTimeMs: number | null = null
  let cumulativeTasks = 0

  for (const [index, iteration] of ordered.entries()) {
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

    const actualRemaining = Math.max(tasksTotal - cumulativeTasks, 0)
    const idealRemaining =
      ordered.length === 1 ? tasksTotal : Math.max(tasksTotal - (tasksTotal * index) / (ordered.length - 1), 0)
    const delta = actualRemaining - idealRemaining

    points.push({
      timeMs,
      iteration: iteration.number,
      actualRemaining,
      idealRemaining,
      behindBase: idealRemaining,
      behindGap: delta > 0 ? delta : 0,
      aheadBase: actualRemaining,
      aheadGap: delta < 0 ? Math.abs(delta) : 0,
    })
  }

  return points
}

function BurndownTooltip({ active, payload }: BurndownTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const point = payload[0]?.payload
  if (!point) {
    return null
  }

  const delta = point.actualRemaining - point.idealRemaining
  const varianceLabel =
    Math.abs(delta) < 0.01
      ? "On ideal track"
      : delta > 0
        ? `${delta.toFixed(1)} tasks behind`
        : `${Math.abs(delta).toFixed(1)} tasks ahead`

  return (
    <div className="rounded-md border bg-background px-3 py-2 text-xs shadow-lg">
      <p className="font-semibold">Iteration {point.iteration}</p>
      <p className="text-muted-foreground">{formatTimestamp(point.timeMs)}</p>
      <p className="mt-1">Actual remaining: {point.actualRemaining.toFixed(1)}</p>
      <p>Ideal remaining: {point.idealRemaining.toFixed(1)}</p>
      <p>{varianceLabel}</p>
    </div>
  )
}

export function TaskBurndownChart({ iterations, tasksTotal }: TaskBurndownChartProps) {
  const data = useMemo(() => buildBurndownData(iterations, tasksTotal), [iterations, tasksTotal])

  return (
    <section className="max-w-full overflow-hidden rounded-xl border bg-card p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Task Burndown</h3>
        <p className="text-sm text-muted-foreground">Ideal vs actual tasks remaining across iterations.</p>
      </header>

      {data.length === 0 ? (
        <div className="flex h-[300px] items-center justify-center rounded-lg border bg-background/40 text-sm text-muted-foreground">
          Burndown requires iteration and task data.
        </div>
      ) : (
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="timeMs"
                type="number"
                scale="time"
                domain={["dataMin", "dataMax"]}
                tick={{ fontSize: 12 }}
                minTickGap={32}
                tickFormatter={formatTimestamp}
              />
              <YAxis tick={{ fontSize: 12 }} domain={[0, tasksTotal]} />
              <Tooltip content={<BurndownTooltip />} />
              <Legend />
              <Area
                type="linear"
                dataKey="behindBase"
                stackId="behind"
                fill="transparent"
                stroke="none"
                isAnimationActive={false}
                legendType="none"
              />
              <Area
                type="linear"
                dataKey="behindGap"
                stackId="behind"
                name="Behind Schedule"
                fill="#EF4444"
                fillOpacity={0.16}
                stroke="none"
              />
              <Area
                type="linear"
                dataKey="aheadBase"
                stackId="ahead"
                fill="transparent"
                stroke="none"
                isAnimationActive={false}
                legendType="none"
              />
              <Area
                type="linear"
                dataKey="aheadGap"
                stackId="ahead"
                name="Ahead of Schedule"
                fill="#22C55E"
                fillOpacity={0.16}
                stroke="none"
              />
              <Line
                type="linear"
                dataKey="idealRemaining"
                name="Ideal Remaining"
                stroke="#64748B"
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="actualRemaining"
                name="Actual Remaining"
                stroke="#2563EB"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
