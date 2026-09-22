# Monaco → CodeMirror evaluation — 2026-09-23

Recommendation: adopt a tailored CodeMirror editor for the dashboard's current Markdown editing needs. The measured size reduction is substantial and the tested editing flows work. This is an isolated prototype based on main `15abe36`; it has not been merged or pushed.

## Measured production builds

Both variants use the same application base, Node 22 and Vite production build. Sizes below include editor-specific JavaScript, CSS, the lazy wrapper, and (for Monaco) the worker and Markdown registration chunk. Decimal KB/MB are used here. Gzip sizes were measured consistently with Python gzip at its default compression level; server compression settings can differ.

| Metric | Monaco | CodeMirror prototype | Change |
| --- | ---: | ---: | ---: |
| Editor-related assets | 3,017,035 bytes | 558,446 bytes | 81.5% smaller |
| Same assets, gzip | 781,116 bytes | 191,134 bytes | 75.5% smaller |
| Initial application JavaScript | 292.0 KiB | 292.0 KiB | Effectively unchanged |
| Separate editor worker | 272,779 bytes | None | Removed |

The editor remains lazy-loaded and served by the application, with no runtime CDN dependency. The initial dashboard already avoids this download; savings apply when editing is opened. This evaluation measures assets, not a statistically controlled load-time, CPU or memory benchmark. The expected benefit is less transfer and less code to process; exact latency depends on the device and network.

## Prototype

Uses direct CodeMirror packages for view/state, Markdown, commands/history, search, bracket handling, folding and a dark theme. It retains a temporary compatibility adapter so the existing five editor instances across the four component files can use the same props during evaluation. The prototype also replaces the obsolete Monaco product copy and sets an editor-specific 600 KiB budget instead of the old 3,000 KiB exception.

The existing application uses Markdown mode everywhere. Features included in this prototype: highlighting, line numbers, wrapping, undo/redo, search/replace controls, folding, bracket matching/closing, Markdown list key bindings, accessible editor names and Tab navigation out of the editor. It does not reproduce Monaco's complete command palette or IDE features.

## Verification

- All **77 frontend tests** passed (74 existing plus 3 editor integration tests).
- ESLint, TypeScript, Vite build and revised bundle checks passed.
- New tests exercise React controlled value echoes without cursor/history loss, undo/redo, StrictMode lifecycle, external document replacement without history leakage or spurious onChange, current callback handling, Markdown parsing/search controls and a 260,000-character document.
- Browser smoke on the built app with a disposable project/database: three editors render together on Specs, editing updates dirty state, Cmd+Z and Cmd+Shift+Z work, Cmd+S saves through the existing backend, and saved content survives reload.
- Search opens with Cmd+F and highlights a requested match. Switching to a different spec then undoing does not restore the previous file's text. Tab moves focus out of the editor.
- Raw plan editing screen renders with highlighting; screenshot inspected. No captured browser errors/warnings.
- Package installation reported zero known vulnerabilities.

## Tradeoffs and remaining adoption checks

- Visual styling and keyboard conventions differ. Current Monaco is explicitly dark even in light application mode; the prototype preserves this behavior using CodeMirror's dark theme.
- More modular dependency packages and a small React lifecycle adapter replace the existing Monaco React wrapper. That adapter needs maintenance; tests cover its most important state transitions.
- Undo history resets when an external document is replaced. Edits echoed back from the parent retain history and cursor position.
- A production migration should simplify the temporary Monaco-shaped props, explicitly identify documents at all call sites, and review the remaining Monaco references in documentation.
- Browser checks were on the available macOS browser. Windows/Linux keyboard behavior, IME input and a screen-reader session were not tested. Large-document integrity was tested automatically; interactive large-document responsiveness was not benchmarked.
- The wizard shares the same editor wrapper and passes existing tests, but no paid generation job was invoked for this evaluation.
- CodeMirror's ~545 KiB lazy chunk still triggers Vite's generic 500 KB advisory, while passing the more specific 600 KiB budget. Eliminating a warning alone is not a reason to remove useful editing features.

Prototype source: `frontend/src/components/ui/markdown-editor.tsx`; integration tests are adjacent. Main remains unchanged, with no new branch or pull request.
