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
