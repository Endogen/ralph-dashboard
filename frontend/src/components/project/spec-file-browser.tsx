import { useEffect, useMemo, useState } from "react"

import { apiFetch } from "@/api/client"
import type { SpecFileInfo } from "@/types/project"

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

export function SpecFileBrowser({ projectId }: SpecFileBrowserProps) {
  const [specFiles, setSpecFiles] = useState<SpecFileInfo[]>([])
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const loadSpecs = async () => {
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
        if (cancelled) {
          return
        }
        setSpecFiles(files)
      } catch (loadError) {
        if (cancelled) {
          return
        }
        const message = loadError instanceof Error ? loadError.message : "Failed to load specs list"
        setSpecFiles([])
        setSelectedFileName(null)
        setError(message)
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadSpecs()

    return () => {
      cancelled = true
    }
  }, [projectId])

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

  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Specs</h3>
        <p className="text-sm text-muted-foreground">File browser sidebar for project `specs/*.md` documents.</p>
      </header>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="rounded-lg border bg-background/40 p-2">
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
                      <p className="truncate font-medium">{file.name}</p>
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
          ) : (
            <div className="space-y-2">
              <p className="font-mono text-sm">{selectedFile.name}</p>
              <p className="text-sm text-muted-foreground">
                Size: {formatFileSize(selectedFile.size)} | Updated: {formatTimestamp(selectedFile.modified)}
              </p>
              <p className="text-sm text-muted-foreground">
                Editor integration is next (Monaco in Phase 14.2).
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
