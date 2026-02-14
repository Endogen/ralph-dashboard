import { Editor } from "@monaco-editor/react"

type PlanMarkdownEditorProps = {
  value: string
  onChange: (value: string) => void
  onSave: () => void
  isSaving: boolean
}

export function PlanMarkdownEditor({
  value,
  onChange,
  onSave,
  isSaving,
}: PlanMarkdownEditorProps) {
  return (
    <section className="rounded-xl border bg-card p-4">
      <header className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold">Raw Plan Markdown</h3>
          <p className="text-sm text-muted-foreground">
            Monaco editor mode for full markdown control over `IMPLEMENTATION_PLAN.md`.
          </p>
        </div>
        <button
          type="button"
          onClick={onSave}
          disabled={isSaving}
          className="rounded-md border bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSaving ? "Saving..." : "Save"}
        </button>
      </header>

      <div className="h-[520px] overflow-hidden rounded-lg border">
        <Editor
          height="100%"
          defaultLanguage="markdown"
          value={value}
          onChange={(nextValue) => onChange(nextValue ?? "")}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            wordWrap: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>
    </section>
  )
}
