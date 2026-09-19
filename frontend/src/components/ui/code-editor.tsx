import { lazy, Suspense } from "react"
import type { EditorProps } from "@monaco-editor/react"
const MonacoEditor = lazy(() => import("./monaco-editor").then((module) => ({ default: module.Editor })))
export function Editor(props: EditorProps) {
  return <Suspense fallback={<div role="status" style={{ height: props.height }} className="p-4 text-sm text-muted-foreground">Loading editor…</div>}><MonacoEditor {...props} /></Suspense>
}
