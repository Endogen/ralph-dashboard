import { create } from "zustand"

import { apiFetch } from "@/api/client"
import type { ProjectSummary } from "@/types/project"

type ProjectsState = {
  projects: ProjectSummary[]
  isLoading: boolean
  error: string | null
  fetchProjects: () => Promise<void>
  setProjects: (projects: ProjectSummary[]) => void
  patchProject: (projectId: string, patch: Partial<ProjectSummary>) => void
  upsertProject: (project: ProjectSummary) => void
  removeProject: (projectId: string) => void
}

export const useProjectsStore = create<ProjectsState>((set) => ({
  projects: [],
  isLoading: false,
  error: null,

  fetchProjects: async () => {
    set({ isLoading: true, error: null })
    try {
      const projects = await apiFetch<ProjectSummary[]>("/projects")
      set({ projects, isLoading: false, error: null })
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load projects"
      set({ isLoading: false, error: message })
    }
  },

  setProjects: (projects: ProjectSummary[]) => set({ projects }),

  patchProject: (projectId: string, patch: Partial<ProjectSummary>) =>
    set((state) => {
      const project = state.projects.find((item) => item.id === projectId)
      if (!project || Object.entries(patch).every(([key, value]) => Object.is(project[key as keyof ProjectSummary], value))) {
        return state
      }
      return { projects: state.projects.map((item) => item === project ? { ...item, ...patch } : item) }
    }),

  upsertProject: (project: ProjectSummary) =>
    set((state) => {
      const index = state.projects.findIndex((item) => item.id === project.id)
      if (index === -1) {
        return { projects: [...state.projects, project] }
      }
      const next = [...state.projects]
      next[index] = project
      return { projects: next }
    }),

  removeProject: (projectId: string) =>
    set((state) => ({
      projects: state.projects.filter((project) => project.id !== projectId),
    })),
}))
