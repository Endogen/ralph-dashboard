STATUS: READY

# Implementation Plan

## Phase 1: Project Scaffolding
- [x] 1.1: Initialize backend (pyproject.toml, FastAPI app skeleton, directory structure, requirements.txt, venv)
- [x] 1.2: Initialize frontend (Vite + React + TypeScript, Tailwind CSS 4, shadcn/ui setup, React Router, Zustand)
- [x] 1.3: Configure Vite dev proxy to backend API (port 3420 → 8420)
- [x] 1.4: Set up backend static file serving for production (serve built frontend from FastAPI)

## Phase 2: Backend Auth
- [x] 2.1: Create config.py with Settings (project_dirs, port, secret_key, credentials file path)
- [x] 2.2: Create SQLite database setup with aiosqlite (for auth + settings storage)
- [x] 2.3: Implement JWT auth module (login, refresh, token validation, bcrypt password hashing)
- [x] 2.4: Add auth middleware/dependency for protecting endpoints
- [x] 2.5: Create initial user setup CLI command or first-run flow (set username/password)
- [x] 2.6: Add auth tests

## Phase 3: Project Discovery & Management
- [x] 3.1: Implement project discovery (scan configured dirs for .ralph/ subdirectories)
- [x] 3.2: Create project models (Pydantic) with status detection (running/paused/stopped/complete)
- [x] 3.3: Implement project registration/unregistration endpoints
- [x] 3.4: Implement GET /api/projects (list) and GET /api/projects/{id} (detail)
- [x] 3.5: Add project tests

## Phase 4: Log & Iteration Parsing
- [x] 4.1: Implement ralph.log parser (extract iterations, timestamps, token counts, errors)
- [x] 4.2: Implement iterations.jsonl parser (read structured JSON lines)
- [x] 4.3: Implement IMPLEMENTATION_PLAN.md parser (phases, tasks, checkboxes, status)
- [x] 4.4: Create iteration endpoints (GET list, GET detail with log output)
- [ ] 4.5: Create plan endpoints (GET parsed plan, PUT update plan)
- [ ] 4.6: Add parser tests (use sample data from antique-catalogue as test fixtures)

## Phase 5: File & Git Endpoints
- [ ] 5.1: Implement file read/write endpoints (AGENTS.md, PROMPT.md)
- [ ] 5.2: Implement specs CRUD endpoints (list, read, create, update, delete)
- [ ] 5.3: Implement git service (log with stats, diff for specific commits)
- [ ] 5.4: Implement git endpoints
- [ ] 5.5: Add file and git tests

## Phase 6: Stats & Notifications
- [ ] 6.1: Implement stats aggregation service (tokens, costs, velocity, projections, health breakdown)
- [ ] 6.2: Implement stats endpoint
- [ ] 6.3: Implement notification history endpoint (read pending + last notification files, plus archived)
- [ ] 6.4: Implement report generation (markdown format)
- [ ] 6.5: Add stats tests

## Phase 7: Loop Control
- [ ] 7.1: Implement process manager (start ralph.sh as subprocess, track PID)
- [ ] 7.2: Implement stop (SIGTERM/SIGKILL with grace period)
- [ ] 7.3: Implement pause/resume (create/remove .ralph/pause file)
- [ ] 7.4: Implement inject (write .ralph/inject.md)
- [ ] 7.5: Implement config read/write (.ralph/config.json)
- [ ] 7.6: Create control endpoints (start, stop, pause, resume, inject, config)
- [ ] 7.7: Add control tests

## Phase 8: WebSocket & File Watching
- [ ] 8.1: Implement WebSocket hub (connection manager, broadcast, subscriptions)
- [ ] 8.2: Implement file watcher service (watchdog observers per project)
- [ ] 8.3: Connect file watcher to log parser → emit iteration events
- [ ] 8.4: Connect file watcher to plan parser → emit plan events
- [ ] 8.5: Connect file watcher to notification/status detection → emit events
- [ ] 8.6: Implement WebSocket authentication (token validation on connect)
- [ ] 8.7: Add WebSocket tests

## Phase 9: Frontend Core Layout
- [ ] 9.1: Create app layout (sidebar + main content area + routing)
- [ ] 9.2: Build sidebar component (project list with status indicators, add project button)
- [ ] 9.3: Build top bar component (project name, status badge, quick stats)
- [ ] 9.4: Build control bar component (start/stop/pause/inject buttons)
- [ ] 9.5: Implement login page
- [ ] 9.6: Set up API client (fetch wrapper with auth token handling, auto-refresh)
- [ ] 9.7: Set up Zustand stores (auth store, projects store, active project store)
- [ ] 9.8: Set up WebSocket hook with reconnection logic

## Phase 10: Dashboard Page
- [ ] 10.1: Build project card component (status, progress bar, stats, mini health bar)
- [ ] 10.2: Build project grid layout (responsive grid of cards)
- [ ] 10.3: Build add project dialog/modal
- [ ] 10.4: Wire up real-time updates (project cards update via WebSocket)

## Phase 11: Overview Tab
- [ ] 11.1: Build status panel (large status badge, iteration, running time, CLI info)
- [ ] 11.2: Build stats grid (8 stat cards with icons)
- [ ] 11.3: Build progress timeline chart (Recharts ComposedChart: tasks area + tokens bar + projection)
- [ ] 11.4: Build task burndown chart (ideal vs actual)
- [ ] 11.5: Build token usage by phase pie chart
- [ ] 11.6: Build iteration health timeline (color-coded strip)
- [ ] 11.7: Build recent activity feed
- [ ] 11.8: Wire up real-time chart updates via WebSocket

## Phase 12: Plan Tab
- [ ] 12.1: Build plan renderer (collapsible phases, task checkboxes, status badges)
- [ ] 12.2: Implement interactive checkboxes (toggle saves to file via API)
- [ ] 12.3: Build raw markdown editor mode (Monaco with toggle)
- [ ] 12.4: Add task metadata display (completed iteration, commit link)

## Phase 13: Iterations Tab
- [ ] 13.1: Build iterations table with sortable columns
- [ ] 13.2: Build health scoring display (colored indicators)
- [ ] 13.3: Build expandable row detail (full log output, terminal-styled)
- [ ] 13.4: Build git diff viewer (syntax highlighted)
- [ ] 13.5: Add filters (status, health, search)

## Phase 14: Specs Tab
- [ ] 14.1: Build file browser sidebar (list specs/*.md files)
- [ ] 14.2: Integrate Monaco editor for spec editing
- [ ] 14.3: Implement create/delete spec file functionality
- [ ] 14.4: Add save with Ctrl+S, unsaved indicator

## Phase 15: Code Tab
- [ ] 15.1: Build side-by-side editors for AGENTS.md and PROMPT.md
- [ ] 15.2: Build inject message box with send
- [ ] 15.3: Build git log component with expandable diffs
- [ ] 15.4: Wire up save functionality

## Phase 16: Log Tab
- [ ] 16.1: Build terminal-style log viewer (dark bg, monospace, ANSI color support)
- [ ] 16.2: Implement real-time log streaming via WebSocket
- [ ] 16.3: Add auto-scroll toggle and "scroll to bottom" button
- [ ] 16.4: Add search/filter functionality
- [ ] 16.5: Implement virtualized rendering for performance (large logs)
- [ ] 16.6: Add jump-to-iteration navigation

## Phase 17: Config Tab
- [ ] 17.1: Build config form (CLI dropdown, flags, max iterations, test command)
- [ ] 17.2: Build model pricing editor section
- [ ] 17.3: Implement save to .ralph/config.json

## Phase 18: Ralph.sh Modifications
- [ ] 18.1: Add iterations.jsonl writing (structured JSON after each iteration)
- [ ] 18.2: Add pause mechanism (check .ralph/pause between iterations)
- [ ] 18.3: Add PID file management (.ralph/ralph.pid)
- [ ] 18.4: Add config.json reading
- [ ] 18.5: Add inject.md handling (append to AGENTS.md, delete)
- [ ] 18.6: Add SIGTERM handler with notification
- [ ] 18.7: Add precise iteration timing and token capture

## Phase 19: Integration & Polish
- [ ] 19.1: Set up nginx config for ralph.xian.technology reverse proxy
- [ ] 19.2: End-to-end testing with a real project (use antique-catalogue data)
- [ ] 19.3: Dark mode theming and visual polish
- [ ] 19.4: Error handling and edge cases (no data, empty projects, stale PIDs)
- [ ] 19.5: Loading states and skeleton screens
- [ ] 19.6: Toast notifications for user actions
- [ ] 19.7: Responsive layout adjustments
- [ ] 19.8: Production build configuration (backend serves frontend static files)
