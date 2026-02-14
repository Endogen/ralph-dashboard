import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ArrowDown, Pin, PinOff } from "lucide-react"

import { apiFetch } from "@/api/client"
import { Button } from "@/components/ui/button"
import type { IterationDetail, IterationListResponse } from "@/types/project"

type ProjectLogViewerProps = {
  projectId?: string
  liveChunk?: {
    id: number
    lines: string
  } | null
}

type AnsiStyle = {
  color: string | null
  bold: boolean
}

type AnsiSegment = {
  text: string
  style: AnsiStyle
}

const ANSI_ESCAPE = String.fromCharCode(27)
const ANSI_PATTERN = new RegExp(`${ANSI_ESCAPE}\\[([0-9;]*)m`, "g")
const BOTTOM_OFFSET_PX = 20

const ANSI_COLOR_CLASS: Record<string, string> = {
  "30": "text-zinc-900",
  "31": "text-rose-300",
  "32": "text-emerald-300",
  "33": "text-amber-200",
  "34": "text-sky-300",
  "35": "text-fuchsia-300",
  "36": "text-cyan-300",
  "37": "text-zinc-100",
  "90": "text-zinc-400",
  "91": "text-rose-200",
  "92": "text-emerald-200",
  "93": "text-amber-100",
  "94": "text-sky-200",
  "95": "text-fuchsia-200",
  "96": "text-cyan-200",
  "97": "text-white",
}

function applyAnsiCodes(style: AnsiStyle, rawCodes: string): AnsiStyle {
  const codes = rawCodes.length === 0 ? ["0"] : rawCodes.split(";")
  let nextStyle = style

  for (const code of codes) {
    if (code === "0") {
      nextStyle = { color: null, bold: false }
      continue
    }
    if (code === "1") {
      nextStyle = { ...nextStyle, bold: true }
      continue
    }
    if (ANSI_COLOR_CLASS[code]) {
      nextStyle = { ...nextStyle, color: code }
    }
  }

  return nextStyle
}

function parseAnsiText(input: string): AnsiSegment[] {
  const segments: AnsiSegment[] = []
  let style: AnsiStyle = { color: null, bold: false }
  let cursor = 0

  for (const match of input.matchAll(ANSI_PATTERN)) {
    const matchIndex = match.index ?? 0
    if (matchIndex > cursor) {
      segments.push({
        text: input.slice(cursor, matchIndex),
        style,
      })
    }
    style = applyAnsiCodes(style, match[1] ?? "")
    cursor = matchIndex + match[0].length
  }

  if (cursor < input.length) {
    segments.push({
      text: input.slice(cursor),
      style,
    })
  }

  if (segments.length === 0) {
    return [{ text: input, style: { color: null, bold: false } }]
  }
  return segments
}

function styleToClass(style: AnsiStyle): string {
  const classes = ["text-zinc-100"]
  if (style.color && ANSI_COLOR_CLASS[style.color]) {
    classes.push(ANSI_COLOR_CLASS[style.color])
  }
  if (style.bold) {
    classes.push("font-semibold")
  }
  return classes.join(" ")
}

function appendLogChunk(current: string, chunk: string): string {
  if (!chunk) {
    return current
  }
  if (!current) {
    return chunk
  }
  if (current.endsWith("\n") || chunk.startsWith("\n")) {
    return `${current}${chunk}`
  }
  return `${current}\n${chunk}`
}

export function ProjectLogViewer({ projectId, liveChunk }: ProjectLogViewerProps) {
  const [logContent, setLogContent] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isAutoScroll, setIsAutoScroll] = useState(true)
  const [isAtBottom, setIsAtBottom] = useState(true)
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const pendingLiveChunkRef = useRef("")
  const hydratingRef = useRef(false)

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const viewport = viewportRef.current
    if (!viewport) {
      return
    }
    viewport.scrollTo({ top: viewport.scrollHeight, behavior })
    setIsAtBottom(true)
  }, [])

  const handleScroll = useCallback(() => {
    const viewport = viewportRef.current
    if (!viewport) {
      return
    }
    const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight
    const nextIsAtBottom = distanceFromBottom <= BOTTOM_OFFSET_PX
    setIsAtBottom((current) => (current === nextIsAtBottom ? current : nextIsAtBottom))
  }, [])

  const handleToggleAutoScroll = useCallback(() => {
    setIsAutoScroll((current) => {
      const next = !current
      if (next) {
        window.requestAnimationFrame(() => {
          scrollToBottom("smooth")
        })
      }
      return next
    })
  }, [scrollToBottom])

  useEffect(() => {
    let cancelled = false

    const loadLogs = async () => {
      if (!projectId) {
        setIsAutoScroll(true)
        setIsAtBottom(true)
        pendingLiveChunkRef.current = ""
        hydratingRef.current = false
        setLogContent("")
        setIsLoading(false)
        setError(null)
        return
      }

      hydratingRef.current = true
      setIsLoading(true)
      setError(null)
      try {
        const listResponse = await apiFetch<IterationListResponse>(`/projects/${projectId}/iterations?status=all&limit=500`)
        const ordered = [...listResponse.iterations].sort((left, right) => left.number - right.number)
        const details = await Promise.all(
          ordered.map((iteration) =>
            apiFetch<IterationDetail>(`/projects/${projectId}/iterations/${iteration.number}`),
          ),
        )
        if (cancelled) {
          return
        }

        const merged = details
          .map((detail) => {
            const body = detail.log_output?.trim() || "(no log output captured)"
            return `[Iteration ${detail.number}]\n${body}`
          })
          .join("\n\n")
        const pending = pendingLiveChunkRef.current
        pendingLiveChunkRef.current = ""
        setLogContent(appendLogChunk(merged, pending))
      } catch (loadError) {
        if (cancelled) {
          return
        }
        const message = loadError instanceof Error ? loadError.message : "Failed to load log output"
        setError(message)
      } finally {
        if (!cancelled) {
          hydratingRef.current = false
          setIsLoading(false)
        }
      }
    }

    void loadLogs()

    return () => {
      cancelled = true
    }
  }, [projectId])

  useEffect(() => {
    if (!projectId || !liveChunk || !liveChunk.lines) {
      return
    }

    if (hydratingRef.current) {
      pendingLiveChunkRef.current = appendLogChunk(pendingLiveChunkRef.current, liveChunk.lines)
      return
    }

    setLogContent((current) => appendLogChunk(current, liveChunk.lines))
    setError(null)
  }, [liveChunk, projectId])

  useEffect(() => {
    if (!isAutoScroll) {
      return
    }
    scrollToBottom()
  }, [isAutoScroll, logContent, scrollToBottom])

  const ansiSegments = useMemo(() => parseAnsiText(logContent), [logContent])

  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold">Log Viewer</h3>
          <p className="text-sm text-muted-foreground">Terminal-style log stream with ANSI color rendering.</p>
        </div>
        <Button
          type="button"
          variant={isAutoScroll ? "secondary" : "outline"}
          size="sm"
          onClick={handleToggleAutoScroll}
          aria-pressed={isAutoScroll}
          className="w-fit gap-2"
        >
          {isAutoScroll ? <Pin className="h-3.5 w-3.5" /> : <PinOff className="h-3.5 w-3.5" />}
          {isAutoScroll ? "Following" : "Manual"}
        </Button>
      </header>

      <div className="relative">
        <div
          ref={viewportRef}
          onScroll={handleScroll}
          className="h-[520px] overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs"
        >
          {isLoading ? (
            <p className="text-zinc-400">Loading logs...</p>
          ) : error ? (
            <p className="text-rose-300">{error}</p>
          ) : logContent.length === 0 ? (
            <p className="text-zinc-400">No log output yet.</p>
          ) : (
            <pre className="whitespace-pre-wrap break-words">
              {ansiSegments.map((segment, index) => (
                <span key={index} className={styleToClass(segment.style)}>
                  {segment.text}
                </span>
              ))}
            </pre>
          )}
        </div>

        {!isAutoScroll && !isAtBottom && !isLoading && !error && logContent.length > 0 ? (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => scrollToBottom("smooth")}
            className="absolute bottom-4 right-4 gap-1.5"
          >
            <ArrowDown className="h-3.5 w-3.5" />
            Scroll to bottom
          </Button>
        ) : null}
      </div>
    </section>
  )
}
