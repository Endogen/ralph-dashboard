import type { NotificationEntry, ProjectStatus } from "@/types/project"

type ProjectEvent<Type extends string, Data> = Readonly<{
  type: Type
  project: string
  timestamp?: string
  data: Readonly<Data>
}>

type NotificationData = Omit<NotificationEntry, "timestamp">

type ServerEvent =
  | ProjectEvent<"status_changed", { status: ProjectStatus }>
  | ProjectEvent<"log_append", { lines: string; offset: number }>
  | ProjectEvent<"notification", NotificationData>
  | ProjectEvent<"iteration_started" | "iteration_completed" | "plan_updated" | "file_changed", Record<string, unknown>>
  | Readonly<{ type: "watcher_projects_refreshed"; project?: never; timestamp?: string; data: Readonly<Record<string, unknown>> }>

export type LiveEvent = ServerEvent | Readonly<{ type: "reconnected"; project?: never }>
export type LiveEventListener = (event: LiveEvent) => void

const statuses: Record<ProjectStatus, true> = {
  running: true, paused: true, stopped: true, complete: true, error: true,
}
function isProjectStatus(value: unknown): value is ProjectStatus {
  return typeof value === "string" && Object.hasOwn(statuses, value)
}
const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value)
const isNullableString = (value: unknown): value is string | null => value === null || typeof value === "string"

/** Validate consumed payloads once, before untrusted JSON reaches subscribers. */
export function parseSocketMessage(raw: string): ServerEvent | { type: "authenticated" } | null {
  let value: unknown
  try { value = JSON.parse(raw) } catch { return null }
  if (!isRecord(value)) return null
  if (value.type === "authenticated") return { type: "authenticated" }
  if (value.timestamp !== undefined && typeof value.timestamp !== "string") return null
  const { data } = value
  if (!isRecord(data)) return null
  const timestamp = value.timestamp
  if (value.type === "watcher_projects_refreshed") {
    return { type: value.type, timestamp, data }
  }
  if (typeof value.project !== "string" || !value.project.trim()) return null
  const metadata = { project: value.project, timestamp }
  switch (value.type) {
    case "status_changed":
      if (!isProjectStatus(data.status)) return null
      return { type: value.type, ...metadata, data: { status: data.status } }
    case "log_append":
      if (typeof data.lines !== "string" || typeof data.offset !== "number" || !Number.isSafeInteger(data.offset) || data.offset < 0) return null
      return { type: value.type, ...metadata, data: { lines: data.lines, offset: data.offset } }
    case "notification":
      if (typeof data.event_id !== "string" || typeof data.kind !== "string" ||
          typeof data.severity !== "string" || typeof data.message !== "string" ||
          typeof data.active !== "boolean" || !isNullableString(data.prefix) ||
          !isNullableString(data.details) || !isNullableString(data.status) ||
          !isNullableString(data.source) ||
          !(data.iteration === null || (typeof data.iteration === "number" && Number.isSafeInteger(data.iteration)))) return null
      return { type: value.type, ...metadata, data: {
        event_id: data.event_id, kind: data.kind, severity: data.severity, message: data.message,
        active: data.active, prefix: data.prefix, details: data.details, status: data.status,
        source: data.source, iteration: data.iteration,
      } }
    case "iteration_started":
    case "iteration_completed":
    case "plan_updated":
    case "file_changed":
      return { type: value.type, ...metadata, data }
    default:
      // Protocol replies and unknown future events have no application effects.
      return null
  }
}

/** Ephemeral fan-out: no event replay, React state, or DOM-global event names. */
export function createLiveEventChannel() {
  const listeners = new Set<LiveEventListener>()
  return {
    subscribe(listener: LiveEventListener) {
      // Each subscription owns its cleanup, even for the same callback.
      const subscription: LiveEventListener = (event) => listener(event)
      listeners.add(subscription)
      return () => { listeners.delete(subscription) }
    },
    publish(event: LiveEvent) {
      for (const listener of [...listeners]) {
        if (!listeners.has(listener)) continue
        try { listener(event) } catch (error) {
          // One broken view must not prevent updates in other subscribers.
          console.error("Live event subscriber failed", error)
        }
      }
    },
  }
}

export const liveEvents = createLiveEventChannel()
