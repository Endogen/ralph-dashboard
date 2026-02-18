import { useCallback, useEffect, useRef, useState } from "react"

import { apiFetch } from "@/api/client"
import type { ProjectSystemInfo } from "@/types/project"

type SystemPanelProps = {
  projectId?: string
}

const POLL_INTERVAL_MS = 5_000

function barColor(percent: number): string {
  if (percent >= 80) return "bg-rose-500"
  if (percent >= 60) return "bg-amber-500"
  return "bg-emerald-500"
}

function formatUptime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return "—"
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const parts: string[] = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  parts.push(`${minutes}m`)
  return parts.join(" ")
}

function formatMb(mb: number): string {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`
  return `${mb.toFixed(0)} MB`
}

function timeSince(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 5) return "just now"
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ago`
}

function UsageBar({ percent, label }: { percent: number; label: string }) {
  const clampedPercent = Math.min(Math.max(percent, 0), 100)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>{clampedPercent.toFixed(1)}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all ${barColor(clampedPercent)}`}
          style={{ width: `${clampedPercent}%` }}
        />
      </div>
    </div>
  )
}

function Badge({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${className}`}
    >
      {children}
    </span>
  )
}

export function SystemPanel({ projectId }: SystemPanelProps) {
  const [data, setData] = useState<ProjectSystemInfo | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [timeSinceLabel, setTimeSinceLabel] = useState("")
  const intervalRef = useRef<number | null>(null)

  const fetchData = useCallback(async () => {
    if (!projectId) return
    try {
      const result = await apiFetch<ProjectSystemInfo>(`/projects/${projectId}/system`)
      setData(result)
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load system metrics"
      setError(message)
    }
  }, [projectId])

  // Initial load
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setIsLoading(true)
      setError(null)
      setData(null)
      await fetchData()
      if (!cancelled) setIsLoading(false)
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [fetchData])

  // Polling — pauses when the browser tab is hidden to save bandwidth/battery
  useEffect(() => {
    if (!projectId) return

    const startPolling = () => {
      if (intervalRef.current !== null) return
      intervalRef.current = window.setInterval(() => {
        void fetchData()
      }, POLL_INTERVAL_MS)
    }

    const stopPolling = () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling()
      } else {
        void fetchData() // Immediate refresh when tab becomes visible
        startPolling()
      }
    }

    startPolling()
    document.addEventListener("visibilitychange", handleVisibilityChange)

    return () => {
      stopPolling()
      document.removeEventListener("visibilitychange", handleVisibilityChange)
    }
  }, [fetchData, projectId])

  // Update "Xs ago" label
  useEffect(() => {
    if (!lastUpdated) return
    setTimeSinceLabel(timeSince(lastUpdated))
    const timer = window.setInterval(() => {
      setTimeSinceLabel(timeSince(lastUpdated))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [lastUpdated])

  if (isLoading && !data) {
    return (
      <section className="rounded-xl p-4">
        <p className="py-8 text-center text-sm text-muted-foreground">Loading system metrics...</p>
      </section>
    )
  }

  if (error && !data) {
    return (
      <section className="rounded-xl p-4">
        <p className="py-8 text-center text-sm text-rose-600 dark:text-rose-400">{error}</p>
      </section>
    )
  }

  if (!data) return null

  const { process: proc, system: sys } = data
  const ramPercent = sys.ram_total_mb > 0 ? (sys.ram_used_mb / sys.ram_total_mb) * 100 : 0
  const processRamPercent =
    sys.ram_total_mb > 0 ? (proc.total_rss_mb / sys.ram_total_mb) * 100 : 0

  return (
    <section className="rounded-xl p-4">
      <header className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-semibold">System</h3>
        {timeSinceLabel && (
          <span className="text-xs text-muted-foreground">Updated {timeSinceLabel}</span>
        )}
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Loop Process */}
        <article className="rounded-lg border bg-background/30 p-4">
          <h4 className="mb-3 text-sm font-semibold">Loop Process</h4>

          <div className="mb-3 flex flex-wrap gap-2">
            <Badge className={proc.pid ? "border-emerald-500/40 text-emerald-600 dark:text-emerald-400" : "border-muted text-muted-foreground"}>
              PID {proc.pid ?? "—"}
            </Badge>
            <Badge className="border-muted text-muted-foreground">
              {proc.child_count} child{proc.child_count !== 1 ? "ren" : ""}
            </Badge>
          </div>

          <div className="space-y-3">
            <UsageBar
              percent={processRamPercent}
              label={`RAM: ${formatMb(proc.total_rss_mb)} (proc ${formatMb(proc.rss_mb)} + children ${formatMb(proc.children_rss_mb)})`}
            />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>CPU</span>
              <span className="font-medium text-foreground">{proc.cpu_percent.toFixed(1)}%</span>
            </div>
          </div>
        </article>

        {/* Server */}
        <article className="rounded-lg border bg-background/30 p-4">
          <h4 className="mb-3 text-sm font-semibold">Server</h4>

          <div className="space-y-3">
            <UsageBar
              percent={ramPercent}
              label={`RAM: ${formatMb(sys.ram_used_mb)} / ${formatMb(sys.ram_total_mb)}`}
            />

            <div>
              <span className="text-xs text-muted-foreground">CPU Load</span>
              <div className="mt-1 flex flex-wrap gap-1.5">
                <Badge className="border-muted text-muted-foreground">
                  1m: {sys.cpu_load_1m.toFixed(2)}
                </Badge>
                <Badge className="border-muted text-muted-foreground">
                  5m: {sys.cpu_load_5m.toFixed(2)}
                </Badge>
                <Badge className="border-muted text-muted-foreground">
                  15m: {sys.cpu_load_15m.toFixed(2)}
                </Badge>
                <Badge className="border-muted text-muted-foreground">
                  {sys.cpu_core_count} core{sys.cpu_core_count !== 1 ? "s" : ""}
                </Badge>
              </div>
            </div>

            <UsageBar
              percent={sys.disk_percent}
              label={`Disk: ${sys.disk_used_gb.toFixed(1)} GB / ${sys.disk_total_gb.toFixed(1)} GB`}
            />

            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Uptime</span>
              <span className="font-medium text-foreground">{formatUptime(sys.uptime_seconds)}</span>
            </div>
          </div>
        </article>
      </div>

      {error && (
        <p className="mt-3 text-center text-xs text-rose-600 dark:text-rose-400">{error}</p>
      )}
    </section>
  )
}
