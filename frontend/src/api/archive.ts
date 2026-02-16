import { apiFetch } from "@/api/client"
import type { ProjectSummary } from "@/types/project"

export type ArchiveSettings = {
  auto_archive_enabled: boolean
  auto_archive_after_days: number
}

export async function fetchArchivedProjects(): Promise<ProjectSummary[]> {
  return apiFetch<ProjectSummary[]>("/projects/archived")
}

export async function archiveProject(projectId: string): Promise<void> {
  await apiFetch(`/projects/${projectId}/archive`, { method: "POST" })
}

export async function unarchiveProject(projectId: string): Promise<void> {
  await apiFetch(`/projects/${projectId}/unarchive`, { method: "POST" })
}

export async function fetchArchiveSettings(): Promise<ArchiveSettings> {
  return apiFetch<ArchiveSettings>("/projects/archive/settings")
}

export async function updateArchiveSettings(
  settings: Partial<ArchiveSettings>,
): Promise<ArchiveSettings> {
  return apiFetch<ArchiveSettings>("/projects/archive/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  })
}
