import { useState } from "react"

import { Button } from "@/components/ui/button"
import { displayTokens } from "@/lib/utils"
import type { ProjectStatus } from "@/types/project"

type ProjectControlBarProps = {
  status: ProjectStatus
  iterationLabel: string
  runtimeLabel: string
  tokensUsed: number
  onStart?: () => void
  onStop?: () => void
  onPause?: () => void
  onResume?: () => void
  onInject?: (message: string) => void
}

export function ProjectControlBar({
  status,
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
  const paused = status === "paused"

  const handleInject = () => {
    const trimmed = injectText.trim()
    if (!trimmed) return
    onInject?.(trimmed)
    setInjectText("")
  }

  return (
    <section className="sticky bottom-4 z-10 max-w-full overflow-hidden rounded-xl border bg-background/95 p-4 shadow-sm backdrop-blur">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Button className="bg-emerald-600 text-white hover:bg-emerald-700" onClick={onStart}>
            Start
          </Button>
          <Button
            className={paused ? "bg-emerald-600 text-white hover:bg-emerald-700" : "bg-amber-600 text-white hover:bg-amber-700"}
            onClick={paused ? onResume : onPause}
          >
            {paused ? "Resume" : "Pause"}
          </Button>
          <Button className="bg-rose-600 text-white hover:bg-rose-700" onClick={onStop}>
            Stop
          </Button>
        </div>

        <div className="flex min-w-0 flex-1 gap-2">
          <input
            className="min-w-0 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
            placeholder="Inject instructions for next iteration..."
            value={injectText}
            onChange={(event) => setInjectText(event.target.value)}
          />
          <Button variant="outline" onClick={handleInject}>
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
