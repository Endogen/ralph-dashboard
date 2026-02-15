import { Fragment, useCallback, useEffect, useMemo, useState } from "react"

import { apiFetch } from "@/api/client"
import { GitDiffViewer } from "@/components/project/git-diff-viewer"
import { ITERATION_HEALTH_BADGE_CLASS, evaluateIterationHealth } from "@/lib/iteration-health"
import { displayTokens } from "@/lib/utils"
import type { GitCommitDiff, IterationDetail, IterationSummary } from "@/types/project"

type IterationSortKey = "number" | "status" | "health" | "duration" | "tokens" | "cost" | "tasks" | "commit" | "test"
type SortDirection = "asc" | "desc"
type StatusFilter = "all" | "success" | "error"
type HealthFilter = "all" | "productive" | "partial" | "failed"

type IterationsTableProps = {
  iterations: IterationSummary[]
  projectId?: string
  isLoading?: boolean
  tokenPricePer1k?: number
}

type StatusMeta = {
  label: string
  rank: number
  className: string
}

type TestMeta = {
  label: string
  rank: number
  className: string
}

const DEFAULT_TOKEN_PRICE_PER_1K = 0.006

const STATUS_CLASSES: Record<"success" | "warning" | "error" | "unknown", string> = {
  success: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  warning: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  error: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
  unknown: "bg-slate-500/15 text-slate-700 dark:text-slate-300",
}

const TEST_CLASSES: Record<"passed" | "failed" | "na", string> = {
  passed: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  failed: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
  na: "bg-slate-500/15 text-slate-700 dark:text-slate-300",
}

const COLUMNS: Array<{ key: IterationSortKey; label: string; hiddenOnMobile?: boolean }> = [
  { key: "number", label: "#" },
  { key: "status", label: "Status" },
  { key: "health", label: "Health" },
  { key: "duration", label: "Duration", hiddenOnMobile: true },
  { key: "tokens", label: "Tokens", hiddenOnMobile: true },
  { key: "cost", label: "Cost" },
  { key: "tasks", label: "Tasks" },
  { key: "commit", label: "Commit" },
  { key: "test", label: "Test" },
]

function getStatusMeta(iteration: IterationSummary): StatusMeta {
  if (iteration.has_errors || iteration.status === "error") {
    return { label: "Error", rank: 0, className: STATUS_CLASSES.error }
  }
  if (iteration.status === "success") {
    return { label: "Success", rank: 2, className: STATUS_CLASSES.success }
  }
  if (iteration.status) {
    return { label: "Warning", rank: 1, className: STATUS_CLASSES.warning }
  }
  return { label: "Unknown", rank: 1, className: STATUS_CLASSES.unknown }
}

function getTestMeta(value: boolean | null): TestMeta {
  if (value === true) {
    return { label: "Pass", rank: 2, className: TEST_CLASSES.passed }
  }
  if (value === false) {
    return { label: "Fail", rank: 0, className: TEST_CLASSES.failed }
  }
  return { label: "N/A", rank: 1, className: TEST_CLASSES.na }
}

function compareNullableNumbers(left: number | null, right: number | null): number {
  if (left === null && right === null) {
    return 0
  }
  if (left === null) {
    return 1
  }
  if (right === null) {
    return -1
  }
  return left - right
}

function compareNullableStrings(left: string | null, right: string | null): number {
  if (!left && !right) {
    return 0
  }
  if (!left) {
    return 1
  }
  if (!right) {
    return -1
  }
  return left.localeCompare(right)
}

function formatDuration(durationSeconds: number | null): string {
  if (durationSeconds === null || !Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    return "n/a"
  }
  const rounded = Math.round(durationSeconds)
  const hours = Math.floor(rounded / 3600)
  const minutes = Math.floor((rounded % 3600) / 60)
  const seconds = rounded % 60
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }
  return `${seconds}s`
}

function formatTokens(tokens: number | null): string {
  if (tokens === null || !Number.isFinite(tokens)) {
    return "n/a"
  }
  // Convert from k-tokens to actual tokens for display
  const actual = displayTokens(tokens)
  return new Intl.NumberFormat("en-US").format(actual)
}

function formatUsd(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "n/a"
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function iterationCost(tokensUsed: number | null, tokenPricePer1k: number): number | null {
  if (tokensUsed === null || !Number.isFinite(tokensUsed)) {
    return null
  }
  // tokens are already in k-tokens (e.g. 49.426 = 49,426 tokens)
  return tokensUsed * tokenPricePer1k
}

function getSortIndicator(column: IterationSortKey, activeSort: IterationSortKey, direction: SortDirection): string {
  if (column !== activeSort) {
    return "↕"
  }
  return direction === "asc" ? "↑" : "↓"
}

export function IterationsTable({
  iterations,
  projectId,
  isLoading = false,
  tokenPricePer1k = DEFAULT_TOKEN_PRICE_PER_1K,
}: IterationsTableProps) {
  const [sortKey, setSortKey] = useState<IterationSortKey>("number")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")
  const [healthFilter, setHealthFilter] = useState<HealthFilter>("all")
  const [searchFilter, setSearchFilter] = useState("")
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({})
  const [iterationDetails, setIterationDetails] = useState<Record<number, IterationDetail>>({})
  const [detailLoading, setDetailLoading] = useState<Record<number, boolean>>({})
  const [detailErrors, setDetailErrors] = useState<Record<number, string>>({})
  const [diffByCommit, setDiffByCommit] = useState<Record<string, string>>({})
  const [diffLoading, setDiffLoading] = useState<Record<string, boolean>>({})
  const [diffErrors, setDiffErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    setExpandedRows({})
    setIterationDetails({})
    setDetailLoading({})
    setDetailErrors({})
    setDiffByCommit({})
    setDiffLoading({})
    setDiffErrors({})
    setStatusFilter("all")
    setHealthFilter("all")
    setSearchFilter("")
  }, [projectId])

  const loadIterationDetail = useCallback(
    async (iterationNumber: number) => {
      if (!projectId || iterationDetails[iterationNumber] || detailLoading[iterationNumber]) {
        return
      }

      setDetailLoading((current) => ({ ...current, [iterationNumber]: true }))
      setDetailErrors((current) => ({ ...current, [iterationNumber]: "" }))

      try {
        const detail = await apiFetch<IterationDetail>(`/projects/${projectId}/iterations/${iterationNumber}`)
        setIterationDetails((current) => ({ ...current, [iterationNumber]: detail }))
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load iteration detail"
        setDetailErrors((current) => ({ ...current, [iterationNumber]: message }))
      } finally {
        setDetailLoading((current) => ({ ...current, [iterationNumber]: false }))
      }
    },
    [detailLoading, iterationDetails, projectId],
  )

  const loadCommitDiff = useCallback(
    async (commitHash: string) => {
      const normalizedCommitHash = commitHash.trim()
      if (
        !projectId ||
        !normalizedCommitHash ||
        diffByCommit[normalizedCommitHash] !== undefined ||
        diffLoading[normalizedCommitHash]
      ) {
        return
      }

      setDiffLoading((current) => ({ ...current, [normalizedCommitHash]: true }))
      setDiffErrors((current) => ({ ...current, [normalizedCommitHash]: "" }))

      try {
        const payload = await apiFetch<GitCommitDiff>(
          `/projects/${projectId}/git/diff/${encodeURIComponent(normalizedCommitHash)}`,
        )
        setDiffByCommit((current) => ({ ...current, [normalizedCommitHash]: payload.diff }))
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load commit diff"
        setDiffErrors((current) => ({ ...current, [normalizedCommitHash]: message }))
      } finally {
        setDiffLoading((current) => ({ ...current, [normalizedCommitHash]: false }))
      }
    },
    [diffByCommit, diffLoading, projectId],
  )

  const normalizedSearch = searchFilter.trim().toLowerCase()

  const filteredIterations = useMemo(() => {
    return iterations.filter((iteration) => {
      if (statusFilter === "success" && (iteration.has_errors || iteration.status !== "success")) {
        return false
      }
      if (statusFilter === "error" && !iteration.has_errors && iteration.status !== "error") {
        return false
      }

      const health = evaluateIterationHealth(iteration)
      if (healthFilter !== "all" && health.level !== healthFilter) {
        return false
      }

      if (!normalizedSearch) {
        return true
      }

      const detailLog = iterationDetails[iteration.number]?.log_output ?? ""
      const searchable = [
        iteration.number.toString(),
        iteration.status ?? "",
        iteration.commit ?? "",
        iteration.tasks_completed.join(" "),
        health.label,
        detailLog,
      ]
        .join(" ")
        .toLowerCase()

      return searchable.includes(normalizedSearch)
    })
  }, [healthFilter, iterationDetails, iterations, normalizedSearch, statusFilter])

  useEffect(() => {
    if (!projectId || !normalizedSearch) {
      return
    }

    const missingIterationNumbers = iterations
      .map((iteration) => iteration.number)
      .filter((iterationNumber) => !iterationDetails[iterationNumber] && !detailLoading[iterationNumber])

    if (missingIterationNumbers.length === 0) {
      return
    }

    let cancelled = false
    const hydrateLogsForSearch = async () => {
      const batchSize = 6
      for (let index = 0; index < missingIterationNumbers.length; index += batchSize) {
        if (cancelled) {
          return
        }
        const batch = missingIterationNumbers.slice(index, index + batchSize)
        await Promise.all(batch.map((iterationNumber) => loadIterationDetail(iterationNumber)))
      }
    }
    void hydrateLogsForSearch()

    return () => {
      cancelled = true
    }
  }, [detailLoading, iterationDetails, iterations, loadIterationDetail, normalizedSearch, projectId])

  const sortedIterations = useMemo(() => {
    const next = [...filteredIterations]
    next.sort((left, right) => {
      let comparison = 0

      if (sortKey === "number") {
        comparison = left.number - right.number
      } else if (sortKey === "status") {
        comparison = getStatusMeta(left).rank - getStatusMeta(right).rank
      } else if (sortKey === "health") {
        comparison = evaluateIterationHealth(left).score - evaluateIterationHealth(right).score
      } else if (sortKey === "duration") {
        comparison = compareNullableNumbers(left.duration_seconds, right.duration_seconds)
      } else if (sortKey === "tokens") {
        comparison = compareNullableNumbers(left.tokens_used, right.tokens_used)
      } else if (sortKey === "cost") {
        comparison = compareNullableNumbers(
          iterationCost(left.tokens_used, tokenPricePer1k),
          iterationCost(right.tokens_used, tokenPricePer1k),
        )
      } else if (sortKey === "tasks") {
        comparison = left.tasks_completed.length - right.tasks_completed.length
        if (comparison === 0) {
          comparison = left.tasks_completed.join(",").localeCompare(right.tasks_completed.join(","))
        }
      } else if (sortKey === "commit") {
        comparison = compareNullableStrings(left.commit, right.commit)
      } else if (sortKey === "test") {
        comparison = getTestMeta(left.test_passed).rank - getTestMeta(right.test_passed).rank
      }

      if (comparison === 0) {
        comparison = left.number - right.number
      }
      return sortDirection === "asc" ? comparison : -comparison
    })
    return next
  }, [filteredIterations, sortDirection, sortKey, tokenPricePer1k])

  const handleSort = (nextSort: IterationSortKey) => {
    if (sortKey === nextSort) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"))
      return
    }
    setSortKey(nextSort)
    setSortDirection(nextSort === "number" ? "desc" : "asc")
  }

  const toggleRow = (iteration: IterationSummary) => {
    const iterationNumber = iteration.number
    const currentlyExpanded = Boolean(expandedRows[iterationNumber])
    setExpandedRows((current) => ({ ...current, [iterationNumber]: !current[iterationNumber] }))

    if (!currentlyExpanded) {
      if (!projectId) {
        setDetailErrors((current) => ({
          ...current,
          [iterationNumber]: "Cannot load log output because no project id is available.",
        }))
        return
      }
      void loadIterationDetail(iterationNumber)
      if (iteration.commit) {
        void loadCommitDiff(iteration.commit)
      }
    }
  }

  return (
    <section className="max-w-full overflow-hidden rounded-xl p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Iterations</h3>
        <p className="break-words text-sm text-muted-foreground">
          Sortable and filterable iteration history with health scoring, terminal logs, and syntax-highlighted git diffs.
        </p>
      </header>

      <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-[150px_170px_minmax(0,1fr)]">
        <label className="text-xs text-muted-foreground">
          <span className="mb-1 block">Status</span>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm text-foreground"
          >
            <option value="all">All</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
          </select>
        </label>

        <label className="text-xs text-muted-foreground">
          <span className="mb-1 block">Health</span>
          <select
            value={healthFilter}
            onChange={(event) => setHealthFilter(event.target.value as HealthFilter)}
            className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm text-foreground"
          >
            <option value="all">All</option>
            <option value="productive">Productive</option>
            <option value="partial">Partial</option>
            <option value="failed">Failed</option>
          </select>
        </label>

        <label className="text-xs text-muted-foreground">
          <span className="mb-1 block">Search</span>
          <input
            value={searchFilter}
            onChange={(event) => setSearchFilter(event.target.value)}
            placeholder="Search task IDs, commits, status, or loaded log output..."
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground"
          />
        </label>
      </div>

      {isLoading && iterations.length === 0 ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-muted-foreground">
          Loading iterations...
        </div>
      ) : iterations.length === 0 ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-muted-foreground">
          No iterations recorded yet.
        </div>
      ) : sortedIterations.length === 0 ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-muted-foreground">
          No iterations match the current filters.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-background/70">
              <tr className="border-b">
                {COLUMNS.map((column) => (
                  <th key={column.key} className={`px-3 py-2 text-left font-medium text-muted-foreground ${column.hiddenOnMobile ? "hidden sm:table-cell" : ""}`}>
                    <button
                      type="button"
                      onClick={() => handleSort(column.key)}
                      className="inline-flex items-center gap-1 hover:text-foreground"
                    >
                      <span>{column.label}</span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {getSortIndicator(column.key, sortKey, sortDirection)}
                      </span>
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedIterations.map((iteration) => {
                const statusMeta = getStatusMeta(iteration)
                const healthMeta = evaluateIterationHealth(iteration)
                const testMeta = getTestMeta(iteration.test_passed)
                const cost = iterationCost(iteration.tokens_used, tokenPricePer1k)
                const isExpanded = Boolean(expandedRows[iteration.number])
                const detail = iterationDetails[iteration.number]
                const detailError = detailErrors[iteration.number]
                const isDetailLoading = detailLoading[iteration.number]
                const detailText = detail?.log_output?.trim() || "No log output available for this iteration."
                return (
                  <Fragment key={iteration.number}>
                    <tr
                      className="cursor-pointer border-b bg-background/20 hover:bg-background/50"
                      onClick={() => toggleRow(iteration)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleRow(iteration); } }}
                      aria-expanded={isExpanded}
                      aria-label={`Iteration ${iteration.number} — ${isExpanded ? "collapse" : "expand"} details`}
                    >
                      <td className="px-3 py-2 font-mono text-xs">
                        {iteration.number}
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${statusMeta.className}`}>
                          {statusMeta.label}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${
                            ITERATION_HEALTH_BADGE_CLASS[healthMeta.level]
                          }`}
                        >
                          {healthMeta.label}
                          <span className="font-mono text-[10px] opacity-80">({healthMeta.score})</span>
                        </span>
                      </td>
                      <td className="hidden px-3 py-2 sm:table-cell">{formatDuration(iteration.duration_seconds)}</td>
                      <td className="hidden px-3 py-2 font-mono sm:table-cell">{formatTokens(iteration.tokens_used)}</td>
                      <td className="px-3 py-2 font-mono">{formatUsd(cost)}</td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {iteration.tasks_completed.length > 0 ? iteration.tasks_completed.join(", ") : "None"}
                      </td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {iteration.commit && projectId ? (
                          <a
                            href={`/project/${projectId}/?tab=code&commit=${encodeURIComponent(iteration.commit)}`}
                            className="underline decoration-dotted"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {iteration.commit}
                          </a>
                        ) : (
                          iteration.commit ?? "n/a"
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${testMeta.className}`}>
                          {testMeta.label}
                        </span>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="border-b bg-background/40 last:border-b-0">
                        <td colSpan={COLUMNS.length} className="max-w-0 px-3 py-3">
                          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-100">
                            <div className="mb-2 flex items-center justify-between gap-2 text-[11px] text-zinc-300">
                              <span>Iteration {iteration.number} log output</span>
                              <span>{formatDuration(iteration.duration_seconds)}</span>
                            </div>
                            {isDetailLoading ? (
                              <p className="text-zinc-400">Loading log output...</p>
                            ) : detailError ? (
                              <p className="text-rose-300">{detailError}</p>
                            ) : (
                              <pre className="max-h-[320px] overflow-auto whitespace-pre-wrap break-words pr-2 text-[11px] leading-5">
                                {detailText}
                              </pre>
                            )}
                          </div>
                          {iteration.commit ? (
                            <div className="mt-3">
                              <GitDiffViewer
                                commitHash={iteration.commit}
                                diff={diffByCommit[iteration.commit] ?? null}
                                isLoading={Boolean(diffLoading[iteration.commit])}
                                error={diffErrors[iteration.commit] ?? null}
                              />
                            </div>
                          ) : (
                            <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-400">
                              No commit recorded for this iteration.
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {normalizedSearch && (
        <p className="mt-2 text-xs text-muted-foreground">
          Search checks loaded log output for {Object.keys(iterationDetails).length}/{iterations.length} iterations.
        </p>
      )}
    </section>
  )
}
