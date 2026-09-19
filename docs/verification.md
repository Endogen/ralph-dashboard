# Reliability overhaul verification — 2026-09-19

This change addresses all 14 confirmed findings from the initial repository audit and the related workflow, performance and deployment issues.

## Changes and regression coverage

| Original issue | Implemented behavior |
| --- | --- |
| Public default signing key | Required signing key, rejected placeholders, rotated-credential token invalidation; credentials removed from tracking. |
| Restricted Claude silently bypassed permissions | Explicit provider permission modes, one shared command builder, restricted/full-access UI wording. |
| Shell cleanup terminated normal runs | Packaged Python runner with a small shell entry point, explicit lifecycle and reliable cleanup. |
| Creation raced discovery | Creation invalidates discovery and refreshes watches before optional startup. |
| New projects lacked watchers | Immediate refresh and periodic reconciliation of watched projects. |
| Stop left children alive | Process identities, captured process group, TERM/KILL escalation and exit verification. |
| Failed tests reported completion | Completion requires successful execution and configured verification; cancelled work reports Stopped. |
| Buffered or duplicated output | One log writer, incremental output, cursor-based browser reconciliation. |
| Watchers lost rapid changes | Trailing coalescing, byte-accurate chunk draining, partial JSONL retention and plan-content invalidation. |
| History stopped at 500 | Complete pagination; cumulative charts sampled after calculation. |
| Config erased model selection | Shared configuration schema, exposed model field and round-trip persistence. |
| Docker could not execute loops | Packaged runner, pinned provider CLIs, unprivileged runtime and persistent project/auth/data mounts. |
| New/active projects auto-archived | Unknown activity is not treated as inactivity; running/paused projects excluded. |
| Failed creation left partial writes | Path validation, staged publication, existing-file preview/version checks and rollback. |

Additional changes include async SQLite and bcrypt handling, login throttling, durable wizard polling/cancellation, controlled context for existing projects, atomic file edits with stale-save rejection, a single authenticated websocket, fewer overview requests, route/editor splitting, offline editor assets, rebuilt source installs, service PATH handling, updated dependencies and CI.

## Validation

- Backend suite: 223 tests passing on macOS and Linux. Includes real runner subprocesses, resistant child processes, cleanup of orphaned background processes after successful completion, pause/inject/resume/stop, rate limits, failed verification, streamed usage, partial writes, stale previews and password rotation.
- Frontend suite: 16 tests passing, including history beyond 500 records and preservation of a draft's revision across background refreshes.
- Ruff, ESLint, TypeScript/Vite build, shell syntax and Git whitespace checks pass.
- Actual HTTP/WebSocket workflow: authentication, wizard creation, immediate discovery/watchers, startup, logs, completion, configuration, editing conflicts and 601-record history.
- Browser walkthrough: login, wizard generation with navigation and reload, file preview, create/start/completion, model persistence, log tab re-entry, locally loaded editor and a 390-pixel mobile viewport. No browser console errors observed during the final checks.
- Docker image built and smoke-tested: both provider CLI version commands, installed runner with a deterministic agent, health endpoint and served frontend.
- Initial JavaScript reduced from 842.89 kB to approximately 297 kB. CI enforces a 350 KiB entry budget. The larger Monaco editor is loaded only on demand.
- Python package audit: no known vulnerabilities in the rebuilt image's audited environment. Frontend audit returned zero findings after dependency updates; the final repeat was unavailable because npm's advisory endpoint returned HTTP 503 maintenance responses.

## Scope of the evidence

The orchestration tests and browser walkthrough use deterministic local agents. They verify the dashboard and runner, not the quality of a paid provider's generated code or account-specific authentication/policy. The installed provider CLIs were checked with `--version`; a live paid-provider project was not run.

The CI workflow is added locally; a hosted GitHub Actions run has not been triggered. Linux validation reports an upstream Starlette/AnyIO deprecation warning. Monaco produces Vite's large optional-chunk advisory. Neither warning is suppressed.

See [reliability and deployment contracts](reliability.md) for setup, permissions, storage and runtime limits.
