import { useCallback, useEffect, useState } from "react"
import { Archive, ArchiveRestore, Settings2 } from "lucide-react"

import {
  type ArchiveSettings,
  fetchArchiveSettings,
  fetchArchivedProjects,
  unarchiveProject,
  updateArchiveSettings,
} from "@/api/archive"
import { Button } from "@/components/ui/button"
import { useToastStore } from "@/stores/toast-store"
import type { ProjectSummary, ProjectStatus } from "@/types/project"

const statusLabel: Record<ProjectStatus, string> = {
  running: "Running",
  paused: "Paused",
  stopped: "Stopped",
  complete: "Complete",
  error: "Error",
}

const statusClassName: Record<ProjectStatus, string> = {
  running: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  paused: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  stopped: "bg-slate-500/15 text-slate-700 dark:text-slate-300",
  complete: "bg-teal-500/15 text-teal-700 dark:text-teal-300",
  error: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
}

export function ArchivePage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [settings, setSettings] = useState<ArchiveSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [unarchiving, setUnarchiving] = useState<string | null>(null)
  const pushToast = useToastStore((state) => state.pushToast)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [archivedProjects, archiveSettings] = await Promise.all([
        fetchArchivedProjects(),
        fetchArchiveSettings(),
      ])
      setProjects(archivedProjects)
      setSettings(archiveSettings)
    } catch {
      pushToast({ title: "Failed to load archive data", tone: "error" })
    } finally {
      setIsLoading(false)
    }
  }, [pushToast])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleUnarchive = async (projectId: string, projectName: string) => {
    setUnarchiving(projectId)
    try {
      await unarchiveProject(projectId)
      setProjects((prev) => prev.filter((p) => p.id !== projectId))
      pushToast({
        title: "Project unarchived",
        description: projectName,
        tone: "success",
      })
    } catch {
      pushToast({ title: "Failed to unarchive project", tone: "error" })
    } finally {
      setUnarchiving(null)
    }
  }

  const handleSaveSettings = async (updated: ArchiveSettings) => {
    try {
      const saved = await updateArchiveSettings(updated)
      setSettings(saved)
      pushToast({ title: "Archive settings saved", tone: "success" })
      setSettingsOpen(false)
    } catch {
      pushToast({ title: "Failed to save settings", tone: "error" })
    }
  }

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <Archive className="h-6 w-6" />
            Archive
          </h1>
          <p className="text-sm text-muted-foreground">
            Archived projects are hidden from the dashboard. Unarchive to restore.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSettingsOpen(!settingsOpen)}
          className="gap-1.5"
        >
          <Settings2 className="h-4 w-4" />
          Settings
        </Button>
      </header>

      {settingsOpen && settings && (
        <ArchiveSettingsPanel settings={settings} onSave={handleSaveSettings} />
      )}

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={`skel-${i}`} className="h-16 animate-pulse rounded-xl border bg-card/50" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="rounded-xl border border-dashed bg-card/40 p-10 text-center">
          <Archive className="mx-auto h-10 w-10 text-muted-foreground/40" />
          <h2 className="mt-3 text-lg font-semibold">No archived projects</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Archived projects will appear here. You can archive projects from the dashboard.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {projects.map((project) => (
            <article
              key={project.id}
              className="flex items-center justify-between gap-3 rounded-xl border bg-card p-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="truncate text-sm font-semibold">{project.name}</h3>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${statusClassName[project.status]}`}
                  >
                    {statusLabel[project.status]}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">{project.path}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="shrink-0 gap-1.5"
                disabled={unarchiving === project.id}
                onClick={() => handleUnarchive(project.id, project.name)}
              >
                <ArchiveRestore className="h-4 w-4" />
                {unarchiving === project.id ? "Restoring..." : "Unarchive"}
              </Button>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

function ArchiveSettingsPanel({
  settings,
  onSave,
}: {
  settings: ArchiveSettings
  onSave: (s: ArchiveSettings) => void
}) {
  const [enabled, setEnabled] = useState(settings.auto_archive_enabled)
  const [days, setDays] = useState(settings.auto_archive_after_days)

  return (
    <div className="rounded-xl border bg-card/80 p-4">
      <h3 className="text-sm font-semibold">Auto-Archive Settings</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Automatically archive projects that have had no activity for a configurable number of days.
      </p>

      <div className="mt-4 space-y-3">
        <label className="flex items-center gap-3 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4 rounded border-input accent-primary"
          />
          Enable auto-archiving
        </label>

        <label className="block text-sm">
          <span className="text-muted-foreground">Archive after inactive for</span>
          <div className="mt-1 flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={365}
              value={days}
              onChange={(e) => setDays(Math.max(1, parseInt(e.target.value) || 1))}
              disabled={!enabled}
              className="w-20 rounded-md border border-input bg-background px-2 py-1.5 text-sm disabled:opacity-50"
            />
            <span className="text-sm text-muted-foreground">days</span>
          </div>
        </label>

        <Button
          size="sm"
          onClick={() => onSave({ auto_archive_enabled: enabled, auto_archive_after_days: days })}
        >
          Save Settings
        </Button>
      </div>
    </div>
  )
}
