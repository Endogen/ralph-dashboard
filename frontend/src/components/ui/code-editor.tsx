import { lazy, Suspense } from "react"
import type { CSSProperties } from "react"

// Compatibility surface restricted to the options the dashboard actually uses.
export type EditorProps = {
  height?: CSSProperties["height"]
  value?: string
  onChange?: (value: string) => void
  defaultLanguage?: "markdown"
  theme?: "vs-dark"
  options?: {
    ariaLabel?: string
    minimap?: { enabled: boolean }
    fontSize?: number
    wordWrap?: "on" | "off"
    scrollBeyondLastLine?: boolean
    automaticLayout?: boolean
  }
}
const MarkdownEditor = lazy(() => import("./markdown-editor").then((module) => ({ default: module.Editor })))
export function Editor(props: EditorProps) {
  return <Suspense fallback={<div role="status" style={{ height: props.height }} className="p-4 text-sm text-muted-foreground">Loading editor…</div>}><MarkdownEditor {...props} /></Suspense>
}
