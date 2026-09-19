import { Editor, loader } from "@monaco-editor/react"
import * as monaco from "monaco-editor/editor/editor.api"
import EditorWorker from "monaco-editor/editor/editor.worker?worker"
import "monaco-editor/languages/definitions/markdown/register"

// Serve the editor and its worker with the app, including offline deployments.
self.MonacoEnvironment = { getWorker: () => new EditorWorker() }
loader.config({ monaco })
export { Editor }
