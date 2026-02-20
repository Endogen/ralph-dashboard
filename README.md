# Ralph Dashboard

A real-time web UI for monitoring, controlling, and analyzing [Ralph](https://ghuntley.com/ralph/) AI agent sessions. Ralph is a technique — in its purest form, a bash loop that feeds a prompt to an AI coding tool over and over, building software iteratively. This dashboard lets you watch it happen live — charts, iteration tracking, plan progress, log streaming, and full process control from your browser.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![React](https://img.shields.io/badge/react-19-61dafb)
![FastAPI](https://img.shields.io/badge/fastapi-0.129-009688)

## Features

### 📊 Live Overview
- **Stats grid** — tokens used, estimated cost, iterations completed, success rate, tasks done, error count
- **Progress timeline** — combined bar + line chart showing task completion and token usage per iteration
- **Task burndown** — remaining tasks over time with projected completion
- **Token usage by phase** — pie chart breaking down token spend per implementation phase
- **Iteration health timeline** — color-coded blocks showing productive / partial / failed outcomes
- **Recent activity feed** — merged stream of iteration completions, task checkoffs, errors, and notifications

### 📋 Plan Management
- **Task board** — rendered from `IMPLEMENTATION_PLAN.md` with phase progress, checkmark/hourglass status icons
- **Phase progress bars** — per-phase completion tracking with task counts
- **Raw markdown editor** — toggle to edit the plan directly with live save
- **Task metadata** — shows which iteration completed each task and links to the commit

### 🔄 Iteration Tracking
- **Sortable table** — 10 columns (#, status, health, duration, tokens, cost, tasks, commit, test)
- **Expandable log output** — click any iteration to see its full terminal output with ANSI color rendering
- **Git diff viewer** — syntax-highlighted diffs for each iteration's commit
- **Health scoring** — automatic classification of iterations as productive, partial, or failed

### 📝 Specs & Prompts
- **Browse, create, edit, delete** spec markdown files in the project's `specs/` directory
- **Side-by-side editors** for `AGENTS.md` and `PROMPT.md` directly in the Specs tab
- **Monaco editor** with markdown syntax highlighting

### 💻 Code
- **Git history** — browse recent commits with expandable syntax-highlighted diffs
- **Commit deep-linking** — plan task commit links open the Code tab at that commit

### ⚙️ Config & Injection
- **Runtime injection** — send instructions to the next loop iteration via `.ralph/inject.md`
- **Loop configuration** — edit max iterations (including unlimited), CLI tool, flags, and test commands

### 📺 Live Log Streaming
- **WebSocket-powered** real-time log output with ANSI color support
- **Virtualized rendering** — handles massive logs without DOM bloat
- **Search and filter** — find specific text or filter to errors only
- **Iteration navigation** — jump between iteration markers in the log
- **Auto-scroll** with pin/unpin toggle

### 📦 Project Archiving
- **Manual archive/unarchive** — hide inactive projects from the dashboard, restore them anytime
- **Archive page** — browse archived projects without loading iteration data
- **Auto-archive** — configurable: automatically archive projects with no activity for N days
- **Settings panel** — toggle auto-archiving and adjust the inactivity threshold

### 🎮 Process Control
- **Start / Stop / Pause / Resume** Ralph loops directly from the dashboard
- **Sticky control bar** — always-visible bottom bar with quick actions
- **Status detection** — reads `.ralph/ralph.pid` and process state in real time

### 🖥️ System Metrics
- **Loop process stats** — RAM usage (RSS), CPU %, child process count, PID monitoring
- **Server metrics** — total/used/available RAM, CPU load averages (1m/5m/15m), disk usage, uptime
- **Color-coded gauges** — green/amber/red thresholds for resource usage
- **Auto-refresh** — polls every 5 seconds with live timestamp

### 🔔 Real-Time Updates
- **WebSocket push** via filesystem watchers (watchdog + inotify)
- **Live events** — plan updates, iteration completions, status changes, log appends, notifications
- **Per-project subscriptions** — only receive events for projects you're viewing

## How Project Tracking Works

The dashboard automatically discovers and tracks Ralph Loop projects — no registration or configuration per project is needed.

### Discovery

On startup (and periodically via filesystem watchers), the dashboard scans all directories listed in `RALPH_PROJECT_DIRS` (default: `~/projects`) recursively. Any directory containing a `.ralph/` subdirectory is recognized as a Ralph Loop project.

```
~/projects/
├── my-app/              ← tracked (has .ralph/)
│   ├── .ralph/
│   ├── PROMPT.md
│   └── ...
├── some-library/        ← NOT tracked (no .ralph/)
│   └── src/
└── another-project/     ← tracked (has .ralph/)
    └── .ralph/
```

**That's all you need:** put your project under a scanned directory and make sure the Ralph Loop script has created the `.ralph/` folder. The dashboard picks it up automatically.

### What the dashboard reads

From `.ralph/`:

| File | Purpose |
|------|---------|
| `iterations.jsonl` | Structured data per iteration (timing, tokens, tasks, commits, test results) |
| `ralph.pid` | PID of the running loop process — used to detect running/stopped state |
| `ralph.log` | Human-readable log output, streamed live via WebSocket |
| `config.json` | Loop configuration (CLI tool, flags, max iterations, test command) |
| `pause` | Sentinel file — presence means the loop is paused |
| `inject.md` | Runtime instructions injected into the next iteration |
| `pending-notification.txt` | Current pending notification from the agent |

From the project root:

| File | Purpose |
|------|---------|
| `IMPLEMENTATION_PLAN.md` | Task list with completion status, parsed into an interactive board |
| `AGENTS.md` | Project context and agent instructions |
| `PROMPT.md` | The prompt template used each iteration |
| `specs/*.md` | Requirement/design spec files |

### Minimum viable setup

To get a project tracked by the dashboard, you need at minimum:

1. A project directory under one of the `RALPH_PROJECT_DIRS` paths
2. A `.ralph/` subdirectory inside it (created automatically by `ralph.sh`)

Everything else is optional — the dashboard gracefully handles missing files and shows whatever data is available.

## Architecture

```
┌──────────────────────────────────────────────┐
│  Browser (React 19 + Vite 7 + Tailwind 4)    │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐   │
│  │ Zustand  │ │ Recharts │ │   Monaco    │   │
│  │ stores   │ │ charts   │ │   editor    │   │
│  └────┬─────┘ └──────────┘ └─────────────┘   │
│       │  REST + WebSocket                    │
└───────┼──────────────────────────────────────┘
        │
┌───────┼──────────────────────────────────────┐
│  Nginx (TLS termination, reverse proxy)      │
└───────┼──────────────────────────────────────┘
        │
┌───────┼──────────────────────────────────────┐
│  FastAPI backend (uvicorn)                   │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐   │
│  │ REST API │ │ WebSocket │ │  File      │   │
│  │ routes   │ │ hub       │ │  watcher   │   │
│  └──────────┘ └───────────┘ └────────────┘   │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐   │
│  │ Plan     │ │ Iteration │ │  Git       │   │
│  │ parser   │ │ parser    │ │  service   │   │
│  └──────────┘ └───────────┘ └────────────┘   │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐   │
│  │ Process  │ │ Stats &   │ │  JWT auth  │   │
│  │ manager  │ │ projector │ │  (SQLite)  │   │
│  └──────────┘ └───────────┘ └────────────┘   │
└───────┼──────────────────────────────────────┘
        │
┌───────┼──────────────────────────────────────┐
│  Filesystem                                  │
│  ~/projects/                                 │
│    ├── my-project/                           │
│    │   ├── .ralph/                           │
│    │   │   ├── ralph.log        (log output) │
│    │   │   ├── ralph.pid        (process id) │
│    │   │   ├── iterations.jsonl (structured) │
│    │   │   ├── config.json      (loop config)│
│    │   │   └── inject.md        (runtime msg)│
│    │   ├── IMPLEMENTATION_PLAN.md            │
│    │   ├── AGENTS.md                         │
│    │   ├── PROMPT.md                         │
│    │   └── specs/*.md                        │
│    └── another-project/                      │
│        └── .ralph/ ...                       │
└──────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite 7, TypeScript 5.9, Tailwind CSS 4, shadcn/ui |
| **Charts** | Recharts 3 |
| **Editor** | Monaco Editor (via @monaco-editor/react) |
| **State** | Zustand 5 |
| **Routing** | React Router 7 |
| **Backend** | Python 3.12+, FastAPI 0.129, Uvicorn |
| **Database** | SQLite (via aiosqlite) — auth & settings only |
| **File Watching** | watchdog (inotify on Linux) |
| **Git** | GitPython |
| **Auth** | JWT (python-jose) + bcrypt (passlib) |
| **System Metrics** | psutil |
| **Reverse Proxy** | Nginx with Let's Encrypt TLS |

## Quick Start

### Prerequisites
- Python 3.12+
- Git
- Node.js 22+ (only needed when frontend assets are not pre-packaged)

### 1. Clone

```bash
git clone https://github.com/Endogen/ralph-dashboard.git
cd ralph-dashboard
```

### 2. Install

```bash
./scripts/install.sh
```

If `ralph-dashboard` is not found afterwards, ensure `~/.local/bin` is on your `PATH`.

### 3. Initialize Config + User

```bash
ralph-dashboard init
```

### 4. Run Doctor

```bash
ralph-dashboard doctor
```

### 5. Start Dashboard

Linux (systemd):
```bash
ralph-dashboard service install --user --start
```

macOS or manual mode:
```bash
set -a
source ~/.config/ralph-dashboard/env
set +a
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$RALPH_PORT"
```

Open `http://localhost:8420` (or the `RALPH_PORT` you configured) and log in.

### Development Setup (manual)

If you are developing the dashboard itself, you can still use the manual path:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd ../frontend
npm install --legacy-peer-deps

# Build frontend and package into backend/app/static/dist
cd ..
ralph-dashboard build-frontend
```

## Complete Setup Guide

A step-by-step guide to get Ralph Dashboard running from scratch on a fresh server. This covers installing the dashboard, setting up the Ralph loop script, and getting your first AI coding session monitored.

### Prerequisites

- A Linux server (Ubuntu 22.04+ recommended) or macOS
- Python 3.12+
- Node.js 22+ and npm (only needed when frontend assets are not pre-packaged)
- Git
- An AI coding CLI tool ([Codex](https://github.com/openai/codex), [Claude Code](https://github.com/anthropics/claude-code), etc.)

### Step 1: Install the Dashboard

```bash
git clone https://github.com/Endogen/ralph-dashboard.git
cd ralph-dashboard

./scripts/install.sh
```

`scripts/install.sh` will:
- create/update `backend/.venv`
- install the backend package and `ralph-dashboard` CLI
- install a wrapper into `~/.local/bin/ralph-dashboard`
- package frontend assets when available

### Step 2: Initialize Runtime Config

```bash
ralph-dashboard init
```

This interactive step configures:
- `RALPH_SECRET_KEY`
- `RALPH_PROJECT_DIRS`
- `RALPH_PORT`
- `RALPH_CREDENTIALS_FILE`
- first dashboard user credentials

### Step 3: Validate Setup

```bash
ralph-dashboard doctor
```

### Step 4: Install User Service

Linux (systemd):
```bash
ralph-dashboard service install --user --start
```

Optional commands:

```bash
ralph-dashboard service status
ralph-dashboard service logs -f
ralph-dashboard service stop
ralph-dashboard service start
```

macOS or manual mode:

```bash
set -a
source ~/.config/ralph-dashboard/env
set +a
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$RALPH_PORT"
```

Open `http://localhost:8420` (or the `RALPH_PORT` you configured) in your browser and log in.

### Step 5: Set Up Ralph Loop

The dashboard monitors projects that use a [Ralph loop](https://ghuntley.com/ralph/) — an iterative AI coding technique where a script feeds a prompt to a coding tool (Codex, Claude Code, etc.) in a loop, building software one task at a time.

The `ralph.sh` script is included in this repo at `scripts/ralph.sh`:

```bash
# Copy the loop runner somewhere convenient
cp scripts/ralph.sh ~/ralph.sh
chmod +x ~/ralph.sh
```

### Step 6: Prepare a Project

```bash
mkdir -p ~/projects/my-project
cd ~/projects/my-project

# Create the project files Ralph Loop expects
cat > AGENTS.md << 'EOF'
# My Project

## Build Commands
- Build: `npm run build`
- Test: `npm test`
- Lint: `npx eslint .`
EOF

cat > PROMPT.md << 'EOF'
You are building my-project. Read AGENTS.md for context.
Follow IMPLEMENTATION_PLAN.md for tasks.
Work on one task per iteration.
EOF

cat > IMPLEMENTATION_PLAN.md << 'EOF'
# Implementation Plan

STATUS: IN PROGRESS

## Phase 1: Setup
- [ ] 1.1: Initialize project structure
- [ ] 1.2: Add core dependencies
EOF

# Initialize git
git init && git add -A && git commit -m "initial"
```

### Step 7: Start a Ralph Loop

```bash
cd ~/projects/my-project

# Start the loop (uses Codex by default)
~/ralph.sh --max-iterations 10 --full-auto

# Or specify a different CLI tool
~/ralph.sh --cli claude --max-iterations 10 --full-auto
```

The loop creates `.ralph/` automatically. Refresh the dashboard — your project should appear in the sidebar.

### Step 8: (Optional) Production Setup

For a persistent deployment, set up a systemd service and nginx reverse proxy. See the [Production Deployment](#production-deployment) section above.

## Production Deployment

### Systemd service

Use the built-in CLI to install/update a user service:

```bash
ralph-dashboard service install --user --start
```

This writes `~/.config/systemd/user/ralph-dashboard.service`, reloads the
user daemon, enables the unit, and starts it.

If you need the service to survive logout/reboot on Linux, enable linger once:

```bash
sudo loginctl enable-linger "$USER"
```

### Nginx reverse proxy

An example config is included at `scripts/nginx/ralph.xian.technology.conf`. Copy it to `/etc/nginx/sites-available/`, adjust the domain and certificate paths, symlink to `sites-enabled`, and reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### TLS with Let's Encrypt

```bash
sudo certbot --nginx -d your.domain.com
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `RALPH_SECRET_KEY` | *(required)* | Secret key for JWT signing |
| `RALPH_PROJECT_DIRS` | `~/projects` | Comma-separated directories to scan for `.ralph/` projects |
| `RALPH_PORT` | `8420` | Backend server port |
| `RALPH_CREDENTIALS_FILE` | `~/.config/ralph-dashboard/credentials.yaml` | Path to credentials file |
| `RALPH_FRONTEND_DIST` | *(optional)* | Override frontend dist directory served by FastAPI |

## Project Structure

```
ralph-dashboard/
├── backend/                   # FastAPI backend (58 Python files)
│   ├── app/
│   │   ├── auth/              # JWT authentication & user management
│   │   ├── cli/               # `ralph-dashboard` operational CLI
│   │   ├── control/           # Process lifecycle (start/stop/pause/inject)
│   │   ├── files/             # AGENTS.md, PROMPT.md, specs CRUD
│   │   ├── git_service/       # Git log & diff via GitPython
│   │   ├── iterations/        # Log & JSONL iteration parsers
│   │   ├── notifications/     # Ralph notification file parsing
│   │   ├── plan/              # IMPLEMENTATION_PLAN.md parser
│   │   ├── projects/          # Project discovery, registration, status
│   │   ├── stats/             # Aggregation, projections, reports
│   │   ├── system/            # System & process metrics (psutil)
│   │   ├── ws/                # WebSocket hub, file watcher, event dispatcher
│   │   └── static/            # Optional packaged frontend dist for no-Node installs
│   └── tests/                 # 126 tests (pytest)
├── frontend/                  # React SPA (43 TS/TSX files)
│   └── src/
│       ├── api/               # API client with auth refresh
│       ├── components/
│       │   ├── charts/        # Recharts visualizations
│       │   ├── layout/        # Page shells, top bar, control bar
│       │   ├── project/       # Tab content components
│       │   └── ui/            # shadcn/ui primitives
│       ├── hooks/             # WebSocket hook
│       ├── lib/               # Utilities
│       ├── stores/            # Zustand state stores
│       └── types/             # TypeScript type definitions
├── scripts/
│   ├── install.sh             # One-command local installer
│   ├── package_frontend.sh    # Copies built frontend into backend static dist
│   ├── ralph.sh               # Ralph loop runner script
│   └── nginx/                 # Example nginx config
└── specs/                     # Design specification documents
```

## API Overview

All API endpoints are under `/api/` and require a Bearer JWT token (except `/api/health`, `/api/auth/login`, `/api/auth/refresh`).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/auth/login` | Login (returns access + refresh tokens) |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `GET` | `/api/projects` | List active projects (excludes archived) |
| `GET` | `/api/projects/archived` | List archived projects |
| `GET/PUT` | `/api/projects/archive/settings` | Auto-archive configuration |
| `POST` | `/api/projects/{id}/archive` | Archive a project |
| `POST` | `/api/projects/{id}/unarchive` | Unarchive a project |
| `GET` | `/api/projects/{id}` | Project detail |
| `GET` | `/api/projects/{id}/plan` | Parsed implementation plan |
| `PUT` | `/api/projects/{id}/plan` | Update plan markdown |
| `GET` | `/api/projects/{id}/iterations` | List iterations (filterable) |
| `GET` | `/api/projects/{id}/iterations/{n}` | Iteration detail with log output |
| `GET` | `/api/projects/{id}/stats` | Aggregated stats & projections |
| `GET` | `/api/projects/{id}/system` | System & process metrics |
| `GET` | `/api/projects/{id}/notifications` | Notification history |
| `GET` | `/api/projects/{id}/git/log` | Commit history |
| `GET` | `/api/projects/{id}/git/diff/{hash}` | Commit diff |
| `GET/PUT` | `/api/projects/{id}/files/{name}` | Read/write AGENTS.md or PROMPT.md |
| `GET/POST/PUT/DELETE` | `/api/projects/{id}/specs` | Spec file CRUD |
| `GET/PUT` | `/api/projects/{id}/config` | Loop configuration |
| `POST` | `/api/projects/{id}/inject` | Send runtime instruction |
| `POST` | `/api/projects/{id}/start` | Start Ralph loop |
| `POST` | `/api/projects/{id}/stop` | Stop Ralph loop |
| `POST` | `/api/projects/{id}/pause` | Pause loop |
| `POST` | `/api/projects/{id}/resume` | Resume loop |
| `WS` | `/api/ws?token=...` | WebSocket for real-time events |

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -q
```

## License

MIT
