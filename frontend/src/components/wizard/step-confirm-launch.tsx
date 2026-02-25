import { useCallback, useState } from "react"
import { useNavigate } from "react-router-dom"

import { AlertCircle, FileText, FolderGit2, Loader2, Play, Rocket } from "lucide-react"

import { apiFetch } from "@/api/client"
import { Button } from "@/components/ui/button"
import { useToastStore } from "@/stores/toast-store"
import { useWizardStore } from "@/stores/wizard-store"

type CreateApiResponse = {
  project_id: string
  project_path: string
  started: boolean
  start_error: string | null
}

export function StepConfirmLaunch() {
  const navigate = useNavigate()
  const pushToast = useToastStore((s) => s.pushToast)

  const projectName = useWizardStore((s) => s.projectName)
  const projectMode = useWizardStore((s) => s.projectMode)
  const existingProjectPath = useWizardStore((s) => s.existingProjectPath)
  const cli = useWizardStore((s) => s.cli)
  const autoApproval = useWizardStore((s) => s.autoApproval)
  const maxIterations = useWizardStore((s) => s.maxIterations)
  const testCommand = useWizardStore((s) => s.testCommand)
  const modelOverride = useWizardStore((s) => s.modelOverride)
  const generatedFiles = useWizardStore((s) => s.generatedFiles)

  const isCreating = useWizardStore((s) => s.isCreating)
  const setIsCreating = useWizardStore((s) => s.setIsCreating)
  const createError = useWizardStore((s) => s.createError)
  const setCreateError = useWizardStore((s) => s.setCreateError)
  const reset = useWizardStore((s) => s.reset)

  const [startLoop, setStartLoop] = useState(false)
  const targetPath =
    projectMode === "existing"
      ? existingProjectPath.trim()
      : `~/projects/${projectName.trim().replace(/\s+/g, "-").toLowerCase()}`
  const fileActionLabel = projectMode === "existing" ? "Files to create/update" : "Files to create"

  const handleCreate = useCallback(async () => {
    setIsCreating(true)
    setCreateError(null)

    try {
      const response = await apiFetch<CreateApiResponse>("/wizard/create", {
        method: "POST",
        body: JSON.stringify({
          project_name: projectName,
          project_mode: projectMode,
          existing_project_path: existingProjectPath,
          cli,
          auto_approval: autoApproval,
          max_iterations: maxIterations,
          test_command: testCommand,
          model_override: modelOverride,
          files: generatedFiles,
          start_loop: startLoop,
        }),
      })

      pushToast({
        title: projectMode === "existing" ? "Project prepared!" : "Project created!",
        description: `${response.project_path} is ready${response.started ? " and building" : ""}`,
        tone: "success",
      })

      if (startLoop && !response.started) {
        pushToast({
          title: "Loop did not auto-start",
          description:
            response.start_error?.trim() ||
            "Project was prepared, but the loop did not start automatically. Start it from the project page.",
          tone: "info",
        })
      }

      reset()
      navigate(`/project/${response.project_id}`)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to prepare project"
      setCreateError(message)
      pushToast({
        title: "Failed to prepare project",
        description: message,
        tone: "error",
      })
    } finally {
      setIsCreating(false)
    }
  }, [
    projectName,
    projectMode,
    existingProjectPath,
    cli,
    autoApproval,
    maxIterations,
    testCommand,
    modelOverride,
    generatedFiles,
    startLoop,
    setIsCreating,
    setCreateError,
    reset,
    navigate,
    pushToast,
  ])

  const agentLabels: Record<string, string> = {
    claude: "Claude Code",
    codex: "Codex",
    opencode: "OpenCode",
    goose: "Goose",
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Confirm & Launch</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Review your project configuration and apply it.
        </p>
      </div>

      {/* Summary Card */}
      <div className="space-y-4 rounded-xl border bg-card/80 p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <FolderGit2 className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="font-semibold">{projectName}</p>
            <p className="text-xs text-muted-foreground">{targetPath}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border bg-muted/20 px-3 py-2">
            <p className="text-xs text-muted-foreground">Project Mode</p>
            <p className="text-sm font-medium capitalize">{projectMode}</p>
          </div>
          <div className="rounded-lg border bg-muted/20 px-3 py-2">
            <p className="text-xs text-muted-foreground">Agent</p>
            <p className="text-sm font-medium">{agentLabels[cli] ?? cli}</p>
          </div>
          <div className="rounded-lg border bg-muted/20 px-3 py-2">
            <p className="text-xs text-muted-foreground">Mode</p>
            <p className="text-sm font-medium capitalize">{autoApproval === "full-auto" ? "Full Auto" : "Sandboxed"}</p>
          </div>
          <div className="rounded-lg border bg-muted/20 px-3 py-2">
            <p className="text-xs text-muted-foreground">Max Iterations</p>
            <p className="text-sm font-medium">{maxIterations === 0 ? "Unlimited" : maxIterations}</p>
          </div>
          <div className="rounded-lg border bg-muted/20 px-3 py-2">
            <p className="text-xs text-muted-foreground">Test Command</p>
            <p className="text-sm font-medium font-mono">{testCommand || "—"}</p>
          </div>
        </div>

        {/* Files list */}
        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">{fileActionLabel} ({generatedFiles.length})</p>
          <div className="space-y-1">
            {generatedFiles.map((file) => (
              <div key={file.path} className="flex items-center gap-2 rounded-md px-2 py-1 text-xs">
                <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="font-mono">{file.path}</span>
                <span className="text-muted-foreground">
                  ({Math.round(file.content.length / 1024 * 10) / 10} KB)
                </span>
              </div>
            ))}
            <div className="flex items-center gap-2 rounded-md px-2 py-1 text-xs">
              <FileText className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="font-mono">.ralph/config.json</span>
              <span className="text-muted-foreground">(auto-generated)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Start loop toggle */}
      <label className="flex cursor-pointer items-center gap-3 rounded-xl border p-4 transition-colors hover:bg-accent/30">
        <input
          type="checkbox"
          checked={startLoop}
          onChange={(e) => setStartLoop(e.target.checked)}
          className="h-4 w-4 accent-primary"
        />
        <div className="flex items-center gap-2">
          <Play className="h-4 w-4 text-emerald-500" />
          <div>
            <p className="text-sm font-medium">Start building immediately</p>
            <p className="text-xs text-muted-foreground">
              Launch the Ralph loop right after project creation
            </p>
          </div>
        </div>
      </label>

      {/* Error */}
      {createError && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
          <div>
            <p className="text-sm font-medium text-rose-700 dark:text-rose-300">Preparation Failed</p>
            <p className="mt-0.5 text-xs text-rose-600 dark:text-rose-400">{createError}</p>
          </div>
        </div>
      )}

      {/* Create button */}
      <Button
        onClick={handleCreate}
        disabled={isCreating}
        className="w-full gap-2"
        size="lg"
      >
        {isCreating ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Preparing Project...
          </>
        ) : (
          <>
            <Rocket className="h-4 w-4" />
            {projectMode === "existing" ? "Prepare Project" : "Create Project"}
            {startLoop ? " & Start Building" : ""}
          </>
        )}
      </Button>
    </div>
  )
}
