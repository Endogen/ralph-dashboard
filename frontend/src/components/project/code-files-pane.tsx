import { useCallback, useEffect, useState } from "react"

import { Editor } from "@monaco-editor/react"

import { apiFetch } from "@/api/client"
import { GitDiffViewer } from "@/components/project/git-diff-viewer"
import { useToastStore } from "@/stores/toast-store"
import type { GitCommitDiff, GitCommitSummary, ProjectFileContent } from "@/types/project"

type CodeFilesPaneProps = {
  projectId?: string
}

type InjectResponse = {
  content: string
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

export function CodeFilesPane({ projectId }: CodeFilesPaneProps) {
  const [agentsContent, setAgentsContent] = useState("")
  const [promptContent, setPromptContent] = useState("")
  const [agentsSavedContent, setAgentsSavedContent] = useState("")
  const [promptSavedContent, setPromptSavedContent] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSavingAgents, setIsSavingAgents] = useState(false)
  const [isSavingPrompt, setIsSavingPrompt] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [injectText, setInjectText] = useState("")
  const [isInjecting, setIsInjecting] = useState(false)
  const [injectResult, setInjectResult] = useState<string | null>(null)
  const [gitLog, setGitLog] = useState<GitCommitSummary[]>([])
  const [isGitLogLoading, setIsGitLogLoading] = useState(false)
  const [gitLogError, setGitLogError] = useState<string | null>(null)
  const [expandedCommitHash, setExpandedCommitHash] = useState<string | null>(null)
  const [diffByCommit, setDiffByCommit] = useState<Record<string, string>>({})
  const [diffLoading, setDiffLoading] = useState<Record<string, boolean>>({})
  const [diffError, setDiffError] = useState<Record<string, string>>({})
  const pushToast = useToastStore((state) => state.pushToast)

  useEffect(() => {
    let cancelled = false

    const loadFiles = async () => {
      if (!projectId) {
        setAgentsContent("")
        setPromptContent("")
        setAgentsSavedContent("")
        setPromptSavedContent("")
        setIsLoading(false)
        setError(null)
        return
      }

      setIsLoading(true)
      setError(null)
      try {
        const [agentsResponse, promptResponse] = await Promise.all([
          apiFetch<ProjectFileContent>(`/projects/${projectId}/files/agents`),
          apiFetch<ProjectFileContent>(`/projects/${projectId}/files/prompt`),
        ])
        if (cancelled) {
          return
        }
        setAgentsContent(agentsResponse.content)
        setPromptContent(promptResponse.content)
        setAgentsSavedContent(agentsResponse.content)
        setPromptSavedContent(promptResponse.content)
      } catch (loadError) {
        if (cancelled) {
          return
        }
        const message = loadError instanceof Error ? loadError.message : "Failed to load AGENTS.md and PROMPT.md"
        setAgentsContent("")
        setPromptContent("")
        setAgentsSavedContent("")
        setPromptSavedContent("")
        setError(message)
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadFiles()

    return () => {
      cancelled = true
    }
  }, [projectId])

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

  const handleInject = useCallback(async () => {
    if (!projectId) {
      return
    }

    const message = injectText.trim()
    if (!message) {
      setInjectResult("Enter an inject message before sending.")
      pushToast({
        title: "Inject message required",
        tone: "error",
      })
      return
    }

    setIsInjecting(true)
    setInjectResult(null)
    try {
      const payload = await apiFetch<InjectResponse>(`/projects/${projectId}/inject`, {
        method: "POST",
        body: JSON.stringify({ message }),
      })
      setInjectText("")
      setInjectResult(`Injected (${payload.content.length} chars).`)
      pushToast({
        title: "Instructions injected",
        description: `${payload.content.length} characters queued`,
        tone: "success",
      })
    } catch (injectError) {
      const messageText = injectError instanceof Error ? injectError.message : "Failed to send inject message"
      setInjectResult(messageText)
      pushToast({
        title: "Inject failed",
        description: messageText,
        tone: "error",
      })
    } finally {
      setIsInjecting(false)
    }
  }, [injectText, projectId, pushToast])

  const handleSaveAgents = useCallback(async () => {
    if (!projectId || agentsContent === agentsSavedContent) {
      return
    }

    setIsSavingAgents(true)
    setSaveMessage(null)
    try {
      const response = await apiFetch<ProjectFileContent>(`/projects/${projectId}/files/agents`, {
        method: "PUT",
        body: JSON.stringify({ content: agentsContent }),
      })
      setAgentsContent(response.content)
      setAgentsSavedContent(response.content)
      setSaveMessage("Saved AGENTS.md")
      pushToast({
        title: "AGENTS.md saved",
        tone: "success",
      })
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "Failed to save AGENTS.md"
      setSaveMessage(message)
      pushToast({
        title: "Failed to save AGENTS.md",
        description: message,
        tone: "error",
      })
    } finally {
      setIsSavingAgents(false)
    }
  }, [agentsContent, agentsSavedContent, projectId, pushToast])

  const handleSavePrompt = useCallback(async () => {
    if (!projectId || promptContent === promptSavedContent) {
      return
    }

    setIsSavingPrompt(true)
    setSaveMessage(null)
    try {
      const response = await apiFetch<ProjectFileContent>(`/projects/${projectId}/files/prompt`, {
        method: "PUT",
        body: JSON.stringify({ content: promptContent }),
      })
      setPromptContent(response.content)
      setPromptSavedContent(response.content)
      setSaveMessage("Saved PROMPT.md")
      pushToast({
        title: "PROMPT.md saved",
        tone: "success",
      })
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "Failed to save PROMPT.md"
      setSaveMessage(message)
      pushToast({
        title: "Failed to save PROMPT.md",
        description: message,
        tone: "error",
      })
    } finally {
      setIsSavingPrompt(false)
    }
  }, [projectId, promptContent, promptSavedContent, pushToast])

  const agentsDirty = agentsContent !== agentsSavedContent
  const promptDirty = promptContent !== promptSavedContent

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

  const toggleCommit = (commitHash: string) => {
    const nextExpanded = expandedCommitHash === commitHash ? null : commitHash
    setExpandedCommitHash(nextExpanded)
    if (nextExpanded) {
      void loadCommitDiff(commitHash)
    }
  }

  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Code Files</h3>
        <p className="text-sm text-muted-foreground">
          Side-by-side AGENTS.md and PROMPT.md editors with runtime inject and git history tooling.
        </p>
      </header>

      {isLoading ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-muted-foreground">
          Loading AGENTS.md and PROMPT.md...
        </div>
      ) : error ? (
        <div className="rounded-lg border bg-background/40 p-4 text-sm text-rose-600 dark:text-rose-400">
          {error}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            <article className="rounded-lg border bg-background/30 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="font-mono text-sm">AGENTS.md{agentsDirty ? " *" : ""}</p>
                <button
                  type="button"
                  onClick={handleSaveAgents}
                  disabled={isSavingAgents || !agentsDirty}
                  className="rounded-md border bg-primary px-2 py-1 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSavingAgents ? "Saving..." : "Save"}
                </button>
              </div>
              <div className="h-[420px] overflow-hidden rounded-lg border">
                <Editor
                  height="100%"
                  defaultLanguage="markdown"
                  value={agentsContent}
                  onChange={(next) => setAgentsContent(next ?? "")}
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    wordWrap: "on",
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              </div>
            </article>

            <article className="rounded-lg border bg-background/30 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="font-mono text-sm">PROMPT.md{promptDirty ? " *" : ""}</p>
                <button
                  type="button"
                  onClick={handleSavePrompt}
                  disabled={isSavingPrompt || !promptDirty}
                  className="rounded-md border bg-primary px-2 py-1 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSavingPrompt ? "Saving..." : "Save"}
                </button>
              </div>
              <div className="h-[420px] overflow-hidden rounded-lg border">
                <Editor
                  height="100%"
                  defaultLanguage="markdown"
                  value={promptContent}
                  onChange={(next) => setPromptContent(next ?? "")}
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    wordWrap: "on",
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              </div>
            </article>
          </div>
          {saveMessage && <p className="text-xs text-muted-foreground">{saveMessage}</p>}

          <section className="rounded-lg border bg-background/30 p-3">
            <p className="text-sm font-semibold">Inject Message</p>
            <p className="mb-2 text-xs text-muted-foreground">Send runtime instructions for the next loop iteration.</p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <textarea
                value={injectText}
                onChange={(event) => setInjectText(event.target.value)}
                rows={3}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground"
                placeholder="Inject instructions for next iteration..."
              />
              <button
                type="button"
                onClick={handleInject}
                disabled={isInjecting}
                className="rounded-md border bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isInjecting ? "Sending..." : "Send Inject"}
              </button>
            </div>
            {injectResult && <p className="mt-2 text-xs text-muted-foreground">{injectResult}</p>}
          </section>

          <section className="rounded-lg border bg-background/30 p-3">
            <p className="text-sm font-semibold">Git History</p>
            <p className="mb-2 text-xs text-muted-foreground">Recent commits with expandable syntax-highlighted diffs.</p>
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
                    <li key={commit.hash} className="rounded-md border bg-background/50 p-2">
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
        </div>
      )}
    </section>
  )
}
