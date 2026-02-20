import { useCallback, useEffect, useRef, useState } from "react"

import { apiFetch } from "@/api/client"
import { GitDiffViewer } from "@/components/project/git-diff-viewer"
import type { GitCommitDiff, GitCommitSummary } from "@/types/project"

type CodeFilesPaneProps = {
  projectId?: string
  initialCommitHash?: string | null
}

function formatCommitDate(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.valueOf())) {
    return value
  }
  return parsed.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export function CodeFilesPane({ projectId, initialCommitHash = null }: CodeFilesPaneProps) {
  const [gitLog, setGitLog] = useState<GitCommitSummary[]>([])
  const [isGitLogLoading, setIsGitLogLoading] = useState(false)
  const [gitLogError, setGitLogError] = useState<string | null>(null)
  const [expandedCommitHash, setExpandedCommitHash] = useState<string | null>(null)
  const [diffByCommit, setDiffByCommit] = useState<Record<string, string>>({})
  const [diffLoading, setDiffLoading] = useState<Record<string, boolean>>({})
  const [diffError, setDiffError] = useState<Record<string, string>>({})
  const [pendingScrollCommitHash, setPendingScrollCommitHash] = useState<string | null>(null)
  const appliedQueryCommitRef = useRef<string | null>(null)
  const commitItemRefs = useRef<Record<string, HTMLLIElement | null>>({})

  useEffect(() => {
    let cancelled = false

    const loadGitLog = async () => {
      if (!projectId) {
        setGitLog([])
        setIsGitLogLoading(false)
        setGitLogError(null)
        setExpandedCommitHash(null)
        setDiffByCommit({})
        setDiffLoading({})
        setDiffError({})
        return
      }

      setIsGitLogLoading(true)
      setGitLogError(null)
      try {
        const commits = await apiFetch<GitCommitSummary[]>(`/projects/${projectId}/git/log?limit=50&offset=0`)
        if (cancelled) {
          return
        }
        setGitLog(commits)
      } catch (loadError) {
        if (cancelled) {
          return
        }
        const message = loadError instanceof Error ? loadError.message : "Failed to load git log"
        setGitLog([])
        setGitLogError(message)
      } finally {
        if (!cancelled) {
          setIsGitLogLoading(false)
        }
      }
    }

    void loadGitLog()

    return () => {
      cancelled = true
    }
  }, [projectId])

  const loadCommitDiff = useCallback(
    async (commitHash: string) => {
      if (!projectId || diffByCommit[commitHash] !== undefined || diffLoading[commitHash]) {
        return
      }

      setDiffLoading((current) => ({ ...current, [commitHash]: true }))
      setDiffError((current) => ({ ...current, [commitHash]: "" }))
      try {
        const payload = await apiFetch<GitCommitDiff>(
          `/projects/${projectId}/git/diff/${encodeURIComponent(commitHash)}`,
        )
        setDiffByCommit((current) => ({ ...current, [commitHash]: payload.diff }))
      } catch (loadError) {
        const message = loadError instanceof Error ? loadError.message : "Failed to load commit diff"
        setDiffError((current) => ({ ...current, [commitHash]: message }))
      } finally {
        setDiffLoading((current) => ({ ...current, [commitHash]: false }))
      }
    },
    [diffByCommit, diffLoading, projectId],
  )

  useEffect(() => {
    if (!projectId) {
      appliedQueryCommitRef.current = null
      return
    }

    const requestedHash = initialCommitHash?.trim() ?? ""
    if (!requestedHash || requestedHash === appliedQueryCommitRef.current) {
      return
    }

    const matchingCommit =
      gitLog.find((commit) => commit.hash === requestedHash) ??
      gitLog.find((commit) => commit.hash.startsWith(requestedHash)) ??
      gitLog.find((commit) => requestedHash.startsWith(commit.hash))
    const targetHash = matchingCommit?.hash ?? requestedHash

    appliedQueryCommitRef.current = requestedHash
    setExpandedCommitHash(targetHash)
    setPendingScrollCommitHash(targetHash)
    void loadCommitDiff(targetHash)
  }, [gitLog, initialCommitHash, loadCommitDiff, projectId])

  useEffect(() => {
    if (!pendingScrollCommitHash) {
      return
    }

    const node = commitItemRefs.current[pendingScrollCommitHash]
    if (!node) {
      return
    }

    window.requestAnimationFrame(() => {
      node.scrollIntoView({ behavior: "smooth", block: "start" })
    })
    setPendingScrollCommitHash(null)
  }, [pendingScrollCommitHash, gitLog.length])

  const toggleCommit = (commitHash: string) => {
    const nextExpanded = expandedCommitHash === commitHash ? null : commitHash
    setExpandedCommitHash(nextExpanded)
    if (nextExpanded) {
      void loadCommitDiff(commitHash)
    }
  }

  return (
    <section className="rounded-xl p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Git History</h3>
        <p className="text-sm text-muted-foreground">Recent commits with expandable syntax-highlighted diffs.</p>
      </header>

      <section className="rounded-lg border bg-background/30 p-3">
        {isGitLogLoading ? (
          <p className="text-sm text-muted-foreground">Loading git history...</p>
        ) : gitLogError ? (
          <p className="text-sm text-rose-600 dark:text-rose-400">{gitLogError}</p>
        ) : gitLog.length === 0 ? (
          <p className="text-sm text-muted-foreground">No commits found.</p>
        ) : (
          <ul className="space-y-2">
            {gitLog.map((commit) => {
              const isExpanded = expandedCommitHash === commit.hash
              return (
                <li
                  key={commit.hash}
                  ref={(node) => {
                    commitItemRefs.current[commit.hash] = node
                  }}
                  className="rounded-md border bg-background/50 p-2"
                >
                  <button
                    type="button"
                    onClick={() => toggleCommit(commit.hash)}
                    className="w-full text-left"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs">{commit.hash}</span>
                      <span className="text-xs text-muted-foreground">{formatCommitDate(commit.date)}</span>
                    </div>
                    <p className="mt-1 text-sm">{commit.message}</p>
                    <p className="text-xs text-muted-foreground">
                      {commit.author} | {commit.files_changed} files | +{commit.insertions} / -{commit.deletions}
                    </p>
                  </button>

                  {isExpanded && (
                    <div className="mt-2">
                      <GitDiffViewer
                        commitHash={commit.hash}
                        diff={diffByCommit[commit.hash] ?? null}
                        isLoading={Boolean(diffLoading[commit.hash])}
                        error={diffError[commit.hash] ?? null}
                      />
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </section>
  )
}
