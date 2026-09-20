import { ProgressTimelineChart } from "@/components/charts/progress-timeline-chart"
import { TaskBurndownChart } from "@/components/charts/task-burndown-chart"
import { TokenUsagePhaseChart } from "@/components/charts/token-usage-phase-chart"
import type { IterationSummary, PhaseTokenUsage } from "@/types/project"

type ProjectChartsPanelProps = {
  iterations: IterationSummary[]
  tasksTotal: number
  tokensByPhase: PhaseTokenUsage[]
  tokensUsed: number
}

/**
 * Every recharts-backed chart on the project page, in one module.
 *
 * Recharts is the largest dependency in this route's bundle and nothing above
 * the Overview tab needs it, so keeping the imports together lets Vite emit a
 * single chunk that loads only when the charts are actually rendered.
 */
export default function ProjectChartsPanel({
  iterations,
  tasksTotal,
  tokensByPhase,
  tokensUsed,
}: ProjectChartsPanelProps) {
  return (
    <>
      <div className="overflow-hidden">
        <ProgressTimelineChart iterations={iterations} tasksTotal={tasksTotal} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="overflow-hidden">
          <TaskBurndownChart iterations={iterations} tasksTotal={tasksTotal} />
        </div>
        <div className="overflow-hidden">
          <TokenUsagePhaseChart data={tokensByPhase} totalTokens={tokensUsed} />
        </div>
      </div>
    </>
  )
}
