import { act, StrictMode, useState } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { EditorView } from "@codemirror/view"
import { undo, redo } from "@codemirror/commands"
import { syntaxTree } from "@codemirror/language"
import { Editor } from "./markdown-editor"

let root: Root
let container: HTMLDivElement
beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true)
  // JSDOM has no text layout; focus/selection code still needs range geometry.
  const createRange = document.createRange.bind(document)
  vi.spyOn(document, "createRange").mockImplementation(() => {
    const range = createRange()
    range.getClientRects = () => [] as unknown as DOMRectList
    range.getBoundingClientRect = () => new DOMRect()
    return range
  })
  container = document.createElement("div")
  document.body.append(container)
  root = createRoot(container)
})
afterEach(async () => {
  await act(async () => root.unmount())
  container.remove()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})
function view() { return EditorView.findFromDOM(container.querySelector(".cm-editor")!)! }

it("keeps cursor and undo history across controlled React updates", async () => {
  function Controlled() {
    const [value, setValue] = useState("# Heading")
    return <Editor documentId="test/a.md" ariaLabel="Markdown editor" value={value} onChange={setValue} />
  }
  await act(async () => root.render(<StrictMode><Controlled /></StrictMode>))
  const editor = view()
  await act(async () => editor.dispatch({ changes: { from: 9, insert: " text" }, selection: { anchor: 14 } }))
  expect(view()).toBe(editor)
  expect(editor.state.selection.main.head).toBe(14)
  expect(editor.contentDOM.getAttribute("aria-label")).toBe("Markdown editor")
  await act(async () => { expect(undo(editor)).toBe(true) })
  expect(editor.state.doc.toString()).toBe("# Heading")
  await act(async () => { expect(redo(editor)).toBe(true) })
  expect(editor.state.doc.toString()).toBe("# Heading text")
})

it("replaces external content without mixing undo history or emitting edits", async () => {
  const changed = vi.fn()
  await act(async () => root.render(<Editor documentId="test/a.md" ariaLabel="Markdown editor" value="First file" onChange={changed} />))
  await act(async () => view().dispatch({ changes: { from: 10, insert: "!" } }))
  changed.mockClear()
  await act(async () => root.render(<Editor documentId="test/a.md" ariaLabel="Markdown editor" value="# Second file" onChange={changed} />))
  expect(view().state.doc.toString()).toBe("# Second file")
  expect(undo(view())).toBe(false)
  expect(changed).not.toHaveBeenCalled()
  expect(syntaxTree(view().state).toString()).toContain("ATXHeading1")
  await act(async () => container.querySelector<HTMLButtonElement>('button[aria-label="Find in markdown editor"]')!.click())
  expect(container.querySelector('input[name="search"]')).not.toBeNull()
})

it("uses the latest callback and handles a large Markdown document", async () => {
  const first = vi.fn(), latest = vi.fn()
  const doc = "# Heading\n\n- Example item\n".repeat(10000)
  await act(async () => root.render(<Editor documentId="test/a.md" ariaLabel="Markdown editor" value={doc} onChange={first} />))
  await act(async () => root.render(<Editor documentId="test/a.md" ariaLabel="Markdown editor" value={doc} onChange={latest} />))
  await act(async () => view().dispatch({ changes: { from: doc.length, insert: "End" } }))
  expect(first).not.toHaveBeenCalled()
  expect(latest).toHaveBeenCalledWith(doc + "End")
})


it("resets history when switching to a different file with identical text", async () => {
  const changed = vi.fn()
  await act(async () => root.render(<Editor documentId="a" ariaLabel="Editor" value="Draft" onChange={changed} />))
  await act(async () => view().dispatch({ changes: { from: 5, insert: "!" } }))
  const previous = view()
  await act(async () => root.render(<Editor documentId="b" ariaLabel="Editor" value="Draft!" onChange={changed} />))
  expect(view()).not.toBe(previous)
  expect(undo(view())).toBe(false)
  expect(view().state.doc.toString()).toBe("Draft!")
})

it("routes the save shortcut only to the focused editor and respects disabled saving", async () => {
  const saveA = vi.fn(), saveB = vi.fn(), changed = vi.fn()
  const editors = (disabled = false) => <>
    <Editor documentId="a" ariaLabel="Editor A" value="A" onChange={changed} onSave={saveA} />
    <Editor documentId="b" ariaLabel="Editor B" value="B" onChange={changed} onSave={saveB} saveDisabled={disabled} />
  </>
  await act(async () => root.render(editors()))
  const second = container.querySelectorAll<HTMLElement>(".cm-content")[1]
  const save = () => second.dispatchEvent(new KeyboardEvent("keydown", { key: "s", ctrlKey: true, bubbles: true, cancelable: true }))
  await act(async () => { second.focus(); save() })
  expect(saveA).not.toHaveBeenCalled()
  expect(saveB).toHaveBeenCalledOnce()
  await act(async () => root.render(editors(true)))
  await act(async () => { save() })
  expect(saveB).toHaveBeenCalledOnce()
})

it("preserves CRLF line endings and Unicode while editing", async () => {
  const changed = vi.fn()
  await act(async () => root.render(<Editor documentId="crlf" ariaLabel="Editor" value={"# Café\r\n你好\r\n"} onChange={changed} />))
  await act(async () => view().dispatch({ changes: { from: 6, insert: "!" } }))
  expect(changed).toHaveBeenCalledWith("# Café!\r\n你好\r\n")
})

it("edits wizard drafts and switches files without running generation", async () => {
  const { StepGenerateReview } = await import("@/components/wizard/step-generate-review")
  const { useWizardStore } = await import("@/stores/wizard-store")
  const fetcher = vi.fn()
  vi.stubGlobal("fetch", fetcher)
  useWizardStore.getState().reset()
  useWizardStore.setState({ generatedFiles: [
    { path: "AGENTS.md", content: "Instructions" },
    { path: "PROMPT.md", content: "Instructions!" },
  ] })
  try {
    await act(async () => root.render(<StepGenerateReview />))
    await act(async () => view().dispatch({ changes: { from: 12, insert: "!" } }))
    expect(useWizardStore.getState().generatedFiles[0].content).toBe("Instructions!")
    await act(async () => [...container.querySelectorAll("button")].find(button => button.textContent === "PROMPT.md")!.click())
    expect(view().state.doc.toString()).toBe("Instructions!")
    expect(undo(view())).toBe(false)
    expect(fetcher).not.toHaveBeenCalled()
  } finally {
    await act(async () => root.render(null))
    useWizardStore.getState().reset()
  }
})
