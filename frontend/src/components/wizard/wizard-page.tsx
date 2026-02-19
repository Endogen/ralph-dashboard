import { useCallback, useEffect, useMemo } from "react"
import { useNavigate } from "react-router-dom"

import { ArrowLeft, ArrowRight, Check } from "lucide-react"

import { apiFetch } from "@/api/client"
import { Button } from "@/components/ui/button"
import { StepAgentConfig } from "@/components/wizard/step-agent-config"
import { StepConfirmLaunch } from "@/components/wizard/step-confirm-launch"
import { StepGenerateReview } from "@/components/wizard/step-generate-review"
import { StepProjectSetup } from "@/components/wizard/step-project-setup"
import { useWizardStore } from "@/stores/wizard-store"

type CancelGenerateApiResponse = {
  cancelled: boolean
}

const steps = [
  { label: "Project Setup", component: StepProjectSetup },
  { label: "Agent Config", component: StepAgentConfig },
  { label: "Generate & Review", component: StepGenerateReview },
  { label: "Confirm & Launch", component: StepConfirmLaunch },
]

const stepLabelsShort = ["Setup", "Agent", "Review", "Launch"]

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <>
      {/* Mobile: two-row layout with short labels */}
      <div className="flex flex-col items-center gap-2 sm:hidden">
        <div className="flex items-center">
          {steps.map((step, idx) => {
            const isComplete = idx < currentStep
            const isCurrent = idx === currentStep

            return (
              <div key={step.label} className="flex items-center">
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all ${
                    isComplete
                      ? "bg-primary text-primary-foreground"
                      : isCurrent
                        ? "border-2 border-primary bg-primary/10 text-primary"
                        : "border-2 border-muted bg-muted/30 text-muted-foreground"
                  }`}
                >
                  {isComplete ? <Check className="h-4 w-4" /> : idx + 1}
                </div>
                {idx < steps.length - 1 && (
                  <div
                    className={`mx-1.5 h-0.5 w-8 ${
                      idx < currentStep ? "bg-primary" : "bg-muted"
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>
        <div className="flex items-start">
          {steps.map((step, idx) => {
            const isCurrent = idx === currentStep
            const isFuture = idx > currentStep

            return (
              <div key={step.label} className="flex items-center">
                <span
                  className={`w-8 text-center text-[10px] font-medium leading-tight ${
                    isCurrent ? "text-primary" : isFuture ? "text-muted-foreground" : "text-foreground"
                  }`}
                >
                  {stepLabelsShort[idx]}
                </span>
                {idx < steps.length - 1 && <div className="mx-1.5 w-8" />}
              </div>
            )
          })}
        </div>
      </div>

      {/* Desktop: original inline layout */}
      <div className="hidden items-center justify-center gap-0 sm:flex">
        {steps.map((step, idx) => {
          const isComplete = idx < currentStep
          const isCurrent = idx === currentStep
          const isFuture = idx > currentStep

          return (
            <div key={step.label} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all ${
                    isComplete
                      ? "bg-primary text-primary-foreground"
                      : isCurrent
                        ? "border-2 border-primary bg-primary/10 text-primary"
                        : "border-2 border-muted bg-muted/30 text-muted-foreground"
                  }`}
                >
                  {isComplete ? <Check className="h-4 w-4" /> : idx + 1}
                </div>
                <span
                  className={`mt-1.5 text-[10px] font-medium ${
                    isCurrent ? "text-primary" : isFuture ? "text-muted-foreground" : "text-foreground"
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <div
                  className={`mx-2 mb-5 h-0.5 w-12 ${
                    idx < currentStep ? "bg-primary" : "bg-muted"
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>
    </>
  )
}

export function WizardPage() {
  const navigate = useNavigate()
  const currentStep = useWizardStore((s) => s.currentStep)
  const setCurrentStep = useWizardStore((s) => s.setCurrentStep)
  const projectName = useWizardStore((s) => s.projectName)
  const projectDescription = useWizardStore((s) => s.projectDescription)
  const techStack = useWizardStore((s) => s.techStack)
  const cli = useWizardStore((s) => s.cli)
  const autoApproval = useWizardStore((s) => s.autoApproval)
  const maxIterations = useWizardStore((s) => s.maxIterations)
  const testCommand = useWizardStore((s) => s.testCommand)
  const modelOverride = useWizardStore((s) => s.modelOverride)
  const generatedFiles = useWizardStore((s) => s.generatedFiles)
  const isGenerating = useWizardStore((s) => s.isGenerating)
  const activeGenerationRequestId = useWizardStore((s) => s.activeGenerationRequestId)
  const isCreating = useWizardStore((s) => s.isCreating)
  const reset = useWizardStore((s) => s.reset)

  const canGoNext = useMemo(() => {
    switch (currentStep) {
      case 0:
        return projectName.trim().length > 0 && projectDescription.trim().length > 0
      case 1:
        return true
      case 2:
        return generatedFiles.length > 0 && !isGenerating
      case 3:
        return false // Last step uses its own button
      default:
        return false
    }
  }, [currentStep, projectName, projectDescription, generatedFiles, isGenerating])

  const goNext = useCallback(() => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }, [currentStep, setCurrentStep])

  const goBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }, [currentStep, setCurrentStep])

  const hasDraft = useMemo(() => {
    return (
      projectName.trim().length > 0 ||
      projectDescription.trim().length > 0 ||
      techStack.length > 0 ||
      cli !== "claude" ||
      autoApproval !== "sandboxed" ||
      maxIterations !== 20 ||
      testCommand.trim().length > 0 ||
      modelOverride.trim().length > 0 ||
      generatedFiles.length > 0 ||
      isGenerating ||
      isCreating ||
      currentStep > 0
    )
  }, [
    autoApproval,
    cli,
    currentStep,
    generatedFiles.length,
    isCreating,
    isGenerating,
    maxIterations,
    modelOverride,
    projectDescription,
    projectName,
    techStack.length,
    testCommand,
  ])

  useEffect(() => {
    if (!isGenerating) return

    const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ""
    }

    window.addEventListener("beforeunload", beforeUnloadHandler)
    return () => {
      window.removeEventListener("beforeunload", beforeUnloadHandler)
    }
  }, [isGenerating])

  const handleCancel = useCallback(async () => {
    if (hasDraft) {
      const message = isGenerating
        ? "Generation is still running. Cancel and discard this project draft?"
        : "Discard this new project draft?"
      const confirmed = window.confirm(message)
      if (!confirmed) return
    }

    if (isGenerating && activeGenerationRequestId) {
      try {
        await apiFetch<CancelGenerateApiResponse>("/wizard/generate/cancel", {
          method: "POST",
          body: JSON.stringify({ request_id: activeGenerationRequestId }),
        })
      } catch {
        // Ignore cancellation endpoint errors; local reset will still abort the request.
      }
    }

    reset()
    navigate("/")
  }, [activeGenerationRequestId, hasDraft, isGenerating, navigate, reset])

  const StepComponent = steps[currentStep].component

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">New Project</h1>
          <p className="text-sm text-muted-foreground">Create a new project with AI-generated specs and plans.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={handleCancel}>
          Cancel
        </Button>
      </header>

      <StepIndicator currentStep={currentStep} />

      <div className="min-h-[400px] rounded-xl border bg-card/50 p-5 shadow-sm">
        <StepComponent />
      </div>

      {/* Navigation */}
      {currentStep < steps.length - 1 && (
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={goBack}
            disabled={currentStep === 0}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          <Button onClick={goNext} disabled={!canGoNext} className="gap-2">
            Next
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {currentStep === steps.length - 1 && (
        <div className="flex items-center justify-start">
          <Button variant="outline" onClick={goBack} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
        </div>
      )}
    </div>
  )
}
