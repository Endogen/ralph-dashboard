import { memo } from "react"

import { ansiStyleToClass, parseAnsiText } from "@/lib/ansi"

type AnsiTextBlockProps = {
  text: string
}

/**
 * Renders a multi-line text block with ANSI colors as styled spans.
 * Meant to be placed inside a `whitespace-pre-wrap` container — newlines
 * inside segments are preserved as-is.
 */
export const AnsiTextBlock = memo(function AnsiTextBlock({ text }: AnsiTextBlockProps) {
  return (
    <>
      {parseAnsiText(text).map((segment, index) => (
        <span key={index} className={ansiStyleToClass(segment.style)}>
          {segment.text}
        </span>
      ))}
    </>
  )
})
