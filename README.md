# Ralph Dashboard

A real-time web UI for monitoring, controlling, and analyzing [Ralph Loop](https://github.com/Endogen/ralph-loop) AI agent sessions. Watch your AI coding agents build software — live charts, iteration tracking, plan progress, log streaming, and full process control from your browser.

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

### 📝 Spec Files
- **Browse, create, edit, delete** spec markdown files in the project's `specs/` directory
- **Monaco editor** with markdown syntax highlighting

### 💻 Code & Config
- **Side-by-side editors** for `AGENTS.md` and `PROMPT.md` with save
- **Runtime injection** — send instructions to the next loop iteration via `.ralph/inject.md`
- **Git history** — browse recent commits with expandable syntax-highlighted diffs
- **Loop configuration** — edit max iterations, CLI tool, flags, and test commands

### 📺 Live Log Streaming
- **WebSocket-powered** real-time log output with ANSI color support
- **Virtualized rendering** — handles massive logs without DOM bloat
- **Search and filter** — find specific text or filter to errors only
- **Iteration navigation** — jump between iteration markers in the log
- **Auto-scroll** with pin/unpin toggle

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
- Node.js 22+

### 1. Clone

```bash
git clone https://github.com/Endogen/ralph-dashboard.git
cd ralph-dashboard
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run build
```

### 4. Create credentials

```bash
cd backend
.venv/bin/python -m app.auth.setup_user --username yourname
```

You'll be prompted for a password. Credentials are stored in `~/.config/ralph-dashboard/credentials.yaml`.

### 5. Run

```bash
# Set required environment variables
export RALPH_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
export RALPH_PROJECT_DIRS=/path/to/your/projects  # directory containing Ralph Loop projects
export RALPH_PORT=8420

# Start the server
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $RALPH_PORT
```

Open `http://localhost:8420` and log in.

## Complete Setup Guide

A step-by-step guide to get Ralph Dashboard running from scratch on a fresh server. This covers installing the dashboard, setting up [Ralph Loop](https://github.com/Endogen/ralph-loop), and getting your first AI coding session monitored.

### Prerequisites

- A Linux server (Ubuntu 22.04+ recommended) or macOS
- Python 3.12+
- Node.js 22+ and npm
- Git
- An AI coding CLI tool ([Codex](https://github.com/openai/codex), [Claude Code](https://github.com/anthropics/claude-code), etc.)

### Step 1: Install the Dashboard

```bash
# Clone the repository
git clone https://github.com/Endogen/ralph-dashboard.git
cd ralph-dashboard

# Set up the backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Build the frontend
cd ../frontend
npm install --legacy-peer-deps
npm run build
cd ..
```

### Step 2: Create Login Credentials

```bash
cd backend
.venv/bin/python -m app.auth.setup_user --username yourname
# You'll be prompted for a password
# Credentials are saved to ~/.config/ralph-dashboard/credentials.yaml
```

### Step 3: Generate a Secret Key

```bash
# Generate a secure key for JWT signing
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# Save this — you'll need it for the environment config
```

### Step 4: Configure and Start

```bash
# Set environment variables
export RALPH_SECRET_KEY="your-generated-secret-key"
export RALPH_PROJECT_DIRS="$HOME/projects"  # where your coding projects live
export RALPH_PORT=8420

# Start the dashboard
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $RALPH_PORT
```

Open `http://localhost:8420` in your browser and log in.

### Step 5: Set Up Ralph Loop

The dashboard monitors projects that use [Ralph Loop](https://github.com/Endogen/ralph-loop) — an AI coding loop runner that manages iterative coding sessions with tools like Codex or Claude Code.

```bash
# Get ralph.sh (the loop runner)
curl -o ~/ralph.sh https://raw.githubusercontent.com/Endogen/ralph-loop/main/ralph.sh
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

Create `/etc/systemd/system/ralph-dashboard.service`:

```ini
[Unit]
Description=Ralph Dashboard
After=network.target

[Service]
Type=simple
User=youruser
Group=youruser
WorkingDirectory=/path/to/ralph-dashboard/backend
Environment=RALPH_SECRET_KEY=your-secret-key-here
Environment=RALPH_PROJECT_DIRS=/path/to/projects
Environment=RALPH_PORT=8420
ExecStart=/path/to/ralph-dashboard/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8420
Restart=on-failure
RestartSec=5
MemoryMax=512M
MemoryHigh=384M

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now ralph-dashboard
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

## Project Structure

```
ralph-dashboard/
├── backend/                   # FastAPI backend (58 Python files)
│   ├── app/
│   │   ├── auth/              # JWT authentication & user management
│   │   ├── control/           # Process lifecycle (start/stop/pause/inject)
│   │   ├── files/             # AGENTS.md, PROMPT.md, specs CRUD
│   │   ├── git_service/       # Git log & diff via GitPython
│   │   ├── iterations/        # Log & JSONL iteration parsers
│   │   ├── notifications/     # Ralph notification file parsing
│   │   ├── plan/              # IMPLEMENTATION_PLAN.md parser
│   │   ├── projects/          # Project discovery, registration, status
│   │   ├── stats/             # Aggregation, projections, reports
│   │   ├── system/            # System & process metrics (psutil)
│   │   └── ws/                # WebSocket hub, file watcher, event dispatcher
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
│   ├── ralph.sh               # Ralph loop runner (copy from ralph-loop repo)
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
| `GET` | `/api/projects` | List all discovered projects |
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

All 126 tests should pass.

## License

MIT
