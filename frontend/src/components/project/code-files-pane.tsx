import { useEffect, useState } from "react"

import { Editor } from "@monaco-editor/react"

import { apiFetch } from "@/api/client"
import type { ProjectFileContent } from "@/types/project"

type CodeFilesPaneProps = {
  projectId?: string
}

export function CodeFilesPane({ projectId }: CodeFilesPaneProps) {
  const [agentsContent, setAgentsContent] = useState("")
  const [promptContent, setPromptContent] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const loadFiles = async () => {
      if (!projectId) {
        setAgentsContent("")
        setPromptContent("")
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
      } catch (loadError) {
        if (cancelled) {
          return
        }
        const message = loadError instanceof Error ? loadError.message : "Failed to load AGENTS.md and PROMPT.md"
        setAgentsContent("")
        setPromptContent("")
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

  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Code Files</h3>
        <p className="text-sm text-muted-foreground">
          Side-by-side AGENTS.md and PROMPT.md editors. Save/inject/git features follow in phase 15.2+.
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
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          <article className="rounded-lg border bg-background/30 p-3">
            <p className="mb-2 font-mono text-sm">AGENTS.md</p>
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
            <p className="mb-2 font-mono text-sm">PROMPT.md</p>
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
      )}
    </section>
  )
}
