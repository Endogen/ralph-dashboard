import { useParams } from "react-router-dom"

import { ProjectControlBar } from "@/components/layout/project-control-bar"
import { ProjectTopBar } from "@/components/layout/project-top-bar"

export function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const projectName = id ?? "Unknown Project"
  const status = "running" as const
  const iterationLabel = "Iteration 15/50"
  const runtimeLabel = "Running for 2h 14m"
  const tokensUsed = 1245
  const estimatedCostUsd = 7.47

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
        <h2 className="text-lg font-semibold">Project Workspace</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Tabs and detailed panels will be implemented in the next frontend phases.
        </p>
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
