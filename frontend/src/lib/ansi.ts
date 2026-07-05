export type AnsiStyle = {
  color: string | null
  bold: boolean
}

export type AnsiSegment = {
  text: string
  style: AnsiStyle
}

const ANSI_ESCAPE = String.fromCharCode(27)
const ANSI_PATTERN = new RegExp(`${ANSI_ESCAPE}\\[([0-9;]*)m`, "g")

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

export function parseAnsiText(input: string): AnsiSegment[] {
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

export function stripAnsi(input: string): string {
  return input.replace(ANSI_PATTERN, "")
}

export function ansiStyleToClass(style: AnsiStyle): string {
  const classes = ["text-zinc-100"]
  if (style.color && ANSI_COLOR_CLASS[style.color]) {
    classes.push(ANSI_COLOR_CLASS[style.color])
  }
  if (style.bold) {
    classes.push("font-semibold")
  }
  return classes.join(" ")
}
