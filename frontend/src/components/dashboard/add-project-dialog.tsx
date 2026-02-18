import { type FormEvent, useEffect, useRef, useState } from "react"

import { apiFetch } from "@/api/client"
import { Button } from "@/components/ui/button"
import { useToastStore } from "@/stores/toast-store"
import type { ProjectSummary } from "@/types/project"

type AddProjectDialogProps = {
  open: boolean
  onClose: () => void
  onCreated?: (project: ProjectSummary) => void
}

export function AddProjectDialog({ open, onClose, onCreated }: AddProjectDialogProps) {
  const [path, setPath] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const pushToast = useToastStore((state) => state.pushToast)
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) {
      return
    }

    // Save the previously focused element to restore on close
    previousFocusRef.current = document.activeElement as HTMLElement | null

    // Lock body scroll
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"

    // Focus the dialog
    requestAnimationFrame(() => {
      const firstInput = dialogRef.current?.querySelector("input")
      if (firstInput) {
        ;(firstInput as HTMLElement).focus()
      }
    })

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose()
        return
      }

      // Focus trap — keep Tab cycling within the dialog
      if (event.key === "Tab" && dialogRef.current) {
        const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        )
        const first = focusableElements[0]
        const last = focusableElements[focusableElements.length - 1]

        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last?.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first?.focus()
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => {
      window.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = originalOverflow
      // Restore focus to the previously focused element
      previousFocusRef.current?.focus()
    }
  }, [onClose, open])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    const normalizedPath = path.trim()
    if (!normalizedPath) {
      setError("Project path is required.")
      return
    }

    setIsSubmitting(true)
    try {
      const project = await apiFetch<ProjectSummary>("/projects", {
        method: "POST",
        body: JSON.stringify({ path: normalizedPath }),
      })
      onCreated?.(project)
      pushToast({
        title: "Project added",
        description: project.name,
        tone: "success",
      })
      setPath("")
      onClose()
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Failed to add project."
      setError(message)
      pushToast({
        title: "Failed to add project",
        description: message,
        tone: "error",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!open) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-project-title"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div ref={dialogRef} className="w-full max-w-lg rounded-xl border bg-card p-5 shadow-lg">
        <header>
          <h2 id="add-project-title" className="text-lg font-semibold">Add Project</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter an absolute path to a project containing a <code>.ralph</code> directory.
          </p>
        </header>

        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium">
            Project Path
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={path}
              onChange={(event) => setPath(event.target.value)}
              placeholder="/home/endogen/projects/my-project"
              required
            />
          </label>

          {error && <p className="text-sm font-medium text-destructive">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Adding..." : "Add Project"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
