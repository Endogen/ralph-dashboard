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

export type IterationSummary = {
  number: number
  max_iterations: number | null
  start_timestamp: string | null
  end_timestamp: string | null
  duration_seconds: number | null
  tokens_used: number | null
  status: string | null
  has_errors: boolean
  errors: string[]
  tasks_completed: string[]
  commit: string | null
  test_passed: boolean | null
}

export type IterationListResponse = {
  iterations: IterationSummary[]
  total: number
}

export type IterationDetail = IterationSummary & {
  log_output: string
}

export type GitCommitDiff = {
  hash: string
  diff: string
}

export type VelocityStats = {
  tasks_per_hour: number
  tasks_remaining: number
  hours_remaining: number
}

export type HealthBreakdown = {
  productive: number
  partial: number
  failed: number
}

export type PhaseTokenUsage = {
  phase: string
  tokens: number
}

export type ProjectStats = {
  total_iterations: number
  total_tokens: number
  total_cost_usd: number
  total_duration_seconds: number
  avg_iteration_duration_seconds: number
  avg_tokens_per_iteration: number
  tasks_done: number
  tasks_total: number
  errors_count: number
  projected_completion: string | null
  projected_total_cost_usd: number
  velocity: VelocityStats
  health_breakdown: HealthBreakdown
  tokens_by_phase: PhaseTokenUsage[]
}

export type NotificationEntry = {
  timestamp: string
  prefix: string | null
  message: string
  status: string | null
  iteration: number | null
  details: string | null
  source: string | null
}

export type ParsedPlanTask = {
  id: string | null
  description: string
  done: boolean
  indent: number
}

export type ParsedPlanPhase = {
  name: string
  tasks: ParsedPlanTask[]
  done_count: number
  total_count: number
  status: "pending" | "in_progress" | "complete"
}

export type ParsedImplementationPlan = {
  status: string | null
  phases: ParsedPlanPhase[]
  tasks_done: number
  tasks_total: number
  raw: string
}
