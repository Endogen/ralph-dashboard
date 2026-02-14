# AGENTS.md

## Project
Ralph Dashboard — A web UI for monitoring and controlling Ralph Loop AI agent sessions. 
FastAPI backend with React frontend, real-time WebSocket updates, multi-project support.

## Tech Stack
- **Backend**: Python 3.12, FastAPI 0.129.0, watchdog, GitPython, python-jose, passlib, aiosqlite, uvicorn
- **Frontend**: React 19.2.x, Vite 7.3.x, TypeScript, Tailwind CSS 4.1.x, shadcn/ui, Recharts 3.7.x, Monaco Editor 4.7.x, Zustand 5.0.x, React Router 7.13.x, Lucide React
- **Database**: SQLite (for auth/settings only — all project data is file-based)

## Commands
- **Backend install**: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e .`
- **Backend run**: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8420`
- **Backend test**: `cd backend && source .venv/bin/activate && pytest`
- **Backend lint**: `cd backend && source .venv/bin/activate && ruff check . --fix && ruff format .`
- **Frontend install**: `cd frontend && npm install`
- **Frontend run**: `cd frontend && npm run dev -- --port 3420`
- **Frontend build**: `cd frontend && npm run build`
- **Frontend lint**: `cd frontend && npm run lint`

## Backpressure
Run these after EACH implementation (in order):
1. Backend lint: `cd backend && .venv/bin/ruff check . --fix && .venv/bin/ruff format .`
2. Backend tests: `cd backend && .venv/bin/pytest --timeout=30 -x`
3. Frontend lint: `cd frontend && npm run lint 2>&1 | head -30`
4. Frontend build check: `cd frontend && npm run build 2>&1 | tail -20`

## Project Structure
```
ralph-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + startup/shutdown
│   │   ├── config.py                # Settings
│   │   ├── database.py              # SQLite setup
│   │   ├── auth/                    # JWT auth
│   │   ├── projects/                # Project discovery + CRUD
│   │   ├── iterations/              # Iteration parsing + endpoints
│   │   ├── plan/                    # Plan parsing + endpoints
│   │   ├── files/                   # File read/write endpoints
│   │   ├── git_service/             # Git operations
│   │   ├── control/                 # Start/stop/pause process management
│   │   ├── stats/                   # Statistics aggregation
│   │   ├── notifications/           # Notification history
│   │   └── ws/                      # WebSocket hub + file watcher
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                     # REST client + types
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui
│   │   │   ├── layout/              # Sidebar, TopBar, ControlBar
│   │   │   ├── dashboard/           # ProjectCard, ProjectGrid
│   │   │   ├── project/             # Tab components
│   │   │   ├── charts/              # Recharts wrappers
│   │   │   └── editors/             # Monaco wrappers
│   │   ├── hooks/                   # useWebSocket, useProject, etc.
│   │   ├── stores/                  # Zustand stores
│   │   ├── lib/                     # Utils
│   │   └── types/                   # TypeScript types
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
├── scripts/
│   └── ralph.sh                     # Modified ralph loop
└── README.md
```

## Conventions
- Backend: Python type hints everywhere, async endpoints, Pydantic models for request/response
- Frontend: TypeScript strict mode, functional components, named exports
- Commits: conventional commits (feat:, fix:, refactor:, test:, chore:)
- File naming: snake_case for Python, kebab-case for TS/React files
- Components: one component per file, colocate styles/types

## Important Notes
- The dashboard reads Ralph project data from the filesystem (no DB for project data)
- Projects are discovered by scanning configured directories for `.ralph/` subdirs
- WebSocket uses watchdog (inotify) to detect file changes and push to clients
- Auth credentials stored in a config YAML file (bcrypt-hashed password)
- The modified `ralph.sh` writes `.ralph/iterations.jsonl` for structured data
- PID file `.ralph/ralph.pid` used to detect running loops
- Pause mechanism via `.ralph/pause` sentinel file
- Injection via `.ralph/inject.md` (appended to AGENTS.md, then deleted)

## Human Decisions
<!-- Record decisions made by humans here so future iterations have context -->

## Learnings
<!-- Agent appends operational notes here during execution -->
- 2026-02-14: Frontend dependency install may be blocked in restricted environments due DNS resolution failures for `registry.npmjs.org`; `npm run lint`/`npm run build` will fail until package installation succeeds.
- 2026-02-14: `npm install` failed with `EAI_AGAIN` for both `registry.npmjs.org` and `registry.npmmirror.com` in this environment, so frontend toolchain binaries (`eslint`, `tsc`, `vite`) were unavailable for lint/build validation.
- 2026-02-14: `npm install` can hang silently in this environment; using `--fetch-retries=1 --fetch-retry-mintimeout=1000 --fetch-retry-maxtimeout=2000` fails fast and confirms DNS-level `EAI_AGAIN` blockage.
- 2026-02-14: Without installed frontend dependencies, backpressure checks report `sh: 1: eslint: not found` and `sh: 1: tsc: not found`; `npm install --offline` also fails with `ENOTCACHED` when no local package cache exists.
- 2026-02-14: Backpressure commands piped to `head`/`tail` can still exit with status 0 even when frontend scripts fail; always inspect output for `eslint: not found` / `tsc: not found`.
- 2026-02-14: In this sandbox, npm may also fail to write debug logs to `/home/endogen/.npm/_logs`, so rely on terminal stderr for diagnostics.
- 2026-02-14: Backend backpressure checks can pass while frontend remains blocked; repeated `npm install` attempts against npmjs/npmmirror returned `EAI_AGAIN`, and offline install returned `ENOTCACHED`, so frontend lint/build validation requires restored registry access or a prewarmed npm cache.
- 2026-02-14: For backpressure validation, three sequential install strategies (`npm install` default, `--registry=https://registry.npmmirror.com`, and `--offline`) quickly distinguish DNS outage (`EAI_AGAIN`) from cache absence (`ENOTCACHED`).
- 2026-02-14: If frontend backpressure still fails after those three install attempts, write `.ralph/pending-notification.txt` with an `ERROR:` message and pause for human help because frontend lint/build cannot be unblocked locally.
- 2026-02-14: `.ralph/` notification files are ignored by git in this repo, so confirm writes with `cat .ralph/pending-notification.txt` rather than `git status`.
- 2026-02-14: Once `frontend/node_modules` is available, backpressure frontend checks run normally; successful `npm run lint` may print only the script header with no additional output.
- 2026-02-14: `app.config.get_settings()` is `lru_cache`d; when tests or scripts mutate `RALPH_*` env vars, call `get_settings.cache_clear()` before reloading settings.
- 2026-02-14: In this sandbox, thread-to-event-loop wakeups can be delayed; keep a lightweight heartbeat task running during `aiosqlite` work to prevent stalled awaits/timeouts.
- 2026-02-14: `passlib` bcrypt backend can fail with modern `bcrypt` releases in this environment; use direct `bcrypt.hashpw` / `bcrypt.checkpw` for stable password hashing tests.
- 2026-02-14: `fastapi.testclient` requires `httpx`, which is not preinstalled here and may be un-installable during DNS outages; prefer unit-testing auth helpers/dependencies directly when network installs are blocked.
- 2026-02-14: Initialize auth credentials with `ralph-dashboard-init-user`; use `--username/--password/--password-confirm` for non-interactive setup in scripts and tests.
- 2026-02-14: Async auth route handlers (`login`, `refresh_token`) can be tested directly with request models, which avoids `TestClient`/`httpx` dependency constraints.
- 2026-02-14: Project discovery scans configured roots recursively for `.ralph/` and skips heavy/noisy folders like `node_modules`, `.git`, and cache dirs.
- 2026-02-14: Project status detection precedence is: running+pause file => `paused`, running without pause => `running`, otherwise `STATUS: COMPLETE` in plan => `complete`, else `stopped`.
- 2026-02-14: Manual project registrations are persisted in SQLite setting key `registered_project_paths` as a JSON array of absolute paths.
- 2026-02-14: `GET /api/projects` and `GET /api/projects/{id}` return data from the union of discovered and manually registered paths, deduped by absolute path.
- 2026-02-14: `ralph.log` parser matches headers like `[HH:MM:SS] === Iteration N/M ===`, reads token counts from the line after `tokens used` (commas supported), and flags common error markers.
- 2026-02-14: `iterations.jsonl` parsing is line-tolerant: malformed JSON or schema-invalid lines are skipped so one bad line does not drop the whole file.
- 2026-02-14: IMPLEMENTATION_PLAN parser captures global `STATUS`, phase blocks, checkbox tasks (with indentation), and computes per-phase + overall done/total counts.
- 2026-02-14: Iteration endpoints merge `.ralph/ralph.log` and `.ralph/iterations.jsonl` by iteration number; JSONL fields override summary metadata while log data provides `log_output`.
- 2026-02-14: `PUT /api/projects/{id}/plan` writes raw markdown to `IMPLEMENTATION_PLAN.md` and returns the freshly parsed structure from the submitted content.
- 2026-02-14: Parser fixture tests use `backend/tests/fixtures/antique-catalogue/`; log header parsing now strips ANSI color codes before matching iteration markers.
- 2026-02-14: File endpoints map aliases `agents`/`prompt` to `AGENTS.md`/`PROMPT.md` under each resolved project path and return `{name, content}` payloads.
- 2026-02-14: Specs CRUD endpoints enforce single-file `.md` names (no path separators) to prevent path traversal and keep operations confined to `project/specs/`.
- 2026-02-14: Git service resolves project repos by id, returns short 7-char hashes with commit stats, and uses `git show --format=''` for diff payloads.
- 2026-02-14: Stats aggregation currently uses default cost rate `$0.006 / 1K tokens`, plan `tasks_done/tasks_total`, and merged iteration data for velocity/projection/health calculations.
- 2026-02-14: Stats endpoint is available at `GET /api/projects/{project_id}/stats` and directly returns the aggregation model produced by `aggregate_project_stats`.
- 2026-02-14: Notification history endpoint aggregates `.ralph/pending-notification.txt`, `.ralph/last-notification.txt`, and archived notification files, then sorts entries by timestamp descending.
- 2026-02-14: Markdown report generation is available via `GET /api/projects/{project_id}/report`, combining project status, plan progress, iteration table, and error summary.
- 2026-02-14: Process manager start writes `.ralph/ralph.pid`, rejects duplicate live PIDs, and defaults to `<project>/ralph.sh` with fallback to dashboard `scripts/ralph.sh`.
- 2026-02-14: Stop logic treats `/proc/<pid>/stat` state `Z` as not running, which avoids false positives from zombie PIDs after SIGTERM/SIGKILL.
- 2026-02-14: Pause/resume helpers are idempotent: pause creates/touches `.ralph/pause` and resume removes it, each returning whether state changed.
- 2026-02-14: Injection helper rejects blank messages and appends new instructions to `.ralph/inject.md` when a prior pending injection already exists.
- 2026-02-14: Loop config service reads/writes `.ralph/config.json` with defaults (`cli`, `flags`, `max_iterations`, `test_command`, `model_pricing`) and raises explicit parse/validation errors for invalid JSON or values.
- 2026-02-14: Control API routes now live under `/api/projects/{project_id}` (`start`, `stop`, `pause`, `resume`, `inject`, `GET/PUT config`); start merges request overrides with persisted config and passes values via `RALPH_*` env vars.
- 2026-02-14: Control router handlers are covered by direct async tests (`backend/tests/test_control_router.py`) including config round-trip, start override behavior, and pause/resume/inject flows without relying on `TestClient`.
- 2026-02-14: WebSocket hub lives in `app/ws/hub.py` with per-connection project subscriptions; `/api/ws` currently supports `subscribe`, `unsubscribe`, and `ping` (`pong`) messages plus `emit`/`broadcast` helpers for backend event producers.
- 2026-02-14: File watcher service (`app/ws/file_watcher.py`) now runs in app lifespan, maintains watchdog observers per discovered/registered project, and filters events to `.ralph` runtime files, root control files, and `specs/*.md`.
- 2026-02-14: Watcher dispatch now parses `.ralph/ralph.log` changes and emits websocket `iteration_started` plus `iteration_completed` envelopes (status inferred from log errors) while deduplicating by project+iteration.
- 2026-02-14: `IMPLEMENTATION_PLAN.md` watcher events are parsed and emitted as websocket `plan_updated` payloads with per-phase done/total/status; duplicate snapshots are suppressed per project.
- 2026-02-14: Watcher dispatch now emits websocket `notification` from `.ralph/pending-notification.txt`, `status_changed` when `.ralph/ralph.pid`/`.ralph/pause`/plan changes alter detected status, and `file_changed` for other watched files.
- 2026-02-14: WebSocket connection at `/api/ws` now requires a valid `token` query parameter; missing or invalid JWTs are rejected before joining the hub.
- 2026-02-14: WebSocket tests (`backend/tests/test_ws.py`) use async fake socket objects (no `TestClient`/`httpx`) to validate hub subscription filtering, event envelopes, auth rejection, and protocol actions (`subscribe`/`unsubscribe`/`ping`).
- 2026-02-14: Frontend `AppLayout` now provides the phase-9 shell (sidebar + main content area), and routing reserves `/`, `/login`, and `/project/:id/*` for dashboard/auth/project detail flows.
- 2026-02-14: Sidebar UI is now a dedicated `AppSidebar` component with status badges, project links, and an Add Project action slot; `AppLayout` currently seeds it with demo project rows pending Zustand/API wiring.
- 2026-02-14: `ProjectTopBar` now renders project name, status badge, and quick stat chips (iteration/runtime/tokens/cost) and is mounted at the top of `ProjectPage` as the phase-9 top-bar scaffold.
- 2026-02-14: `ProjectControlBar` now provides Start/Pause-Resume/Stop actions plus inject input/send and summary status text; `ProjectPage` wires demo values pending API/store hookup.
- 2026-02-14: Login flow now posts to `/api/auth/login`, stores access/refresh tokens in Zustand, redirects back to the originally requested route, and the app shell is guarded by a simple token-based route gate.
- 2026-02-14: `apiFetch` now attaches bearer tokens from Zustand, retries once on `401` via `/api/auth/refresh`, and clears auth state if refresh fails.
- 2026-02-14: Zustand stores now include persisted auth tokens, a projects list store (`fetchProjects`/upsert/remove), and an active-project detail store (`fetchActiveProject`), with `AppLayout` and `ProjectPage` hooked to these stores.
- 2026-02-14: `useWebSocket` now handles token-authenticated connect, exponential reconnect (1s→30s), project subscribe/unsubscribe diffing, and JSON event dispatch; `AppLayout` shows live/reconnecting/offline state from the hook.
- 2026-02-14: Dashboard `ProjectCard` component is now available with status badge, iteration progress bar, token/cost stat cells, last-activity text, and mini iteration-health strip.
- 2026-02-14: Dashboard now uses a responsive `ProjectGrid` (1/2/3 columns) wired to `useProjectsStore`; it renders loading/error/empty states and routes card open actions to `/project/:id`.
- 2026-02-14: Add-project flow now uses `AddProjectDialog` modal from `AppLayout`; it posts absolute path to `POST /api/projects` and upserts the returned project summary into `useProjectsStore`.
- 2026-02-14: Project cards now react to websocket events through `AppLayout` (`status_changed` patches project status in-store, iteration/plan events trigger project refresh), so dashboard state updates without manual reload.
- 2026-02-14: Overview tab scaffolding now includes a `StatusPanel` component (large status badge + iteration/runtime/CLI/mode blocks) mounted inside `ProjectPage`.
- 2026-02-14: Overview `StatsGrid` component is now in place with eight icon-based stat cards (tokens, cost, iterations, duration, tasks, errors, success rate, health summary).
- 2026-02-14: Recharts build can fail in this sandbox with unresolved `react-is`; aliasing `react-is` to `frontend/src/vendor/react-is.ts` in `vite.config.ts` provides a local fallback when npm registry access is blocked.
- 2026-02-14: Overview now includes `TaskBurndownChart`, using unique completed-task accumulation from iteration events to render ideal vs actual remaining tasks and ahead/behind tinted bands.
- 2026-02-14: `TokenUsagePhaseChart` now renders a donut from stats `tokens_by_phase`, sorted by token volume, with exact-value tooltip and centered total token count.
- 2026-02-14: `IterationHealthTimeline` now classifies each iteration as productive/partial/failed using task completion, commit presence, error flags, and test status, then renders a compact clickable health strip.
- 2026-02-14: `RecentActivityFeed` now merges iteration-derived events (completion/tasks/errors) with `/notifications` history, sorts by timestamp descending, and renders the latest activity cards on Overview.
- 2026-02-14: Overview charts now live-refresh via a project-scoped `useWebSocket` subscription in `ProjectPage`; relevant events are debounced (300ms) before reloading iterations/stats/notifications.
- 2026-02-14: `PlanRenderer` is now available with collapsible phase cards, per-phase progress bars, read-only task checkboxes (with indentation), and pending/in-progress/complete badges sourced from `/plan`.
- 2026-02-14: Plan checkboxes are now interactive; `ProjectPage` maps phase/task to checkbox ordinal in `plan.raw`, patches markdown safely, saves via `PUT /plan`, then refreshes overview data.
- 2026-02-14: Plan view now has a Monaco-powered raw markdown mode (`PlanMarkdownEditor`) with toggle + save flow (`PUT /plan`) and syncs back to rendered mode after successful save.
- 2026-02-14: Plan tasks now display completion metadata when available by mapping task IDs to iteration + commit from iteration history; commit hashes render as links to the project code route with commit query.
- 2026-02-14: Iterations UI now includes `IterationsTable` with client-side sortable columns (`#`, status, health, duration, tokens, cost, tasks, commit, test), and per-row cost uses the default `$0.006/1K` token rate.
- 2026-02-14: Iteration health scoring is centralized in `frontend/src/lib/iteration-health.ts` and reused by both the table and health timeline, including a numeric score with consistent color classes.
- 2026-02-14: Iteration rows can now expand to lazily fetch `GET /api/projects/{id}/iterations/{n}` detail and render `log_output` in a terminal-styled panel; per-project expansion/detail caches reset when project changes.
- 2026-02-14: Expanded iteration rows now lazy-load commit diffs from `GET /api/projects/{id}/git/diff/{hash}` and render them with line-based syntax highlighting in `GitDiffViewer` (headers, hunks, additions, deletions).
- 2026-02-14: Iterations table filters now include status (`all/success/error`), health (`all/productive/partial/failed`), and text search; when searching, missing iteration logs are hydrated in small batches so log-output text becomes searchable.
- 2026-02-14: Specs UI now includes `SpecFileBrowser`, which fetches `GET /api/projects/{id}/specs`, renders a selectable sidebar list, and shows selected file metadata while reserving editor integration for phase 14.2.
