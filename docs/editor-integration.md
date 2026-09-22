# Markdown editor integration

The dashboard uses a locally bundled, lazy-loaded CodeMirror 6 editor for plans, project instructions, prompts, specifications and wizard drafts. All instances share the dashboard's light/dark theme, Markdown highlighting, search/replace, folding, wrapping and undo/redo behavior.

## State and keyboard behavior

- Each instance has an explicit document identity. Switching files resets history even when both files contain identical text. Controlled value echoes retain the current cursor and undo history.
- External document replacements reset history. The editor preserves CRLF line endings and Unicode when reporting changes.
- Ctrl/Cmd+S acts on the focused editor for project documents and respects saving/disabled state. The previous page-wide spec-save listener has been removed so saving instructions cannot accidentally save a dirty spec.
- Wizard draft edits update the existing persisted wizard store. No generation request is needed to edit them.
- Theme changes are driven by CSS tokens and leave editor state intact. Tab moves focus out of the editor.

The Monaco packages, obsolete compatibility props, worker and DOMPurify override are removed. Dated review/evaluation documents describe earlier states; this document describes the adopted implementation.

## Final validation — 2026-09-23

- 81 frontend tests passed, including seven editor integration tests covering controlled edits, StrictMode, cursor/history, document identity, shortcuts, Unicode/CRLF, a 260,000-character document and wizard file switching without any API/generation calls.
- 245 backend tests passed. ESLint, Ruff, TypeScript/Vite, bundle budgets and Docker/container smoke checks passed.
- Initial JavaScript: 292.1 KiB / 350 KiB. Lazy editor chunk: 546.2 KiB / 600 KiB (about 559 KB raw and 193 KB gzip). The optional editor remains substantially smaller than Monaco; Vite's generic 500 KB advisory remains unsuppressed.
- Browser smoke used a real disposable Git project with a tiny Python task-list module, two passing unittest tests, plan/instructions/prompt and two specs. No LLM generation job ran.
- Saved plan, AGENTS.md, PROMPT.md and spec edits through the real API, then verified the files on disk and reloaded the browser. Saving AGENTS.md while a spec was dirty left the spec unsaved until its own save action. An untouched second spec remained byte-for-byte unchanged.
- Search/replace, undo/redo across a theme change, file switching and dark/light rendering passed. The available browser's narrow layout was also inspected. No captured browser warnings/errors.

This is focused regression and browser validation, not a full screen-reader, IME or cross-browser certification.
