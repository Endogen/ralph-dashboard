# Code review and regression testing — 2026-09-22

Base: `77431b3` (main after branch consolidation). This pass examined persistence, authentication refresh, wizard polling, browser fallbacks, project restoration, and unused code. A code-only Graphify extraction helped trace backend relationships; Knip and Vulture findings were checked against actual callers and build configuration.

## Findings fixed

| Finding | Impact and correction |
| --- | --- |
| Concurrent settings writes lost changes | Simultaneous archive, registration and settings updates read the same old JSON and overwrote each other. SQLite compare-and-swap updates now retry against the latest value, including across independent connections. Duplicate archive operations report one actual change. |
| Refresh responses crossed login sessions | A late refresh could restore logged-out credentials, overwrite a new login, or clear it on an old authorization error. A nonpersistent session version scopes refresh deduplication, response handling and unauthorized-request retries. |
| Old polling failures changed a new generation | A previous job's 404 could clear the active job; other failures could overwrite its error. Error handling now checks the request ID, like successful responses already did. |
| Browser persistence could break login and wizard edits | Missing, blocked or full storage threw during state updates. A guarded storage adapter preserves in-memory operation and retains persistence when available. |
| Notification permission errors skipped the fallback | A rejected permission request escaped before the notification catch block. It now returns failure so the existing in-app toast fallback runs. |
| Restored projects stayed absent from the dashboard | Unarchiving updated only the archive page's private list. It now refreshes the shared project list. Reproduced and verified in both a regression test and the built app. |
| Dashboard statistics failures were unhandled | A failed overview request rejected an effect without feedback. The dashboard now reports the error via a toast while leaving project controls usable. Removed a redundant loading-state update. |

Concurrency, session, polling, permission and archive regressions were reproduced before the fixes. New tests also exercise storage failure modes and statistics error feedback.

## Dead code removed

- Unreferenced project status panel.
- Unused WebSocket send API and exposed socket reference (the internal transport remains).
- Unused active-project/project-list/auth store actions and public type exports.
- Obsolete wizard AbortController state; generation uses server-side job polling.
- Backend PID wrappers and termination helper used only by tests; tests now use the production lifecycle operations.
- Replaced settings setter and obsolete database documentation.

The remaining Knip unused-file report is the `react-is` compatibility shim, explicitly loaded through the Vite alias for Recharts. It is retained. Pydantic validator signatures are also retained despite static-analysis false positives.

## Validation

- Backend: **245 passing tests**, including five new SQLite concurrency regressions; Ruff passed.
- Frontend on Node 22: **74 passing tests** in 17 files; ESLint, TypeScript and Vite production build passed.
- Shell syntax and dependency lock consistency checks passed.
- Initial JavaScript: **292.0 KiB / 350 KiB**; all lazy-chunk budgets passed.
- Built-app browser smoke used an isolated temporary project and database: login, dashboard, project overview/charts, live log updates through the real watcher/WebSocket, archive and restore. No captured browser warnings or errors.
- Docker build and container smoke test passed on the final implementation.

Remaining nonblocking warnings: Starlette's AnyIO deprecation in tests and Vite's generic size warning for the deliberately lazy-loaded Monaco editor. The editor is within its explicit budget; reducing its language/features footprint is a possible future optimization.

This is a targeted review and regression pass. Browser testing used fixture data; it did not invoke a paid coding agent or prove every deployment/browser combination.
