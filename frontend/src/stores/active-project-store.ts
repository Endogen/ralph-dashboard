import { create } from "zustand"

import { apiFetch } from "@/api/client"
import type { ProjectDetail } from "@/types/project"

type ActiveProjectState = {
  activeProjectId: string | null
  activeProject: ProjectDetail | null
  isLoading: boolean
  error: string | null
  setActiveProjectId: (projectId: string | null) => void
  fetchActiveProject: (projectId?: string | null) => Promise<void>
  patchActiveProject: (projectId: string, patch: Partial<ProjectDetail>) => void
  clearActiveProject: () => void
}

export const useActiveProjectStore = create<ActiveProjectState>((set, get) => ({
  activeProjectId: null,
  activeProject: null,
  isLoading: false,
  error: null,

  setActiveProjectId: (projectId: string | null) => set({ activeProjectId: projectId }),

  fetchActiveProject: async (projectId?: string | null) => {
    const resolvedProjectId = projectId ?? get().activeProjectId
    if (!resolvedProjectId) {
      set({ activeProject: null, activeProjectId: null, error: null })
      return
    }

    set({ activeProjectId: resolvedProjectId, isLoading: true, error: null })
    try {
      const project = await apiFetch<ProjectDetail>(`/projects/${resolvedProjectId}`)
      set({
        activeProject: project,
        activeProjectId: resolvedProjectId,
        isLoading: false,
        error: null,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load active project"
      set({ activeProject: null, isLoading: false, error: message })
    }
  },

  patchActiveProject: (projectId: string, patch: Partial<ProjectDetail>) =>
    set((state) => {
      if (!state.activeProject || state.activeProject.id !== projectId) {
        return state
      }
      return { activeProject: { ...state.activeProject, ...patch } }
    }),

  clearActiveProject: () =>
    set({
      activeProjectId: null,
      activeProject: null,
      isLoading: false,
      error: null,
    }),
}))
