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

export type SpecFileInfo = {
  name: string
  size: number
  modified: string
}

export type SpecFileContent = {
  name: string
  content: string
}

export type ProjectFileContent = {
  name: string
  content: string
}

export type GitCommitSummary = {
  hash: string
  author: string
  date: string
  message: string
  files_changed: number
  insertions: number
  deletions: number
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
  cost_per_1k_tokens: number
}

export type ProcessMetrics = {
  pid: number | null
  rss_mb: number
  children_rss_mb: number
  total_rss_mb: number
  cpu_percent: number
  child_count: number
}

export type SystemMetrics = {
  ram_total_mb: number
  ram_used_mb: number
  ram_available_mb: number
  ram_percent: number
  cpu_load_1m: number
  cpu_load_5m: number
  cpu_load_15m: number
  cpu_core_count: number
  disk_total_gb: number
  disk_used_gb: number
  disk_free_gb: number
  disk_percent: number
  uptime_seconds: number
}

export type ProjectSystemInfo = {
  process: ProcessMetrics
  system: SystemMetrics
}

export type LoopConfig = {
  cli: string
  flags: string
  max_iterations: number
  test_command: string
  model_pricing: Record<string, number>
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
