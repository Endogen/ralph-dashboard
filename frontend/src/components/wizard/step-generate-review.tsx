import { useEffect, useMemo, useRef, useState } from "react"

import { Editor } from "@monaco-editor/react"
import { AlertCircle, FileText, Loader2, RefreshCw, Sparkles } from "lucide-react"

import { apiFetch } from "@/api/client"
import { Button } from "@/components/ui/button"
import { showBrowserNotification, requestNotificationPermission } from "@/lib/browser-notifications"
import { type GeneratedFile, useWizardStore } from "@/stores/wizard-store"

type StartGenerateApiResponse = {
  request_id: string
}

type GenerationStatusApiResponse = {
  status: "pending" | "complete" | "error"
  files: GeneratedFile[] | null
  error: string | null
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
  const setGeneratedFiles = useWizardStore((s) => s.setGeneratedFiles)
  const updateFileContent = useWizardStore((s) => s.updateFileContent)
  const isGenerating = useWizardStore((s) => s.isGenerating)
  const setIsGenerating = useWizardStore((s) => s.setIsGenerating)
  const generateError = useWizardStore((s) => s.generateError)
  const setGenerateError = useWizardStore((s) => s.setGenerateError)
  const setActiveGenerateController = useWizardStore((s) => s.setActiveGenerateController)
  const setActiveGenerationRequestId = useWizardStore((s) => s.setActiveGenerationRequestId)
  const generationStartedAt = useWizardStore((s) => s.generationStartedAt)
  const setGenerationStartedAt = useWizardStore((s) => s.setGenerationStartedAt)
  const abortActiveGeneration = useWizardStore((s) => s.abortActiveGeneration)

  const [activeTab, setActiveTab] = useState(0)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const pollTimeoutRef = useRef<number | null>(null)
  const pollTokenRef = useRef(0)

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

  const stopPolling = () => {
    pollTokenRef.current += 1
    if (pollTimeoutRef.current !== null) {
      window.clearTimeout(pollTimeoutRef.current)
      pollTimeoutRef.current = null
    }
  }

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      pollTokenRef.current += 1
      if (pollTimeoutRef.current !== null) {
        window.clearTimeout(pollTimeoutRef.current)
        pollTimeoutRef.current = null
      }
    }
  }, [])

  const handleAbortGeneration = async () => {
    if (!isGenerating) return

    const requestId = useWizardStore.getState().activeGenerationRequestId
    stopPolling()
    abortActiveGeneration()
    if (requestId) {
      try {
        await apiFetch<CancelGenerateApiResponse>("/wizard/generate/cancel", {
          method: "POST",
          body: JSON.stringify({ request_id: requestId }),
        })
      } catch {
        // Ignore cancellation endpoint errors; local abort already completed.
      }
    }
    setGenerateError("Generation cancelled.")
  }

  const handleGenerate = async () => {
    if (isGenerating) return

    stopPolling()
    const generationToken = pollTokenRef.current + 1
    pollTokenRef.current = generationToken

    setIsGenerating(true)
    setGenerateError(null)
    setGenerationStartedAt(Date.now())
    void requestNotificationPermission()
    setActiveGenerateController(null)
    setActiveGenerationRequestId(null)

    try {
      // Step 1: Start async generation
      const startResponse = await apiFetch<StartGenerateApiResponse>("/wizard/generate/start", {
        method: "POST",
        body: JSON.stringify({
          project_name: projectName,
          project_description: projectDescription,
          tech_stack: techStack,
          cli,
          auto_approval: autoApproval,
          max_iterations: maxIterations,
          test_command: testCommand,
          model_override: modelOverride,
        }),
      })

      if (pollTokenRef.current !== generationToken || !useWizardStore.getState().isGenerating) {
        return
      }

      const requestId = startResponse.request_id
      setActiveGenerationRequestId(requestId)

      const finishGeneration = () => {
        setIsGenerating(false)
        setGenerationStartedAt(null)
        setActiveGenerateController(null)
        setActiveGenerationRequestId(null)
      }

      const scheduleNextPoll = () => {
        if (pollTokenRef.current !== generationToken) return
        pollTimeoutRef.current = window.setTimeout(() => {
          void poll()
        }, 2000)
      }

      // Step 2: Poll for status every 2 seconds (no overlap: next poll is scheduled after this one resolves)
      const poll = async () => {
        if (pollTokenRef.current !== generationToken) return

        try {
          const statusResponse = await apiFetch<GenerationStatusApiResponse>(
            `/wizard/generate/status/${encodeURIComponent(requestId)}`,
          )

          if (pollTokenRef.current !== generationToken) return

          if (statusResponse.status === "complete") {
            stopPolling()
            setGeneratedFiles(statusResponse.files ?? [])
            setActiveTab(0)
            finishGeneration()
            void showBrowserNotification({
              title: "✅ Plan generation complete",
              body: `${statusResponse.files?.length ?? 0} files ready for review.`,
              tag: "ralph-wizard-generate",
              onClick: () => window.focus(),
            })
          } else if (statusResponse.status === "error") {
            stopPolling()
            const errorMsg = statusResponse.error ?? "Generation failed"
            setGenerateError(errorMsg)
            finishGeneration()
            void showBrowserNotification({
              title: "❌ Plan generation failed",
              body: errorMsg,
              tag: "ralph-wizard-generate",
              onClick: () => window.focus(),
            })
          } else {
            scheduleNextPoll()
          }
        } catch (err) {
          if (pollTokenRef.current !== generationToken) return

          stopPolling()
          const message = err instanceof Error ? err.message : "Failed to check generation status"
          setGenerateError(message)
          finishGeneration()
        }
      }

      await poll()
    } catch (err) {
      if (pollTokenRef.current !== generationToken) return

      const message = err instanceof Error ? err.message : "Generation failed"
      setGenerateError(message)
      setIsGenerating(false)
      setGenerationStartedAt(null)
      setActiveGenerateController(null)
      setActiveGenerationRequestId(null)
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
            defaultLanguage="markdown"
            value={activeFile.content}
            onChange={(value) => updateFileContent(activeFile.path, value ?? "")}
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
      )}
    </div>
  )
}
