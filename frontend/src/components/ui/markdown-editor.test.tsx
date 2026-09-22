import { act, StrictMode, useState } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { EditorView } from "@codemirror/view"
import { undo, redo } from "@codemirror/commands"
import { openSearchPanel } from "@codemirror/search"
import { syntaxTree } from "@codemirror/language"
import { Editor } from "./markdown-editor"

let root: Root
let container: HTMLDivElement
beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true)
  container = document.createElement("div")
  document.body.append(container)
  root = createRoot(container)
})
afterEach(async () => {
  await act(async () => root.unmount())
  container.remove()
  vi.unstubAllGlobals()
})
function view() { return EditorView.findFromDOM(container.querySelector(".cm-editor")!)! }

it("keeps cursor and undo history across controlled React updates", async () => {
  function Controlled() {
    const [value, setValue] = useState("# Heading")
    return <Editor value={value} onChange={setValue} options={{ ariaLabel: "Test editor" }} />
  }
  await act(async () => root.render(<StrictMode><Controlled /></StrictMode>))
  const editor = view()
  await act(async () => editor.dispatch({ changes: { from: 9, insert: " text" }, selection: { anchor: 14 } }))
  expect(view()).toBe(editor)
  expect(editor.state.selection.main.head).toBe(14)
  expect(editor.contentDOM.getAttribute("aria-label")).toBe("Test editor")
  await act(async () => { expect(undo(editor)).toBe(true) })
  expect(editor.state.doc.toString()).toBe("# Heading")
  await act(async () => { expect(redo(editor)).toBe(true) })
  expect(editor.state.doc.toString()).toBe("# Heading text")
})

it("replaces external content without mixing undo history or emitting edits", async () => {
  const changed = vi.fn()
  await act(async () => root.render(<Editor value="First file" onChange={changed} />))
  await act(async () => view().dispatch({ changes: { from: 10, insert: "!" } }))
  changed.mockClear()
  await act(async () => root.render(<Editor value="# Second file" onChange={changed} />))
  expect(view().state.doc.toString()).toBe("# Second file")
  expect(undo(view())).toBe(false)
  expect(changed).not.toHaveBeenCalled()
  expect(syntaxTree(view().state).toString()).toContain("ATXHeading1")
  expect(openSearchPanel(view())).toBe(true)
  expect(container.querySelector('input[name="search"]')).not.toBeNull()
})

it("uses the latest callback and handles a large Markdown document", async () => {
  const first = vi.fn(), latest = vi.fn()
  const doc = "# Heading\n\n- Example item\n".repeat(10000)
  await act(async () => root.render(<Editor value={doc} onChange={first} />))
  await act(async () => root.render(<Editor value={doc} onChange={latest} />))
  await act(async () => view().dispatch({ changes: { from: doc.length, insert: "End" } }))
  expect(first).not.toHaveBeenCalled()
  expect(latest).toHaveBeenCalledWith(doc + "End")
})
