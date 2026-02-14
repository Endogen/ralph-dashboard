import { useEffect } from "react"

import { useParams } from "react-router-dom"

import { ProjectControlBar } from "@/components/layout/project-control-bar"
import { ProjectTopBar } from "@/components/layout/project-top-bar"
import { StatusPanel } from "@/components/project/status-panel"
import { useActiveProjectStore } from "@/stores/active-project-store"

export function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const activeProject = useActiveProjectStore((state) => state.activeProject)
  const fetchActiveProject = useActiveProjectStore((state) => state.fetchActiveProject)
  const clearActiveProject = useActiveProjectStore((state) => state.clearActiveProject)
  const isLoading = useActiveProjectStore((state) => state.isLoading)

  useEffect(() => {
    void fetchActiveProject(id ?? null)
    return () => {
      clearActiveProject()
    }
  }, [clearActiveProject, fetchActiveProject, id])

  const projectName = activeProject?.name ?? id ?? "Unknown Project"
  const status = activeProject?.status ?? "stopped"
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
        <StatusPanel
          status={status}
          iterationLabel={iterationLabel}
          runningFor={runtimeLabel}
          cliLabel="codex"
          modeLabel="BUILDING"
        />

        <div className="mt-4 rounded-xl border bg-background/50 p-4">
          <h3 className="text-base font-semibold">Project Workspace</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Overview charts and activity widgets will be implemented in the next frontend phases.
          </p>
        </div>
        {isLoading && <p className="mt-3 text-sm text-muted-foreground">Loading project details...</p>}
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
