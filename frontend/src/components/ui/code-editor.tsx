import { lazy, Suspense } from "react"
import type { CSSProperties } from "react"

export type EditorProps = {
  documentId: string
  value: string
  onChange: (value: string) => void
  ariaLabel: string
  height?: CSSProperties["height"]
  onSave?: () => void
  saveDisabled?: boolean
}

const MarkdownEditor = lazy(() => import("./markdown-editor").then((module) => ({ default: module.Editor })))

export function Editor(props: EditorProps) {
  return (
    <Suspense fallback={<div role="status" style={{ height: props.height ?? "100%" }} className="p-4 text-sm text-muted-foreground">Loading editor…</div>}>
      <MarkdownEditor {...props} />
    </Suspense>
  )
}
