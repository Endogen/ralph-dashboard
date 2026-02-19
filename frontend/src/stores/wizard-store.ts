import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

export type AgentChoice = "codex" | "claude"
export type ApprovalMode = "full-auto" | "sandboxed"

export type GeneratedFile = {
  path: string
  content: string
}

type WizardState = {
  // Step tracking
  currentStep: number
  setCurrentStep: (step: number) => void

  // Step 1: Project Setup
  projectName: string
  setProjectName: (name: string) => void
  projectDescription: string
  setProjectDescription: (desc: string) => void
  techStack: string[]
  setTechStack: (stack: string[]) => void
  addTechTag: (tag: string) => void
  removeTechTag: (tag: string) => void

  // Step 2: Agent Configuration
  cli: AgentChoice
  setCli: (cli: AgentChoice) => void
  autoApproval: ApprovalMode
  setAutoApproval: (mode: ApprovalMode) => void
  maxIterations: number
  setMaxIterations: (max: number) => void
  testCommand: string
  setTestCommand: (cmd: string) => void
  modelOverride: string
  setModelOverride: (model: string) => void

  // Step 3: Generate & Review
  generatedFiles: GeneratedFile[]
  setGeneratedFiles: (files: GeneratedFile[]) => void
  updateFileContent: (path: string, content: string) => void
  isGenerating: boolean
  setIsGenerating: (generating: boolean) => void
  generateError: string | null
  setGenerateError: (error: string | null) => void
  activeGenerateController: AbortController | null
  setActiveGenerateController: (controller: AbortController | null) => void
  activeGenerationRequestId: string | null
  setActiveGenerationRequestId: (requestId: string | null) => void
  generationStartedAt: number | null
  setGenerationStartedAt: (startedAt: number | null) => void
  abortActiveGeneration: () => void

  // Step 4: Create
  isCreating: boolean
  setIsCreating: (creating: boolean) => void
  createError: string | null
  setCreateError: (error: string | null) => void

  // Reset
  reset: () => void
}

const initialState = {
  currentStep: 0,
  projectName: "",
  projectDescription: "",
  techStack: [] as string[],
  cli: "claude" as AgentChoice,
  autoApproval: "sandboxed" as ApprovalMode,
  maxIterations: 20,
  testCommand: "",
  modelOverride: "",
  generatedFiles: [] as GeneratedFile[],
  isGenerating: false,
  generateError: null as string | null,
  activeGenerateController: null as AbortController | null,
  activeGenerationRequestId: null as string | null,
  generationStartedAt: null as number | null,
  isCreating: false,
  createError: null as string | null,
}

export const useWizardStore = create<WizardState>()(
  persist(
    (set, get) => ({
      ...initialState,

      setCurrentStep: (step) => set({ currentStep: step }),

      setProjectName: (projectName) => set({ projectName }),
      setProjectDescription: (projectDescription) => set({ projectDescription }),
      setTechStack: (techStack) => set({ techStack }),
      addTechTag: (tag) =>
        set((state) => {
          const normalized = tag.trim().toLowerCase()
          if (!normalized || state.techStack.includes(normalized)) return state
          return { techStack: [...state.techStack, normalized] }
        }),
      removeTechTag: (tag) =>
        set((state) => ({
          techStack: state.techStack.filter((t) => t !== tag),
        })),

      setCli: (cli) => set({ cli, modelOverride: "" }),
      setAutoApproval: (autoApproval) => set({ autoApproval }),
      setMaxIterations: (maxIterations) => set({ maxIterations }),
      setTestCommand: (testCommand) => set({ testCommand }),
      setModelOverride: (modelOverride) => set({ modelOverride }),

      setGeneratedFiles: (generatedFiles) => set({ generatedFiles }),
      updateFileContent: (path, content) =>
        set((state) => ({
          generatedFiles: state.generatedFiles.map((f) =>
            f.path === path ? { ...f, content } : f,
          ),
        })),
      setIsGenerating: (isGenerating) => set({ isGenerating }),
      setGenerateError: (generateError) => set({ generateError }),
      setActiveGenerateController: (activeGenerateController) => set({ activeGenerateController }),
      setActiveGenerationRequestId: (activeGenerationRequestId) => set({ activeGenerationRequestId }),
      setGenerationStartedAt: (generationStartedAt) => set({ generationStartedAt }),
      abortActiveGeneration: () => {
        const controller = get().activeGenerateController
        if (controller) {
          controller.abort()
        }
        set({
          activeGenerateController: null,
          activeGenerationRequestId: null,
          generationStartedAt: null,
          isGenerating: false,
        })
      },

      setIsCreating: (isCreating) => set({ isCreating }),
      setCreateError: (createError) => set({ createError }),

      reset: () => {
        const controller = get().activeGenerateController
        if (controller) {
          controller.abort()
        }
        set({
          ...initialState,
        })
      },
    }),
    {
      name: "ralph-wizard-draft-v1",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        currentStep: state.currentStep,
        projectName: state.projectName,
        projectDescription: state.projectDescription,
        techStack: state.techStack,
        cli: state.cli,
        autoApproval: state.autoApproval,
        maxIterations: state.maxIterations,
        testCommand: state.testCommand,
        modelOverride: state.modelOverride,
        generatedFiles: state.generatedFiles,
      }),
    },
  ),
)
