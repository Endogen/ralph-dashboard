import { useCallback, useEffect, useState } from "react"

import { Editor } from "@monaco-editor/react"

import { apiFetch } from "@/api/client"
import { useToastStore } from "@/stores/toast-store"
import type { ProjectFileContent } from "@/types/project"

type ControlFilesPaneProps = {
  projectId?: string
}

export function ControlFilesPane({ projectId }: ControlFilesPaneProps) {
  const [agentsContent, setAgentsContent] = useState("")
  const [promptContent, setPromptContent] = useState("")
  const [agentsSavedContent, setAgentsSavedContent] = useState("")
  const [promptSavedContent, setPromptSavedContent] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSavingAgents, setIsSavingAgents] = useState(false)
  const [isSavingPrompt, setIsSavingPrompt] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
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

  return (
    <section className="rounded-xl p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Agent Files</h3>
        <p className="text-sm text-muted-foreground">Edit AGENTS.md and PROMPT.md used by Ralph.</p>
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
        </div>
      )}
    </section>
  )
}
