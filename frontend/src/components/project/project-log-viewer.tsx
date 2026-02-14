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

type LogFilterMode = "all" | "errors"

type AnsiStyle = {
  color: string | null
  bold: boolean
}

type AnsiSegment = {
  text: string
  style: AnsiStyle
}

type ParsedLogLine = {
  raw: string
  segments: AnsiSegment[]
}

const ANSI_ESCAPE = String.fromCharCode(27)
const ANSI_PATTERN = new RegExp(`${ANSI_ESCAPE}\\[([0-9;]*)m`, "g")
const BOTTOM_OFFSET_PX = 20
const LOG_ERROR_PATTERN = /(error|failed|exception|traceback|fatal|❌|⚠)/i
const LOG_VIEWPORT_HEIGHT_PX = 520
const LOG_LINE_HEIGHT_PX = 18
const LOG_OVERSCAN_LINES = 20

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

function stripAnsi(input: string): string {
  return input.replace(ANSI_PATTERN, "")
}

function extractIterationNumber(line: string): number | null {
  const normalized = stripAnsi(line)
  const dashboardMatch = normalized.match(/^\[Iteration\s+(\d+)\]/i)
  if (dashboardMatch) {
    return Number.parseInt(dashboardMatch[1], 10)
  }

  const streamMatch = normalized.match(/===\s*Iteration\s+(\d+)\/\d+\s*===/i)
  if (streamMatch) {
    return Number.parseInt(streamMatch[1], 10)
  }

  return null
}

function parseIterationBound(rawValue: string): number | null {
  if (rawValue.trim().length === 0) {
    return null
  }
  const value = Number.parseInt(rawValue, 10)
  if (!Number.isFinite(value) || value <= 0) {
    return null
  }
  return value
}

export function ProjectLogViewer({ projectId, liveChunk }: ProjectLogViewerProps) {
  const [logContent, setLogContent] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isAutoScroll, setIsAutoScroll] = useState(true)
  const [isAtBottom, setIsAtBottom] = useState(true)
  const [scrollTop, setScrollTop] = useState(0)
  const [searchTerm, setSearchTerm] = useState("")
  const [filterMode, setFilterMode] = useState<LogFilterMode>("all")
  const [iterationFrom, setIterationFrom] = useState("")
  const [iterationTo, setIterationTo] = useState("")
  const viewportRef = useRef<HTMLDivElement | null>(null)
  const searchInputRef = useRef<HTMLInputElement | null>(null)
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
    setScrollTop(viewport.scrollTop)
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
        setScrollTop(0)
        setSearchTerm("")
        setFilterMode("all")
        setIterationFrom("")
        setIterationTo("")
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
    if (!projectId) {
      return
    }

    const handleFindShortcut = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey)) {
        return
      }
      if (event.key.toLowerCase() !== "f") {
        return
      }
      event.preventDefault()
      searchInputRef.current?.focus()
      searchInputRef.current?.select()
    }

    window.addEventListener("keydown", handleFindShortcut)
    return () => {
      window.removeEventListener("keydown", handleFindShortcut)
    }
  }, [projectId])

  const normalizedSearchTerm = searchTerm.trim().toLowerCase()
  const parsedFrom = parseIterationBound(iterationFrom)
  const parsedTo = parseIterationBound(iterationTo)
  const hasIterationRange = parsedFrom !== null || parsedTo !== null
  const hasInvalidRange = parsedFrom !== null && parsedTo !== null && parsedFrom > parsedTo
  const hasActiveFilters = normalizedSearchTerm.length > 0 || filterMode !== "all" || hasIterationRange

  const filteredLogContent = useMemo(() => {
    if (logContent.length === 0 || hasInvalidRange) {
      return ""
    }

    const lines = logContent.split(/\r?\n/)
    const filteredLines: string[] = []
    let currentIteration: number | null = null

    for (const line of lines) {
      const parsedIteration = extractIterationNumber(line)
      if (parsedIteration !== null) {
        currentIteration = parsedIteration
      }

      if (hasIterationRange) {
        if (currentIteration === null) {
          continue
        }
        if (parsedFrom !== null && currentIteration < parsedFrom) {
          continue
        }
        if (parsedTo !== null && currentIteration > parsedTo) {
          continue
        }
      }

      const normalizedLine = stripAnsi(line).toLowerCase()
      if (filterMode === "errors" && !LOG_ERROR_PATTERN.test(normalizedLine)) {
        continue
      }
      if (normalizedSearchTerm.length > 0 && !normalizedLine.includes(normalizedSearchTerm)) {
        continue
      }

      filteredLines.push(line)
    }

    return filteredLines.join("\n")
  }, [filterMode, hasInvalidRange, hasIterationRange, logContent, normalizedSearchTerm, parsedFrom, parsedTo])

  const parsedLogLines = useMemo<ParsedLogLine[]>(() => {
    if (filteredLogContent.length === 0) {
      return []
    }
    return filteredLogContent.split(/\r?\n/).map((raw) => ({
      raw,
      segments: parseAnsiText(raw),
    }))
  }, [filteredLogContent])

  const virtualizedWindow = useMemo(() => {
    const totalLines = parsedLogLines.length
    if (totalLines === 0) {
      return {
        startIndex: 0,
        endIndex: 0,
        offsetY: 0,
        totalHeight: 0,
      }
    }

    const visibleLineCount = Math.max(1, Math.ceil(LOG_VIEWPORT_HEIGHT_PX / LOG_LINE_HEIGHT_PX))
    const baseStart = Math.floor(scrollTop / LOG_LINE_HEIGHT_PX)
    const unclampedStart = Math.max(0, baseStart - LOG_OVERSCAN_LINES)
    const maxStartIndex = Math.max(0, totalLines - visibleLineCount)
    const startIndex = Math.min(unclampedStart, maxStartIndex)
    const endIndex = Math.min(totalLines, startIndex + visibleLineCount + LOG_OVERSCAN_LINES * 2)

    return {
      startIndex,
      endIndex,
      offsetY: startIndex * LOG_LINE_HEIGHT_PX,
      totalHeight: totalLines * LOG_LINE_HEIGHT_PX,
    }
  }, [parsedLogLines.length, scrollTop])

  const visibleLines = useMemo(
    () => parsedLogLines.slice(virtualizedWindow.startIndex, virtualizedWindow.endIndex),
    [parsedLogLines, virtualizedWindow.endIndex, virtualizedWindow.startIndex],
  )

  useEffect(() => {
    if (!isAutoScroll) {
      return
    }
    scrollToBottom()
  }, [filteredLogContent, isAutoScroll, scrollToBottom])

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

      <div className="mb-3 grid grid-cols-1 gap-2 lg:grid-cols-[minmax(0,1fr)_11rem_6.5rem_6.5rem]">
        <input
          ref={searchInputRef}
          type="text"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="Search logs (Ctrl/Cmd+F)..."
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
        <select
          value={filterMode}
          onChange={(event) => setFilterMode(event.target.value as LogFilterMode)}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          aria-label="Log filter mode"
        >
          <option value="all">All lines</option>
          <option value="errors">Errors only</option>
        </select>
        <input
          type="number"
          min={1}
          inputMode="numeric"
          value={iterationFrom}
          onChange={(event) => setIterationFrom(event.target.value)}
          placeholder="Iter from"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
        <input
          type="number"
          min={1}
          inputMode="numeric"
          value={iterationTo}
          onChange={(event) => setIterationTo(event.target.value)}
          placeholder="Iter to"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
      </div>
      {hasInvalidRange ? (
        <p className="mb-3 text-xs text-rose-600 dark:text-rose-400">
          Iteration range is invalid: start must be {"<="} end.
        </p>
      ) : null}

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
          ) : filteredLogContent.length === 0 ? (
            <p className="text-zinc-400">
              {logContent.length === 0
                ? "No log output yet."
                : hasActiveFilters
                  ? "No log lines match the current search/filter."
                  : "No log output yet."}
            </p>
          ) : (
            <div className="relative min-w-full" style={{ height: `${virtualizedWindow.totalHeight}px` }}>
              <div
                className="absolute inset-x-0 top-0"
                style={{ transform: `translateY(${virtualizedWindow.offsetY}px)` }}
              >
                {visibleLines.map((line, lineOffset) => {
                  const lineIndex = virtualizedWindow.startIndex + lineOffset
                  return (
                    <div
                      key={lineIndex}
                      className="whitespace-pre"
                      style={{ height: `${LOG_LINE_HEIGHT_PX}px`, lineHeight: `${LOG_LINE_HEIGHT_PX}px` }}
                    >
                      {line.raw.length === 0 ? (
                        <span className="text-zinc-100">&nbsp;</span>
                      ) : (
                        line.segments.map((segment, segmentIndex) => (
                          <span key={segmentIndex} className={styleToClass(segment.style)}>
                            {segment.text}
                          </span>
                        ))
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {!isAutoScroll && !isAtBottom && !isLoading && !error && parsedLogLines.length > 0 ? (
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
