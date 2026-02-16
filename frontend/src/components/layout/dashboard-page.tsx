import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"

import { apiFetch } from "@/api/client"
import { ProjectGrid, type ProjectGridItem } from "@/components/dashboard/project-grid"
import { useProjectsStore } from "@/stores/projects-store"
import type { IterationListResponse, IterationSummary, ProjectStats } from "@/types/project"

type PerProjectData = {
  stats: ProjectStats | null
  iterations: IterationSummary[]
}

function relativeTimeLabel(isoTimestamp: string | null | undefined): string {
  if (!isoTimestamp) return "No recent activity"
  const then = new Date(isoTimestamp).getTime()
  if (Number.isNaN(then)) return "No recent activity"
  const diffMs = Date.now() - then
  if (diffMs < 0) return "Updated just now"
  const seconds = Math.floor(diffMs / 1000)
  if (seconds < 60) return "Updated just now"
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `Updated ${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Updated ${hours}h ago`
  const days = Math.floor(hours / 24)
  return `Updated ${days}d ago`
}

function buildHealthStrip(iterations: IterationSummary[]): ProjectGridItem["healthStrip"] {
  const sorted = [...iterations].sort((a, b) => a.number - b.number)
  const recent = sorted.slice(-10)
  return recent.map((iter) => {
    if (iter.has_errors) return "failed"
    if (iter.tasks_completed.length > 0) return "productive"
    return "partial"
  })
}

export function DashboardPage() {
  const navigate = useNavigate()
  const projects = useProjectsStore((state) => state.projects)
  const isLoading = useProjectsStore((state) => state.isLoading)
  const error = useProjectsStore((state) => state.error)

  const [dataMap, setDataMap] = useState<Record<string, PerProjectData>>({})
  const [statsLoading, setStatsLoading] = useState(false)

  const fetchProjectData = useCallback(async () => {
    if (projects.length === 0) return
    setStatsLoading(true)
    const entries = await Promise.all(
      projects.map(async (project) => {
        try {
          const [stats, iterResponse] = await Promise.all([
            apiFetch<ProjectStats>(`/projects/${project.id}/stats`),
            apiFetch<IterationListResponse>(`/projects/${project.id}/iterations`),
          ])
          return [project.id, { stats, iterations: iterResponse.iterations }] as const
        } catch {
          return [project.id, { stats: null, iterations: [] }] as const
        }
      }),
    )
    setDataMap(Object.fromEntries(entries))
    setStatsLoading(false)
  }, [projects])

  useEffect(() => {
    fetchProjectData()
  }, [fetchProjectData])

  const gridItems = useMemo<ProjectGridItem[]>(() => {
    const items = projects.map((project) => {
      const data = dataMap[project.id]
      const stats = data?.stats ?? null
      const iterations = data?.iterations ?? []

      const currentIteration = stats?.total_iterations ?? 0
      const maxFromIter = iterations.find((i) => i.max_iterations != null)?.max_iterations
      const maxIterations = maxFromIter ?? currentIteration

      const sorted = [...iterations].sort((a, b) => a.number - b.number)
      const latestIteration = sorted[sorted.length - 1]
      const lastActivityLabel = relativeTimeLabel(latestIteration?.end_timestamp)

      const healthStrip = iterations.length > 0 ? buildHealthStrip(iterations) : []

      const firstTimestamp = sorted[0]?.start_timestamp ?? null

      return {
        id: project.id,
        name: project.name,
        status: project.status,
        currentIteration,
        maxIterations,
        totalTokens: stats?.total_tokens ?? 0,
        estimatedCostUsd: stats?.total_cost_usd ?? 0,
        lastActivityLabel,
        healthStrip,
        _firstTimestamp: firstTimestamp,
      }
    })

    // Sort newest projects first (most recent first iteration timestamp),
    // projects with no iterations go to the top
    items.sort((a, b) => {
      if (!a._firstTimestamp && !b._firstTimestamp) return 0
      if (!a._firstTimestamp) return -1
      if (!b._firstTimestamp) return 1
      return new Date(b._firstTimestamp).getTime() - new Date(a._firstTimestamp).getTime()
    })

    return items
  }, [projects, dataMap])

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Project Dashboard</h1>
        <p className="text-sm text-muted-foreground">Overview of registered Ralph loop projects.</p>
      </header>
      <ProjectGrid
        projects={gridItems}
        isLoading={isLoading || statsLoading}
        error={error}
        onOpenProject={(projectId) => navigate(`/project/${projectId}`)}
      />
    </div>
  )
}
