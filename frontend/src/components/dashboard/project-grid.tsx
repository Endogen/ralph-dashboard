import { ProjectCard } from "@/components/dashboard/project-card"
import type { ProjectStatus } from "@/types/project"

type IterationHealth = "productive" | "partial" | "failed"

export type ProjectGridItem = {
  id: string
  name: string
  status: ProjectStatus
  currentIteration: number
  maxIterations: number
  totalTokens: number
  estimatedCostUsd: number
  lastActivityLabel: string
  healthStrip: IterationHealth[]
}

type ProjectGridProps = {
  projects: ProjectGridItem[]
  isLoading?: boolean
  error?: string | null
  onOpenProject?: (projectId: string) => void
}

export function ProjectGrid({ projects, isLoading, error, onOpenProject }: ProjectGridProps) {
  if (isLoading) {
    return (
      <section className="rounded-xl border border-dashed bg-card/40 p-10 text-center text-sm text-muted-foreground">
        Loading projects...
      </section>
    )
  }

  if (error) {
    return (
      <section className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-10 text-center text-sm text-rose-700 dark:text-rose-300">
        {error}
      </section>
    )
  }

  if (projects.length === 0) {
    return (
      <section className="rounded-xl border border-dashed bg-card/40 p-10 text-center">
        <h2 className="text-lg font-semibold">No projects yet</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Add a project from the sidebar to start monitoring Ralph loops.
        </p>
      </section>
    )
  }

  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {projects.map((project) => (
        <ProjectCard
          key={project.id}
          id={project.id}
          name={project.name}
          status={project.status}
          currentIteration={project.currentIteration}
          maxIterations={project.maxIterations}
          totalTokens={project.totalTokens}
          estimatedCostUsd={project.estimatedCostUsd}
          lastActivityLabel={project.lastActivityLabel}
          healthStrip={project.healthStrip}
          onOpen={onOpenProject}
        />
      ))}
    </section>
  )
}
