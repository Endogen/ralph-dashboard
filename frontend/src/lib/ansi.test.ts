import { describe, expect, it } from "vitest"

import { ansiStyleToClass, parseAnsiText, stripAnsi } from "@/lib/ansi"

const ESC = String.fromCharCode(27)

describe("parseAnsiText", () => {
  it("returns a single unstyled segment for plain text", () => {
    expect(parseAnsiText("hello world")).toEqual([
      { text: "hello world", style: { color: null, bold: false } },
    ])
  })

  it("splits colored and reset segments", () => {
    const segments = parseAnsiText(`${ESC}[0;32mok${ESC}[0m done`)
    expect(segments).toEqual([
      { text: "ok", style: { color: "32", bold: false } },
      { text: " done", style: { color: null, bold: false } },
    ])
  })

  it("carries color across newlines and applies bold", () => {
    const segments = parseAnsiText(`${ESC}[1;31mline one\nline two${ESC}[0m`)
    expect(segments).toEqual([
      { text: "line one\nline two", style: { color: "31", bold: true } },
    ])
  })

  it("treats a bare escape as a full reset", () => {
    const segments = parseAnsiText(`${ESC}[33mwarn${ESC}[mrest`)
    expect(segments).toEqual([
      { text: "warn", style: { color: "33", bold: false } },
      { text: "rest", style: { color: null, bold: false } },
    ])
  })

  it("ignores unsupported codes while keeping known ones", () => {
    const segments = parseAnsiText(`${ESC}[4;36munderlined cyan${ESC}[0m`)
    expect(segments).toEqual([
      { text: "underlined cyan", style: { color: "36", bold: false } },
    ])
  })
})

describe("stripAnsi", () => {
  it("removes escape sequences and keeps text", () => {
    expect(stripAnsi(`${ESC}[0;31mERROR${ESC}[0m: failed`)).toBe("ERROR: failed")
  })

  it("leaves plain text untouched", () => {
    expect(stripAnsi("no colors here")).toBe("no colors here")
  })
})

describe("ansiStyleToClass", () => {
  it("maps colors and bold to tailwind classes", () => {
    expect(ansiStyleToClass({ color: "31", bold: true })).toBe(
      "text-zinc-100 text-rose-300 font-semibold",
    )
  })

  it("falls back to the base class for unknown colors", () => {
    expect(ansiStyleToClass({ color: "99", bold: false })).toBe("text-zinc-100")
  })
})
