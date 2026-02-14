import { useParams } from "react-router-dom"

import { ProjectTopBar } from "@/components/layout/project-top-bar"

export function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const projectName = id ?? "Unknown Project"

  return (
    <div className="space-y-4">
      <ProjectTopBar
        projectName={projectName}
        status="running"
        iterationLabel="Iteration 15/50"
        runtimeLabel="Running for 2h 14m"
        tokensUsed={1245}
        estimatedCostUsd={7.47}
      />

      <section className="rounded-xl border bg-card p-6">
        <h2 className="text-lg font-semibold">Project Workspace</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Tabs and detailed panels will be implemented in the next frontend phases.
        </p>
      </section>
    </div>
  )
}
