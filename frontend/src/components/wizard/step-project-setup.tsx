import { type KeyboardEvent, useState } from "react"

import { X } from "lucide-react"

import { useWizardStore } from "@/stores/wizard-store"

function deriveProjectNameFromPath(pathValue: string): string {
  const trimmed = pathValue.trim().replace(/\/+$/, "")
  if (!trimmed) return ""
  const segments = trimmed.split("/")
  const lastSegment = segments[segments.length - 1]?.trim() ?? ""
  if (!lastSegment) return ""
  return lastSegment
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9._-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "")
}

export function StepProjectSetup() {
  const projectMode = useWizardStore((s) => s.projectMode)
  const setProjectMode = useWizardStore((s) => s.setProjectMode)
  const existingProjectPath = useWizardStore((s) => s.existingProjectPath)
  const setExistingProjectPath = useWizardStore((s) => s.setExistingProjectPath)
  const projectName = useWizardStore((s) => s.projectName)
  const setProjectName = useWizardStore((s) => s.setProjectName)
  const projectDescription = useWizardStore((s) => s.projectDescription)
  const setProjectDescription = useWizardStore((s) => s.setProjectDescription)
  const techStack = useWizardStore((s) => s.techStack)
  const addTechTag = useWizardStore((s) => s.addTechTag)
  const removeTechTag = useWizardStore((s) => s.removeTechTag)

  const [tagInput, setTagInput] = useState("")

  const handleTagKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      const tag = tagInput.trim()
      if (tag) {
        addTechTag(tag)
        setTagInput("")
      }
    } else if (e.key === "Backspace" && tagInput === "" && techStack.length > 0) {
      removeTechTag(techStack[techStack.length - 1])
    }
  }

  const handleExistingPathChange = (rawPath: string) => {
    setExistingProjectPath(rawPath)
    if (projectName.trim()) {
      return
    }
    const derived = deriveProjectNameFromPath(rawPath)
    if (derived) {
      setProjectName(derived)
    }
  }

  const normalizedProjectName = projectName.trim().replace(/\s+/g, "-").toLowerCase()

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Project Setup</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose whether to start from a new project or an existing codebase, then describe what you want to build.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium">Project Base</label>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => setProjectMode("new")}
              className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                projectMode === "new"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-input hover:bg-accent/30"
              }`}
            >
              <p className="font-medium">New Project</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Create a new folder under your Ralph project roots.</p>
            </button>
            <button
              type="button"
              onClick={() => setProjectMode("existing")}
              className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                projectMode === "existing"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-input hover:bg-accent/30"
              }`}
            >
              <p className="font-medium">Existing Project</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Use an existing repo, with or without a current `.ralph/` folder.</p>
            </button>
          </div>
        </div>

        {projectMode === "existing" && (
          <label className="block text-sm font-medium">
            Existing Project Path
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={existingProjectPath}
              onChange={(e) => handleExistingPathChange(e.target.value)}
              placeholder="/Users/you/projects/existing-app"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Must be an existing directory inside one of your configured `RALPH_PROJECT_DIRS` roots.
            </p>
          </label>
        )}

        <label className="block text-sm font-medium">
          Project Name
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="my-awesome-project"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            {projectMode === "new"
              ? "This becomes the directory name under your projects folder. Spaces are converted to hyphens automatically."
              : 'Used for wizard generation context. Directory path comes from "Existing Project Path".'}
          </p>
        </label>

        <label className="block text-sm font-medium">
          Project Description
          <textarea
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            value={projectDescription}
            onChange={(e) => setProjectDescription(e.target.value)}
            placeholder="Describe what you want to build in detail. Include features, user flows, API endpoints, data models — the more context the better."
            rows={8}
            maxLength={20000}
          />
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <span>Be as detailed as you like — the LLM will distill it into a spec.</span>
            <span className={projectDescription.length > 18000 ? "text-destructive font-medium" : ""}>
              {projectDescription.length.toLocaleString()} / 20,000
            </span>
          </div>
        </label>

        <div>
          <label className="block text-sm font-medium">
            Tech Stack
            <span className="ml-1 font-normal text-muted-foreground">(optional)</span>
          </label>
          <div className="mt-1 flex flex-wrap items-center gap-2 rounded-md border border-input bg-background px-3 py-2">
            {techStack.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => removeTechTag(tag)}
                  className="rounded-sm p-0.5 hover:bg-primary/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            <input
              className="min-w-[120px] flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              placeholder={techStack.length === 0 ? "Type and press Enter (e.g., React, Python, PostgreSQL)" : "Add more..."}
            />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Press Enter or comma to add a tag. These help guide the spec generation.
          </p>
        </div>

        {projectName.trim() && projectMode === "new" && (
          <div className="rounded-lg border border-dashed bg-muted/30 px-4 py-3">
            <p className="text-xs text-muted-foreground">
              Target directory: <code className="font-mono text-foreground">~/projects/{normalizedProjectName}</code>
            </p>
          </div>
        )}

        {projectMode === "existing" && existingProjectPath.trim() && (
          <div className="rounded-lg border border-dashed bg-muted/30 px-4 py-3">
            <p className="text-xs text-muted-foreground">
              Target directory: <code className="font-mono text-foreground">{existingProjectPath.trim()}</code>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
