import { useState } from "react"

import { Button } from "@/components/ui/button"
import { displayTokens } from "@/lib/utils"
import type { ProjectStatus } from "@/types/project"

type ProjectControlBarProps = {
  pauseRequested?: boolean
  status: ProjectStatus
  iterationLabel: string
  runtimeLabel: string
  tokensUsed: number
  onStart?: () => void | Promise<void>
  onStop?: () => void | Promise<void>
  onPause?: () => void | Promise<void>
  onResume?: () => void | Promise<void>
  onInject?: (message: string) => Promise<void>
}

export function ProjectControlBar({
  status,
  pauseRequested = false,
  iterationLabel,
  runtimeLabel,
  tokensUsed,
  onStart,
  onStop,
  onPause,
  onResume,
  onInject,
}: ProjectControlBarProps) {
  const [injectText, setInjectText] = useState("")
  const paused = status === "paused" || pauseRequested

  const [busy, setBusy] = useState(false)
  const running = status === "running" || status === "paused"
  const runAction = async (action?: () => void | Promise<void>) => {
    if (busy || !action) return
    setBusy(true)
    try { await action() } finally { setBusy(false) }
  }
  const handleInject = async () => {
    const trimmed = injectText.trim()
    if (!trimmed) return
    setBusy(true)
    try { await onInject?.(trimmed); setInjectText("") } catch { /* Parent displays the error. */ } finally { setBusy(false) }
  }

  return (
    <section className="sticky bottom-4 z-10 max-w-full overflow-hidden rounded-xl border bg-background/95 p-4 shadow-sm backdrop-blur">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Button className="bg-emerald-600 text-white hover:bg-emerald-700" disabled={running || busy} onClick={() => void runAction(onStart)}>
            Start
          </Button>
          <Button
            className={paused ? "bg-emerald-600 text-white hover:bg-emerald-700" : "bg-amber-600 text-white hover:bg-amber-700"}
            disabled={!running || busy} title="Pause after the current iteration finishes" onClick={() => void runAction(paused ? onResume : onPause)}
          >
            {status === "paused" ? "Resume" : pauseRequested ? "Cancel pause" : "Pause"}
          </Button>
          <Button className="bg-rose-600 text-white hover:bg-rose-700" disabled={!running || busy} onClick={() => void runAction(onStop)}>
            Stop
          </Button>
        </div>

        <div className="flex min-w-0 flex-1 gap-2">
          <input
            className="min-w-0 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
            aria-label="Instructions for next iteration"
            placeholder="Inject instructions for next iteration..."
            value={injectText}
            onChange={(event) => setInjectText(event.target.value)}
          />
          <Button variant="outline" disabled={busy || !injectText.trim()} onClick={handleInject}>
            Inject
          </Button>
        </div>
      </div>

      <p className="mt-3 text-xs text-muted-foreground">
        {iterationLabel} - {runtimeLabel} - {displayTokens(tokensUsed).toLocaleString("en-US")} tokens
      </p>
    </section>
  )
}
