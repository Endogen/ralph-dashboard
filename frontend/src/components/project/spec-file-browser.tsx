import { useCallback, useEffect, useMemo, useState } from "react"

import { Editor } from "@monaco-editor/react"

import { apiFetch } from "@/api/client"
import { useToastStore } from "@/stores/toast-store"
import type { SpecFileContent, SpecFileInfo } from "@/types/project"

type SpecFileBrowserProps = {
  projectId?: string
}

function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function formatTimestamp(value: string): string {
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

function estimateByteSize(content: string): number {
  return new TextEncoder().encode(content).length
}

export function SpecFileBrowser({ projectId }: SpecFileBrowserProps) {
  const [specFiles, setSpecFiles] = useState<SpecFileInfo[]>([])
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null)
  const [selectedContent, setSelectedContent] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingContent, setIsLoadingContent] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [newSpecName, setNewSpecName] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [contentError, setContentError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [lastSavedContent, setLastSavedContent] = useState("")
  const pushToast = useToastStore((state) => state.pushToast)

  const loadSpecs = useCallback(async () => {
    if (!projectId) {
      setSpecFiles([])
      setSelectedFileName(null)
      setIsLoading(false)
      setError(null)
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const files = await apiFetch<SpecFileInfo[]>(`/projects/${projectId}/specs`)
      setSpecFiles(files)
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load specs list"
      setSpecFiles([])
      setSelectedFileName(null)
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void loadSpecs()
  }, [loadSpecs])

  useEffect(() => {
    if (specFiles.length === 0) {
      setSelectedFileName(null)
      return
    }

    setSelectedFileName((current) => {
      if (current && specFiles.some((file) => file.name === current)) {
        return current
      }
      return specFiles[0].name
    })
  }, [specFiles])

  const selectedFile = useMemo(
    () => specFiles.find((file) => file.name === selectedFileName) ?? null,
    [selectedFileName, specFiles],
  )

  useEffect(() => {
    let cancelled = false

    const loadSelectedFile = async () => {
      if (!projectId || !selectedFileName) {
        setSelectedContent("")
        setLastSavedContent("")
        setIsLoadingContent(false)
        setContentError(null)
        return
      }

      setIsLoadingContent(true)
      setContentError(null)
      try {
        const response = await apiFetch<SpecFileContent>(
          `/projects/${projectId}/specs/${encodeURIComponent(selectedFileName)}`,
        )
        if (cancelled) {
          return
        }
        setSelectedContent(response.content)
        setLastSavedContent(response.content)
      } catch (loadError) {
        if (cancelled) {
          return
        }
        const message = loadError instanceof Error ? loadError.message : "Failed to load spec file"
        setSelectedContent("")
        setLastSavedContent("")
        setContentError(message)
      } finally {
        if (!cancelled) {
          setIsLoadingContent(false)
        }
      }
    }

    void loadSelectedFile()

    return () => {
      cancelled = true
    }
  }, [projectId, selectedFileName])

  const handleCreateSpec = useCallback(async () => {
    if (!projectId) {
      return
    }

    const rawName = newSpecName.trim()
    if (!rawName) {
      setActionError("Enter a spec filename.")
      return
    }
    const normalizedName = rawName.endsWith(".md") ? rawName : `${rawName}.md`

    setIsCreating(true)
    setActionError(null)
    try {
      const defaultHeading = normalizedName.replace(/\.md$/i, "").replace(/[-_]/g, " ")
      const response = await apiFetch<SpecFileContent>(`/projects/${projectId}/specs`, {
        method: "POST",
        body: JSON.stringify({
          name: normalizedName,
          content: `# ${defaultHeading}\n`,
        }),
      })
      setSpecFiles((current) => {
        const next = [
          ...current.filter((file) => file.name !== response.name),
          {
            name: response.name,
            size: estimateByteSize(response.content),
            modified: new Date().toISOString(),
          },
        ]
        next.sort((left, right) => left.name.localeCompare(right.name))
        return next
      })
      setSelectedFileName(response.name)
      setSelectedContent(response.content)
      setLastSavedContent(response.content)
      setNewSpecName("")
      setContentError(null)
      pushToast({
        title: "Spec created",
        description: response.name,
        tone: "success",
      })
    } catch (createError) {
      const message = createError instanceof Error ? createError.message : "Failed to create spec file"
      setActionError(message)
      pushToast({
        title: "Create failed",
        description: message,
        tone: "error",
      })
    } finally {
      setIsCreating(false)
    }
  }, [newSpecName, projectId, pushToast])

  const handleDeleteSpec = useCallback(async () => {
    if (!projectId || !selectedFileName) {
      return
    }
    const shouldDelete = window.confirm(`Delete ${selectedFileName}? This cannot be undone.`)
    if (!shouldDelete) {
      return
    }

    setIsDeleting(true)
    setActionError(null)
    try {
      await apiFetch<void>(`/projects/${projectId}/specs/${encodeURIComponent(selectedFileName)}`, {
        method: "DELETE",
      })
      setSpecFiles((current) => current.filter((file) => file.name !== selectedFileName))
      setSelectedContent("")
      setLastSavedContent("")
      setContentError(null)
      pushToast({
        title: "Spec deleted",
        description: selectedFileName,
        tone: "success",
      })
    } catch (deleteError) {
      const message = deleteError instanceof Error ? deleteError.message : "Failed to delete spec file"
      setActionError(message)
      pushToast({
        title: "Delete failed",
        description: message,
        tone: "error",
      })
    } finally {
      setIsDeleting(false)
    }
  }, [projectId, pushToast, selectedFileName])

  const handleSaveSpec = useCallback(async () => {
    if (!projectId || !selectedFileName || selectedContent === lastSavedContent) {
      return
    }

    setIsSaving(true)
    setActionError(null)
    try {
      const response = await apiFetch<SpecFileContent>(
        `/projects/${projectId}/specs/${encodeURIComponent(selectedFileName)}`,
        {
          method: "PUT",
          body: JSON.stringify({ content: selectedContent }),
        },
      )
      setSelectedContent(response.content)
      setLastSavedContent(response.content)
      setSpecFiles((current) =>
        current.map((file) =>
          file.name === response.name
            ? {
                ...file,
                size: estimateByteSize(response.content),
                modified: new Date().toISOString(),
              }
            : file,
        ),
      )
      pushToast({
        title: "Spec saved",
        description: response.name,
        tone: "success",
      })
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "Failed to save spec file"
      setActionError(message)
      pushToast({
        title: "Save failed",
        description: message,
        tone: "error",
      })
    } finally {
      setIsSaving(false)
    }
  }, [lastSavedContent, projectId, pushToast, selectedContent, selectedFileName])

  const hasUnsavedChanges = Boolean(selectedFileName) && selectedContent !== lastSavedContent

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "s") {
        return
      }
      if (!selectedFileName) {
        return
      }
      if (selectedContent === lastSavedContent) {
        return
      }
      event.preventDefault()
      void handleSaveSpec()
    }

    window.addEventListener("keydown", onKeyDown)
    return () => {
      window.removeEventListener("keydown", onKeyDown)
    }
  }, [handleSaveSpec, lastSavedContent, selectedContent, selectedFileName])

  return (
    <section className="rounded-xl p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Specs</h3>
        <p className="text-sm text-muted-foreground">File browser sidebar for project `specs/*.md` documents.</p>
      </header>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="rounded-lg border bg-background/40 p-2">
          <div className="mb-2 space-y-2 px-1">
            <div className="flex gap-1">
              <input
                value={newSpecName}
                onChange={(event) => setNewSpecName(event.target.value)}
                placeholder="new-spec.md"
                className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm text-foreground"
              />
              <button
                type="button"
                onClick={handleCreateSpec}
                disabled={!projectId || isCreating}
                className="rounded-md border bg-primary px-2 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreating ? "Creating..." : "Create"}
              </button>
            </div>
            {actionError && <p className="text-xs text-rose-600 dark:text-rose-400">{actionError}</p>}
          </div>

          {isLoading ? (
            <p className="px-2 py-2 text-sm text-muted-foreground">Loading specs...</p>
          ) : error ? (
            <p className="px-2 py-2 text-sm text-rose-600 dark:text-rose-400">{error}</p>
          ) : specFiles.length === 0 ? (
            <p className="px-2 py-2 text-sm text-muted-foreground">No spec files found.</p>
          ) : (
            <ul className="space-y-1">
              {specFiles.map((file) => {
                const isSelected = file.name === selectedFileName
                return (
                  <li key={file.name}>
                    <button
                      type="button"
                      onClick={() => setSelectedFileName(file.name)}
                      className={`w-full rounded-md px-2 py-2 text-left text-sm ${
                        isSelected
                          ? "bg-primary/15 text-foreground"
                          : "text-muted-foreground hover:bg-background/70 hover:text-foreground"
                      }`}
                    >
                      <p className="truncate font-medium">
                        {file.name}
                        {isSelected && hasUnsavedChanges ? " *" : ""}
                      </p>
                      <p className="text-[11px]">{formatFileSize(file.size)}</p>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </aside>

        <div className="rounded-lg border bg-background/30 p-4">
          {!selectedFile ? (
            <p className="text-sm text-muted-foreground">Select a spec file from the sidebar.</p>
          ) : isLoadingContent ? (
            <p className="text-sm text-muted-foreground">Loading `{selectedFile.name}`...</p>
          ) : contentError ? (
            <p className="text-sm text-rose-600 dark:text-rose-400">{contentError}</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-sm">{selectedFile.name}</p>
                  <p className="text-sm text-muted-foreground">
                    Size: {formatFileSize(selectedFile.size)} | Updated: {formatTimestamp(selectedFile.modified)}
                  </p>
                  {hasUnsavedChanges && <p className="text-xs text-amber-600 dark:text-amber-300">Unsaved changes</p>}
                </div>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={handleSaveSpec}
                    disabled={isSaving || !hasUnsavedChanges}
                    className="rounded-md border bg-primary px-2 py-1 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSaving ? "Saving..." : "Save"}
                  </button>
                  <button
                    type="button"
                    onClick={handleDeleteSpec}
                    disabled={isDeleting}
                    className="rounded-md border border-rose-500/40 bg-rose-500/15 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-500/25 dark:text-rose-300 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isDeleting ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>

              <div className="h-[420px] overflow-hidden rounded-lg border">
                <Editor
                  height="100%"
                  defaultLanguage="markdown"
                  value={selectedContent}
                  onChange={(next) => setSelectedContent(next ?? "")}
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

              <p className="text-sm text-muted-foreground">
                Save is available via button or Ctrl+S / Cmd+S.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
