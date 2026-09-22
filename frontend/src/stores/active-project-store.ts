import { create } from "zustand"

import { apiFetch } from "@/api/client"
import type { ProjectDetail } from "@/types/project"

type ActiveProjectState = {
  activeProjectId: string | null
  activeProject: ProjectDetail | null
  isLoading: boolean
  error: string | null
  fetchActiveProject: (projectId?: string | null) => Promise<void>
  patchActiveProject: (projectId: string, patch: Partial<ProjectDetail>) => void
  clearActiveProject: () => void
}

let requestVersion = 0

export const useActiveProjectStore = create<ActiveProjectState>((set, get) => ({
  activeProjectId: null,
  activeProject: null,
  isLoading: false,
  error: null,

  fetchActiveProject: async (projectId?: string | null) => {
    const version = ++requestVersion
    const resolvedProjectId = projectId ?? get().activeProjectId
    if (!resolvedProjectId) {
      set({ activeProject: null, activeProjectId: null, isLoading: false, error: null })
      return
    }

    set((state) => ({
      activeProjectId: resolvedProjectId,
      activeProject: state.activeProject?.id === resolvedProjectId ? state.activeProject : null,
      isLoading: true,
      error: null,
    }))
    try {
      const project = await apiFetch<ProjectDetail>(`/projects/${resolvedProjectId}`)
      if (version !== requestVersion) return
      set({
        activeProject: project,
        activeProjectId: resolvedProjectId,
        isLoading: false,
        error: null,
      })
    } catch (error) {
      if (version !== requestVersion) return
      const message = error instanceof Error ? error.message : "Failed to load active project"
      set({ activeProject: null, isLoading: false, error: message })
    }
  },

  patchActiveProject: (projectId: string, patch: Partial<ProjectDetail>) =>
    set((state) => {
      if (!state.activeProject || state.activeProject.id !== projectId) {
        return state
      }
      const project = state.activeProject
      if (Object.entries(patch).every(([key, value]) => Object.is(project[key as keyof ProjectDetail], value))) {
        return state
      }
      return { activeProject: { ...project, ...patch } }
    }),

  clearActiveProject: () => {
    requestVersion += 1
    set({
      activeProjectId: null,
      activeProject: null,
      isLoading: false,
      error: null,
    })
  },
}))
