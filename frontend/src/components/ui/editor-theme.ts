import { EditorView } from "@codemirror/view"
import { HighlightStyle } from "@codemirror/language"
import { tags } from "@lezer/highlight"

// Use the application's tokens so theme changes never recreate the document.
export const editorTheme = EditorView.theme({
  "&": { height: "100%", backgroundColor: "var(--background)", color: "var(--foreground)" },
  "&.cm-focused": { outline: "none" },
  ".cm-scroller": { overflow: "auto", fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", monospace', lineHeight: "1.75" },
  ".cm-content": { padding: "14px 0", caretColor: "var(--primary)" },
  ".cm-line": { padding: "0 16px 0 10px" },
  ".cm-gutters": { backgroundColor: "var(--background)", color: "var(--muted-foreground)", borderRight: "1px solid var(--border)", paddingLeft: "6px" },
  ".cm-gutterElement": { padding: "0 8px 0 4px" },
  ".cm-activeLine, .cm-activeLineGutter": { backgroundColor: "color-mix(in srgb, var(--primary) 6%, transparent)" },
  ".cm-activeLineGutter": { color: "var(--primary)" },
  ".cm-cursor, .cm-dropCursor": { borderLeftColor: "var(--primary)" },
  "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection": { backgroundColor: "color-mix(in srgb, var(--primary) 24%, transparent)" },
  ".cm-searchMatch": { backgroundColor: "color-mix(in srgb, var(--primary) 18%, transparent)", outline: "1px solid color-mix(in srgb, var(--primary) 40%, transparent)", borderRadius: "2px" },
  ".cm-searchMatch.cm-searchMatch-selected": { backgroundColor: "color-mix(in srgb, var(--primary) 32%, transparent)" },
  ".cm-selectionMatch, .cm-matchingBracket": { backgroundColor: "color-mix(in srgb, var(--primary) 15%, transparent)" },
  ".cm-foldPlaceholder": { backgroundColor: "var(--muted)", borderColor: "var(--border)", color: "var(--muted-foreground)", borderRadius: "4px" },
  ".cm-panels": { backgroundColor: "var(--card)", color: "var(--foreground)", fontFamily: '"IBM Plex Sans", "Segoe UI", sans-serif' },
  ".cm-panels-top": { borderBottom: "1px solid var(--border)" },
  ".cm-search": { padding: "8px 32px 8px 10px !important", fontSize: "12px" },
  ".cm-search label": { display: "inline-flex", alignItems: "center", gap: "4px", margin: "4px 8px 4px 0", whiteSpace: "nowrap" },
  ".cm-search input[type=checkbox]": { accentColor: "var(--primary)" },
  ".cm-textfield": { backgroundColor: "var(--background)", color: "var(--foreground)", border: "1px solid var(--input)", borderRadius: "6px", padding: "5px 8px", maxWidth: "100%", outline: "none" },
  ".cm-textfield:focus": { borderColor: "var(--primary)", boxShadow: "0 0 0 2px color-mix(in srgb, var(--primary) 15%, transparent)" },
  ".cm-button": { backgroundImage: "none", backgroundColor: "var(--background)", color: "var(--foreground)", border: "1px solid var(--border)", borderRadius: "6px", padding: "4px 8px", fontSize: "12px", textTransform: "capitalize", cursor: "pointer" },
  ".cm-button:hover": { backgroundColor: "var(--accent)" },
  ".cm-button:focus-visible": { outline: "2px solid var(--primary)", outlineOffset: "2px" },
  ".cm-search button[name=close]": { color: "var(--muted-foreground)", cursor: "pointer", top: "8px", right: "8px", fontSize: "18px" },
  ".cm-tooltip": { backgroundColor: "var(--popover)", color: "var(--popover-foreground)", border: "1px solid var(--border)", borderRadius: "6px" },
})

export const editorHighlighting = HighlightStyle.define([
  { tag: tags.heading, color: "var(--primary)", fontWeight: "600" },
  { tag: tags.strong, fontWeight: "700" },
  { tag: tags.emphasis, fontStyle: "italic" },
  { tag: tags.strikethrough, textDecoration: "line-through" },
  { tag: [tags.link, tags.url], color: "var(--primary)", textDecoration: "underline", textUnderlineOffset: "3px" },
  { tag: [tags.monospace, tags.string], color: "var(--editor-code)" },
  { tag: [tags.processingInstruction, tags.meta, tags.comment], color: "var(--muted-foreground)" },
  { tag: [tags.keyword, tags.atom, tags.bool], color: "var(--editor-keyword)" },
  { tag: [tags.number, tags.literal], color: "var(--editor-code)" },
])
