import { useMemo } from "react"

import { AlertTriangle, Bell, CheckCircle2, ListChecks } from "lucide-react"

import type { IterationSummary, NotificationEntry } from "@/types/project"

type ActivityKind = "iteration" | "task" | "error" | "notification"

type ActivityItem = {
  id: string
  timeMs: number
  kind: ActivityKind
  title: string
  description: string
}

type RecentActivityFeedProps = {
  iterations: IterationSummary[]
  notifications: NotificationEntry[]
  limit?: number
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

function formatTokens(value: number | null): string {
  if (value === null || value === undefined) {
    return "token usage unavailable"
  }
  return `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })} tokens`
}

function buildIterationEvents(iterations: IterationSummary[]): ActivityItem[] {
  const ordered = [...iterations].sort((left, right) => left.number - right.number)
  const fallbackBase = Date.now() - ordered.length * 60_000

  const events: ActivityItem[] = []
  for (const [index, iteration] of ordered.entries()) {
    const timeMs =
      parseTimestamp(iteration.end_timestamp) ??
      parseTimestamp(iteration.start_timestamp) ??
      (fallbackBase + index * 60_000)
    const status = iteration.status ?? (iteration.has_errors ? "error" : "success")

    events.push({
      id: `iter-${iteration.number}`,
      timeMs: timeMs + 2_000,
      kind: "iteration",
      title: `Iteration ${iteration.number} completed`,
      description: `${status.toUpperCase()} - ${formatTokens(iteration.tokens_used)}`,
    })

    if (iteration.tasks_completed.length > 0) {
      events.push({
        id: `task-${iteration.number}`,
        timeMs: timeMs + 1_000,
        kind: "task",
        title: "Tasks marked done",
        description: `Iteration ${iteration.number}: ${iteration.tasks_completed.join(", ")}`,
      })
    }

    if (iteration.has_errors || status === "error" || iteration.test_passed === false) {
      const firstError = iteration.errors[0] ?? "Check iteration logs for details."
      events.push({
        id: `error-${iteration.number}`,
        timeMs: timeMs + 500,
        kind: "error",
        title: `Error in iteration ${iteration.number}`,
        description: firstError,
      })
    }
  }

  return events
}

function buildNotificationEvents(notifications: NotificationEntry[]): ActivityItem[] {
  const fallbackBase = Date.now()
  return notifications.map((notification, index) => {
    const timeMs = parseTimestamp(notification.timestamp) ?? fallbackBase - index * 60_000
    const prefix = notification.prefix ? `${notification.prefix}: ` : ""
    const iterationSuffix = notification.iteration ? ` (iteration ${notification.iteration})` : ""
    return {
      id: `notification-${notification.timestamp}-${index}`,
      timeMs,
      kind: "notification",
      title: `Notification${iterationSuffix}`,
      description: `${prefix}${notification.message}`.trim(),
    }
  })
}

function iconForKind(kind: ActivityKind) {
  if (kind === "task") {
    return <ListChecks className="h-4 w-4 text-emerald-500" />
  }
  if (kind === "error") {
    return <AlertTriangle className="h-4 w-4 text-rose-500" />
  }
  if (kind === "notification") {
    return <Bell className="h-4 w-4 text-amber-500" />
  }
  return <CheckCircle2 className="h-4 w-4 text-blue-500" />
}

export function RecentActivityFeed({
  iterations,
  notifications,
  limit = 12,
}: RecentActivityFeedProps) {
  const items = useMemo(() => {
    const merged = [...buildIterationEvents(iterations), ...buildNotificationEvents(notifications)]
    return merged.sort((left, right) => right.timeMs - left.timeMs).slice(0, limit)
  }, [iterations, notifications, limit])

  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Recent Activity</h3>
        <p className="text-sm text-muted-foreground">
          Latest iteration outcomes, task completions, errors, and notifications.
        </p>
      </header>

      {items.length === 0 ? (
        <div className="flex h-[200px] items-center justify-center rounded-lg border bg-background/40 text-sm text-muted-foreground">
          No recent activity yet.
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <article key={item.id} className="rounded-lg border bg-background/50 p-3">
              <div className="flex items-start gap-2">
                <span className="mt-0.5">{iconForKind(item.kind)}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="text-xs text-muted-foreground">{formatTimestamp(item.timeMs)}</p>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
