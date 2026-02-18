import { type KeyboardEvent, useState } from "react"

import { X } from "lucide-react"

import { useWizardStore } from "@/stores/wizard-store"

export function StepProjectSetup() {
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

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Project Setup</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Describe what you want to build. The more detail you provide, the better the generated plan will be.
        </p>
      </div>

      <div className="space-y-4">
        <label className="block text-sm font-medium">
          Project Name
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="my-awesome-project"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            This becomes the directory name under your projects folder.
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
          />
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

        {projectName.trim() && (
          <div className="rounded-lg border border-dashed bg-muted/30 px-4 py-3">
            <p className="text-xs text-muted-foreground">
              Target directory: <code className="font-mono text-foreground">~/projects/{projectName.trim()}</code>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
