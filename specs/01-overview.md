# Overview

## Goal
Build a web-based dashboard for monitoring, controlling, and analyzing Ralph Loop AI agent sessions. Provides real-time visibility into what Codex/Claude is doing, with full control over the loop lifecycle.

## Target Users
- David (primary) — software engineer running Ralph loops on xiantech server
- Monty (OpenClaw AI) — needs to be aware of start/stop events via notification files

## Deployment
- **Server**: xiantech (same machine as Ralph loops)
- **URL**: `ralph.xian.technology` (nginx reverse proxy)
- **Port**: 8420 (backend serves both API and built frontend)
- **Auth**: Username + password (JWT)

## Tech Stack

### Backend (Python)
- **FastAPI** 0.129.0 — Async web framework with native WebSocket
- **watchdog** — File system monitoring (inotify-based)
- **GitPython** — Git log/diff operations
- **python-jose** — JWT tokens
- **passlib[bcrypt]** — Password hashing
- **aiosqlite** — Async SQLite (auth + iteration cache)
- **uvicorn** — ASGI server
- **pydantic** — Data validation (comes with FastAPI)

### Frontend (TypeScript)
- **React** 19.2.x — UI framework
- **Vite** 7.3.x — Build tool
- **Tailwind CSS** 4.1.x — Utility-first CSS
- **shadcn/ui** — Component library (latest, built on Radix)
- **Recharts** 3.7.x — Charting library
- **@monaco-editor/react** 4.7.x — Code editor
- **Zustand** 5.0.x — State management
- **React Router** 7.13.x — Client-side routing
- **Lucide React** — Icons (used by shadcn)

## Key Features
1. Multi-project dashboard with status overview
2. Real-time live updates via WebSocket (push, not polling)
3. Interactive implementation plan editor
4. Specs editor (Monaco)
5. Iteration history with health scoring and git diffs
6. Progress timeline with future projections
7. Token usage and cost tracking
8. Error tracking with details
9. Loop control (start/stop/pause/resume)
10. Inject instructions mid-run
11. Configuration panel
12. Log viewer with real-time streaming
13. Notification history
14. Task burndown chart
15. Export/report generation

## Non-Goals (for now)
- Mobile app
- Multi-user collaboration
- Cloud deployment
