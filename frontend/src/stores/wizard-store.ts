import { create } from "zustand"

export type AgentChoice = "codex" | "claude-code"
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
  cli: "claude-code" as AgentChoice,
  autoApproval: "sandboxed" as ApprovalMode,
  maxIterations: 20,
  testCommand: "",
  modelOverride: "",
  generatedFiles: [] as GeneratedFile[],
  isGenerating: false,
  generateError: null as string | null,
  isCreating: false,
  createError: null as string | null,
}

export const useWizardStore = create<WizardState>((set) => ({
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

  setIsCreating: (isCreating) => set({ isCreating }),
  setCreateError: (createError) => set({ createError }),

  reset: () => set(initialState),
}))
