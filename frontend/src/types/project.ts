export type ProjectStatus = "running" | "paused" | "stopped" | "complete" | "error"

export type ProjectSummary = {
  id: string
  name: string
  path: string
  status: ProjectStatus
}

export type ProjectDetail = ProjectSummary & {
  ralph_dir: string
  plan_file: string | null
  log_file: string | null
}
