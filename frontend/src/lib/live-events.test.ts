import { describe, expect, it, vi } from "vitest"
import { createLiveEventChannel, parseSocketMessage, type LiveEvent } from "./live-events"

const notification = {
  event_id: "event-1", prefix: "ERROR", kind: "error", severity: "error", active: true,
  message: "Failed", iteration: 1, details: null, status: "error", source: "runner",
}

describe("socket boundary", () => {
  it.each([
    { type: "authenticated" },
    { type: "status_changed", project: "a", data: { status: "running" } },
    { type: "log_append", project: "a", data: { lines: "hello\n", offset: 6 } },
    { type: "notification", project: "a", data: notification },
    ...["iteration_started", "iteration_completed", "plan_updated", "file_changed"].map(type => ({ type, project: "a", data: {} })),
    { type: "watcher_projects_refreshed", data: { count: 1 } },
  ])("accepts supported event $type", (event) => {
    expect(parseSocketMessage(JSON.stringify(event))).toEqual(event)
  })

  it.each([
    "broken json", "null", "[]", "1",
    ...[
      {}, { type: "reconnected" }, { type: "unknown", project: "a", data: {} },
      { type: "status_changed", data: { status: "running" } },
      { type: "status_changed", project: "a", data: { status: "invented" } },
      { type: "log_append", project: "a", data: { lines: 42, offset: 0 } },
      { type: "log_append", project: "a", data: { lines: "x", offset: -1 } },
      { type: "log_append", project: "a", data: { lines: "x", offset: 1 }, timestamp: {} },
      { type: "notification", project: "a", data: { ...notification, message: null } },
      { type: "notification", project: "a", data: { ...notification, active: "yes" } },
    ].map(event => JSON.stringify(event)),
  ])("ignores malformed or unsupported input %s", (raw) => {
    expect(parseSocketMessage(raw)).toBeNull()
  })
})

describe("live subscriptions", () => {
  it("delivers once per subscriber, isolates failures and honors independent cleanup", () => {
    const channel = createLiveEventChannel()
    const report = vi.spyOn(console, "error").mockImplementation(() => {})
    const stopBroken = channel.subscribe(() => { throw new Error("broken view") })
    const receive = vi.fn()
    const stopFirst = channel.subscribe(receive)
    const stopSecond = channel.subscribe(receive)
    const event: LiveEvent = { type: "reconnected" }
    channel.publish(event)
    expect(receive).toHaveBeenCalledTimes(2)
    expect(report).toHaveBeenCalledOnce()
    stopBroken()
    stopFirst()
    stopFirst()
    channel.publish(event)
    expect(receive).toHaveBeenCalledTimes(3)
    stopSecond()
    channel.publish(event)
    expect(receive).toHaveBeenCalledTimes(3)
    report.mockRestore()
  })
})
