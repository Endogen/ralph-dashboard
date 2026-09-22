import { useEffect, useLayoutEffect, useRef } from "react"
import { EditorState, type Extension } from "@codemirror/state"
import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection, rectangularSelection } from "@codemirror/view"
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands"
import { bracketMatching, foldGutter, foldKeymap, indentOnInput, syntaxHighlighting, defaultHighlightStyle } from "@codemirror/language"
import { markdown, markdownKeymap } from "@codemirror/lang-markdown"
import { search, searchKeymap, highlightSelectionMatches } from "@codemirror/search"
import { closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete"
import { oneDark } from "@codemirror/theme-one-dark"
import type { EditorProps } from "./code-editor"

export function Editor({ value = "", onChange, height, options }: EditorProps) {
  const host = useRef<HTMLDivElement>(null)
  const view = useRef<EditorView | null>(null)
  const extensions = useRef<Extension[]>([])
  const initialValue = useRef(value)
  const onChangeRef = useRef(onChange)
  useLayoutEffect(() => { onChangeRef.current = onChange }, [onChange])
  const label = options?.ariaLabel ?? "Markdown editor"
  const fontSize = options?.fontSize ?? 13
  const wrap = options?.wordWrap !== "off"

  useEffect(() => {
    extensions.current = [
        lineNumbers(), highlightActiveLineGutter(), highlightActiveLine(),
        history(), drawSelection(), rectangularSelection(), indentOnInput(),
        bracketMatching(), closeBrackets(), foldGutter(),
        markdown(), syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        search({ top: true }), highlightSelectionMatches(), oneDark,
        keymap.of([...closeBracketsKeymap, ...markdownKeymap, ...defaultKeymap, ...historyKeymap, ...searchKeymap, ...foldKeymap]),
        ...(wrap ? [EditorView.lineWrapping] : []),
        EditorView.contentAttributes.of({ "aria-label": label }),
        EditorView.theme({
          "&": { height: "100%", fontSize: `${fontSize}px` },
          ".cm-scroller": { overflow: "auto", fontFamily: "ui-monospace, monospace" },
        }),
        EditorView.updateListener.of(update => {
          if (update.docChanged) onChangeRef.current?.(update.state.doc.toString())
        }),
      ]
    const editor = new EditorView({ parent: host.current!, doc: initialValue.current, extensions: extensions.current })
    view.current = editor
    return () => { initialValue.current = editor.state.doc.toString(); editor.destroy(); view.current = null }
  }, [fontSize, label, wrap])

  useEffect(() => {
    const editor = view.current
    if (editor && editor.state.doc.toString() !== value) {
      // External document replacement must not leak undo history between files.
      editor.setState(EditorState.create({ doc: value, extensions: extensions.current }))
    }
  }, [value])

  return <div ref={host} style={{ height }} className="min-w-0 overflow-hidden" />
}
