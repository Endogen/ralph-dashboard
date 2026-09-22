import { useEffect, useMemo, useState } from "react"

import { Editor } from "@/components/ui/code-editor"
import { AlertCircle, FileText, Loader2, RefreshCw, Sparkles } from "lucide-react"

import { apiFetch } from "@/api/client"
import { Button } from "@/components/ui/button"
import { ensureGenerationPolling } from "@/api/generation"
import { useWizardStore } from "@/stores/wizard-store"

type StartGenerateApiResponse = {
  request_id: string
}

type CancelGenerateApiResponse = {
  cancelled: boolean
}

function formatElapsed(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins === 0) return `${secs}s`
  return `${mins}m ${secs}s`
}

function getFileLabel(path: string): string {
  if (path === "specs/overview.md") return "Overview"
  if (path === "specs/features.md") return "Features"
  if (path === "IMPLEMENTATION_PLAN.md") return "Implementation Plan"
  if (path === "AGENTS.md") return "AGENTS.md"
  if (path === "PROMPT.md") return "PROMPT.md"
  return path
}

export function StepGenerateReview() {
  const projectName = useWizardStore((s) => s.projectName)
  const projectDescription = useWizardStore((s) => s.projectDescription)
  const techStack = useWizardStore((s) => s.techStack)
  const cli = useWizardStore((s) => s.cli)
  const testCommand = useWizardStore((s) => s.testCommand)
  const maxIterations = useWizardStore((s) => s.maxIterations)
  const autoApproval = useWizardStore((s) => s.autoApproval)
  const modelOverride = useWizardStore((s) => s.modelOverride)
  const generatorAgentLabel = cli === "codex" ? "Codex" : "Claude Code"

  const generatedFiles = useWizardStore((s) => s.generatedFiles)
  const updateFileContent = useWizardStore((s) => s.updateFileContent)
  const isGenerating = useWizardStore((s) => s.isGenerating)
  const setIsGenerating = useWizardStore((s) => s.setIsGenerating)
  const generateError = useWizardStore((s) => s.generateError)
  const setGenerateError = useWizardStore((s) => s.setGenerateError)
  const setActiveGenerationRequestId = useWizardStore((s) => s.setActiveGenerationRequestId)
  const generationStartedAt = useWizardStore((s) => s.generationStartedAt)
  const setGenerationStartedAt = useWizardStore((s) => s.setGenerationStartedAt)
  const abortActiveGeneration = useWizardStore((s) => s.abortActiveGeneration)

  const [activeTab, setActiveTab] = useState(0)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useEffect(() => {
    if (!isGenerating || !generationStartedAt) {
      setElapsedSeconds(0)
      return
    }

    const updateElapsed = () => {
      const elapsed = Math.max(0, Math.floor((Date.now() - generationStartedAt) / 1000))
      setElapsedSeconds(elapsed)
    }

    updateElapsed()
    const intervalId = window.setInterval(updateElapsed, 1000)
    return () => window.clearInterval(intervalId)
  }, [generationStartedAt, isGenerating])

  const elapsedLabel = useMemo(() => formatElapsed(elapsedSeconds), [elapsedSeconds])

  const handleAbortGeneration = async () => {
    const requestId = useWizardStore.getState().activeGenerationRequestId
    if (!requestId) return
    try {
      await apiFetch<CancelGenerateApiResponse>("/wizard/generate/cancel", {
        method: "POST", body: JSON.stringify({ request_id: requestId }),
      })
      abortActiveGeneration()
      setGenerateError("Generation cancelled.")
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Cancellation failed; generation is still tracked.")
    }
  }

  const handleGenerate = async () => {
    if (isGenerating) return
    const requestId = crypto.randomUUID()
    setIsGenerating(true)
    setGenerateError(null)
    setGenerationStartedAt(Date.now())
    setActiveGenerationRequestId(requestId)
    try {
      const draft = useWizardStore.getState()
      await apiFetch<StartGenerateApiResponse>("/wizard/generate/start", {
        method: "POST",
        body: JSON.stringify({ request_id: requestId, project_name: projectName,
          project_mode: draft.projectMode, existing_project_path: draft.existingProjectPath,
          project_description: projectDescription, tech_stack: techStack, cli,
          auto_approval: autoApproval, max_iterations: maxIterations,
          test_command: testCommand, model_override: modelOverride }),
      })
      ensureGenerationPolling()
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Generation failed")
      // The server may have accepted a request whose response was lost.
      ensureGenerationPolling()
    }
  }

  // No files generated yet — show generate button
  if (generatedFiles.length === 0 && !isGenerating) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold">Generate & Review</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Generate detailed specifications and an implementation plan using AI based on your project description.
          </p>
        </div>

        <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed bg-muted/20 px-6 py-12">
          <Sparkles className="h-10 w-10 text-primary/60" />
          <div className="text-center">
            <p className="text-sm font-medium">Ready to generate your project plan</p>
            <p className="mt-1 text-xs text-muted-foreground">
              This will use {generatorAgentLabel} to create specs, an implementation plan, and agent instructions.
            </p>
          </div>
          <Button onClick={handleGenerate} className="gap-2">
            <Sparkles className="h-4 w-4" />
            Generate Plan
          </Button>
        </div>

        {generateError && (
          <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
            <div>
              <p className="text-sm font-medium text-rose-700 dark:text-rose-300">Generation Failed</p>
              <p className="mt-0.5 text-xs text-rose-600 dark:text-rose-400">{generateError}</p>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Loading state
  if (isGenerating) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold">Generate & Review</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Generating your project specs and implementation plan...
          </p>
        </div>

        <div className="flex flex-col items-center gap-4 rounded-xl border bg-muted/20 px-6 py-16">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <div className="text-center">
            <p className="text-sm font-medium">Generating project files...</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {generatorAgentLabel} is creating detailed specs and an implementation plan. Duration depends on the model used.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Elapsed: {elapsedLabel}</p>
          </div>
          <Button variant="outline" onClick={handleAbortGeneration}>
            Cancel Generation
          </Button>
        </div>
      </div>
    )
  }

  // Files generated — show tabs with editors
  const activeFile = generatedFiles[activeTab]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Review & Edit</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Review the generated files and edit them before creating the project.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleGenerate} className="shrink-0 gap-2">
          <RefreshCw className="h-3.5 w-3.5" />
          Regenerate
        </Button>
      </div>

      {generateError && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
          <p className="text-sm text-rose-700 dark:text-rose-300">{generateError}</p>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 overflow-x-auto rounded-lg border bg-muted/30 p-1">
        {generatedFiles.map((file, idx) => (
          <button
            key={file.path}
            type="button"
            onClick={() => setActiveTab(idx)}
            className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              idx === activeTab
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            {getFileLabel(file.path)}
          </button>
        ))}
      </div>

      {/* Editor */}
      {activeFile && (
        <div className="h-[480px] overflow-hidden rounded-lg border">
          <Editor
            height="100%"
            value={activeFile.content}
            onChange={(value) => updateFileContent(activeFile.path, value)}
            ariaLabel="Generated file editor"
            documentId={`wizard/${activeFile.path}`}
          />
        </div>
      )}
    </div>
  )
}
