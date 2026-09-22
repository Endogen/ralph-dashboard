import { useEffect, useLayoutEffect, useRef } from "react"
import { EditorState, type Extension } from "@codemirror/state"
import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection, rectangularSelection } from "@codemirror/view"
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands"
import { bracketMatching, foldGutter, foldKeymap, indentOnInput, syntaxHighlighting } from "@codemirror/language"
import { markdown, markdownKeymap } from "@codemirror/lang-markdown"
import { search, searchKeymap, highlightSelectionMatches, openSearchPanel } from "@codemirror/search"
import { closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete"
import { FileText, Search } from "lucide-react"
import { editorTheme, editorHighlighting } from "./editor-theme"
import type { EditorProps } from "./code-editor"

export function Editor(props: EditorProps) {
  // Equal text can still belong to a different file. Never share its undo stack.
  return <EditorDocument key={props.documentId} {...props} />
}

function EditorDocument({ value, onChange, height = "100%", ariaLabel: label, onSave, saveDisabled }: EditorProps) {
  const host = useRef<HTMLDivElement>(null)
  const view = useRef<EditorView | null>(null)
  const extensions = useRef<Extension[]>([])
  const initialValue = useRef(value)
  const callbacks = useRef({ onChange, onSave, saveDisabled })
  useLayoutEffect(() => { callbacks.current = { onChange, onSave, saveDisabled } }, [onChange, onSave, saveDisabled])

  useEffect(() => {
    extensions.current = [
        EditorState.lineSeparator.of(initialValue.current.includes("\r\n") ? "\r\n" : "\n"),
        lineNumbers(), highlightActiveLineGutter(), highlightActiveLine(),
        history(), drawSelection(), rectangularSelection(), indentOnInput(),
        bracketMatching(), closeBrackets(), foldGutter(),
        markdown(), syntaxHighlighting(editorHighlighting),
        search({ top: true }), highlightSelectionMatches(), editorTheme,
        keymap.of([{ key: "Mod-s", run: () => {
          const current = callbacks.current
          if (!current.onSave) return false
          if (!current.saveDisabled) current.onSave()
          return true
        } }, ...closeBracketsKeymap, ...markdownKeymap, ...defaultKeymap, ...historyKeymap, ...searchKeymap, ...foldKeymap]),
        EditorView.lineWrapping,
        EditorView.contentAttributes.of({ "aria-label": label }),
        EditorView.theme({
          "&": { height: "100%", fontSize: "13px" },
        }),
        EditorView.updateListener.of(update => {
          if (update.docChanged) callbacks.current.onChange(update.state.sliceDoc())
        }),
      ]
    const editor = new EditorView({ parent: host.current!, doc: initialValue.current, extensions: extensions.current })
    view.current = editor
    return () => { initialValue.current = editor.state.sliceDoc(); editor.destroy(); view.current = null }
  }, [label])

  useEffect(() => {
    const editor = view.current
    if (editor && editor.state.sliceDoc() !== value) {
      // External document replacement must not leak undo history between files.
      editor.setState(EditorState.create({ doc: value, extensions: extensions.current }))
    }
  }, [value])

  const lineCount = value.split("\n").length
  return (
    <div style={{ height }} className="flex min-w-0 flex-col overflow-hidden bg-background focus-within:ring-1 focus-within:ring-inset focus-within:ring-primary/30">
      <div className="flex h-9 shrink-0 items-center justify-between border-b bg-muted/30 px-3">
        <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"><FileText className="h-3.5 w-3.5" aria-hidden="true" />Markdown</span>
        <button type="button" onClick={() => { if (view.current) openSearchPanel(view.current) }} title="Find and replace (Ctrl/Cmd+F)" aria-label={`Find in ${label.toLowerCase()}`} className="flex items-center gap-1.5 rounded px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary">
          <Search className="h-3.5 w-3.5" aria-hidden="true" />Find
        </button>
      </div>
      <div ref={host} className="min-h-0 flex-1" />
      <div className="flex h-7 shrink-0 items-center justify-between border-t bg-muted/20 px-3 text-[11px] text-muted-foreground">
        <span>{lineCount.toLocaleString()} {lineCount === 1 ? "line" : "lines"}</span>
        <span>Tab to move focus</span>
      </div>
    </div>
  )
}
