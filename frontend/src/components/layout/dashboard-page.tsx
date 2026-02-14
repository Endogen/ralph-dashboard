import { useMemo } from "react"
import { useNavigate } from "react-router-dom"

import { ProjectGrid, type ProjectGridItem } from "@/components/dashboard/project-grid"
import { useProjectsStore } from "@/stores/projects-store"

export function DashboardPage() {
  const navigate = useNavigate()
  const projects = useProjectsStore((state) => state.projects)
  const isLoading = useProjectsStore((state) => state.isLoading)
  const error = useProjectsStore((state) => state.error)

  const gridItems = useMemo<ProjectGridItem[]>(
    () =>
      projects.map((project, index) => {
        const currentIteration = project.status === "running" ? 15 + index : 0
        const maxIterations = project.status === "running" ? 50 : 50
        const healthStrip: ProjectGridItem["healthStrip"] = ["productive", "productive", "partial", "failed", "productive"]

        return {
          id: project.id,
          name: project.name,
          status: project.status,
          currentIteration,
          maxIterations,
          totalTokens: 1245 + index * 227,
          estimatedCostUsd: 7.47 + index * 1.12,
          lastActivityLabel: project.status === "running" ? "Updated just now" : "No recent activity",
          healthStrip,
        }
      }),
    [projects],
  )

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Project Dashboard</h1>
        <p className="text-sm text-muted-foreground">Overview of registered Ralph loop projects.</p>
      </header>
      <ProjectGrid
        projects={gridItems}
        isLoading={isLoading}
        error={error}
        onOpenProject={(projectId) => navigate(`/project/${projectId}`)}
      />
    </div>
  )
}
