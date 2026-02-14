export type ProjectStatus = "running" | "paused" | "stopped" | "complete" | "error"

export type ProjectSummary = {
  id: string
  name: string
  path: string
  status: ProjectStatus
  currentIteration: number
  maxIterations: number
}
