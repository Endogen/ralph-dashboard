---
name: ralph-dashboard
description: Monitor and control Ralph Loop AI agent sessions via the Ralph Dashboard REST API. Use to check project status, view iterations/stats, start/stop/pause loops, inject instructions, manage plans and specs, and browse git history.
---

# Ralph Dashboard API Skill

Interact with a [Ralph Dashboard](https://github.com/Endogen/ralph-dashboard) instance to monitor and control Ralph Loop sessions.

## First-Time Installation

If the dashboard isn't running yet, follow these steps. If it's already deployed, skip to [Setup](#setup).

```bash
# 1. Clone and install
git clone https://github.com/Endogen/ralph-dashboard.git
cd ralph-dashboard

# 2. Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Frontend
cd ../frontend
npm install --legacy-peer-deps
npm run build
cd ..

# 4. Create login credentials
cd backend
.venv/bin/python -m app.auth.setup_user --username yourname
# Prompts for password. Saved to ~/.config/ralph-dashboard/credentials.yaml

# 5. Generate a secret key
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 6. Start the dashboard
export RALPH_SECRET_KEY="<your-generated-key>"
export RALPH_PROJECT_DIRS="$HOME/projects"  # directories to scan for .ralph/ projects
export RALPH_PORT=8420
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $RALPH_PORT
```

For production deployment with systemd and nginx, see the [README](https://github.com/Endogen/ralph-dashboard#production-deployment).

## Setup

To use the API, you need:
- **Base URL** of the dashboard (e.g. `https://ralph.example.com` or `http://localhost:8420`)
- **Username and password** for JWT authentication

Store credentials somewhere the agent can access them (e.g. `TOOLS.md`, env vars, or a config file). Never hardcode passwords in scripts.

## Authentication

All API endpoints (except `/api/health`, `/api/auth/login`, `/api/auth/refresh`) require a Bearer JWT token.

### Login

```bash
curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"USER","password":"PASS"}' | jq
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

Use `access_token` in all subsequent requests as `Authorization: Bearer <access_token>`.

### Refresh

When the access token expires, refresh it:

```bash
curl -s -X POST "$BASE_URL/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"eyJ..."}' | jq
```

Returns a new `access_token`.

### Auth header for all requests

```bash
TOKEN="<access_token>"
AUTH="Authorization: Bearer $TOKEN"
```

---

## API Reference

### Health Check (no auth)

```bash
curl -s "$BASE_URL/api/health" | jq
# {"status": "ok"}
```

---

### Projects

#### List all projects

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects" | jq
```

Response: array of project summaries:
```json
[
  {
    "id": "my-project",
    "name": "my-project",
    "path": "/home/user/projects/my-project",
    "status": "running"
  }
]
```

Status values: `running`, `paused`, `stopped`, `complete`.

The `id` is a slug derived from the directory name. Use it in all project-specific endpoints.

#### Get project detail

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}" | jq
```

#### Register a project manually

```bash
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects" \
  -d '{"path":"/path/to/project"}' | jq
```

The project directory must contain a `.ralph/` subdirectory.

#### Unregister a project

```bash
curl -s -X DELETE -H "$AUTH" "$BASE_URL/api/projects/{id}"
```

---

### Iterations

#### List iterations

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/iterations?status=all&limit=50&offset=0" | jq
```

Query params:
- `status`: `all` (default), `success`, `error`
- `limit`: 1–500 (default 50)
- `offset`: pagination offset

Response:
```json
{
  "iterations": [
    {
      "number": 5,
      "max_iterations": 50,
      "start_timestamp": "2026-02-08T01:23:41+01:00",
      "end_timestamp": "2026-02-08T01:26:00+01:00",
      "duration_seconds": 139,
      "tokens_used": 62.698,
      "status": "success",
      "has_errors": false,
      "errors": [],
      "tasks_completed": ["1.5"],
      "commit": "abc1234",
      "test_passed": true
    }
  ],
  "total": 15
}
```

#### Get iteration detail (includes log output)

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/iterations/{number}" | jq
```

Returns the same fields as above plus `log_output` (string with full terminal output for that iteration).

---

### Stats

#### Get aggregated project stats

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/stats" | jq
```

Response:
```json
{
  "total_iterations": 15,
  "total_tokens": 940.5,
  "total_cost_usd": 5.64,
  "total_duration_seconds": 2100,
  "avg_iteration_duration_seconds": 140,
  "avg_tokens_per_iteration": 62.7,
  "tasks_done": 12,
  "tasks_total": 18,
  "errors_count": 2,
  "projected_completion": "2026-02-08T04:00:00+01:00",
  "projected_total_cost_usd": 8.46,
  "velocity": {
    "tasks_per_hour": 3.4,
    "tasks_remaining": 6,
    "hours_remaining": 1.76
  },
  "health_breakdown": {
    "productive": 12,
    "partial": 1,
    "failed": 2
  },
  "tokens_by_phase": [
    {"phase": "Phase 1: Core", "tokens": 450.2}
  ]
}
```

#### Get project report (markdown summary)

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/report" | jq -r '.content'
```

Returns a human-readable markdown report of the project's progress.

---

### System Metrics

#### Get system and process metrics

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/system" | jq
```

Response:
```json
{
  "process": {
    "pid": 12345,
    "rss_mb": 85.2,
    "children_rss_mb": 312.4,
    "total_rss_mb": 397.6,
    "cpu_percent": 12.5,
    "child_count": 3
  },
  "system": {
    "ram_total_mb": 16384.0,
    "ram_used_mb": 8192.0,
    "ram_available_mb": 8192.0,
    "ram_percent": 50.0,
    "cpu_load_1m": 1.2,
    "cpu_load_5m": 0.8,
    "cpu_load_15m": 0.6,
    "cpu_core_count": 8,
    "disk_total_gb": 500.0,
    "disk_used_gb": 120.0,
    "disk_free_gb": 380.0,
    "disk_percent": 24.0,
    "uptime_seconds": 864000.0
  }
}
```

Process metrics are gathered from the PID in `.ralph/ralph.pid`. If the loop isn't running, `process.pid` is `null` and memory/CPU values are `0`.

---

### Implementation Plan

#### Get parsed plan

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/plan" | jq
```

Returns the parsed `IMPLEMENTATION_PLAN.md` with phases, tasks, completion status.

#### Update plan

```bash
curl -s -X PUT -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects/{id}/plan" \
  -d '{"content":"# Implementation Plan\n\n## Phase 1\n- [ ] Task 1\n- [x] Task 2\n"}' | jq
```

---

### Loop Control

#### Start a loop

```bash
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects/{id}/start" \
  -d '{"max_iterations":50,"cli":"codex","flags":"--full-auto","test_command":"pytest"}' | jq
```

All fields are optional — defaults come from `.ralph/config.json`.

Response:
```json
{
  "project_id": "my-project",
  "pid": 12345,
  "command": ["./scripts/ralph.sh", "50"]
}
```

#### Stop a loop

```bash
curl -s -X POST -H "$AUTH" "$BASE_URL/api/projects/{id}/stop" | jq
# {"stopped": true}
```

#### Pause a loop

```bash
curl -s -X POST -H "$AUTH" "$BASE_URL/api/projects/{id}/pause" | jq
# {"paused": true}
```

#### Resume a loop

```bash
curl -s -X POST -H "$AUTH" "$BASE_URL/api/projects/{id}/resume" | jq
# {"resumed": true}
```

#### Inject instructions into next iteration

```bash
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects/{id}/inject" \
  -d '{"message":"Use async SQLAlchemy sessions instead of sync"}' | jq
```

The message is written to `.ralph/inject.md` and automatically appended to `AGENTS.md` at the start of the next iteration.

---

### Loop Configuration

#### Read config

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/config" | jq
```

Response:
```json
{
  "cli": "codex",
  "flags": "--full-auto",
  "max_iterations": 20,
  "test_command": "pytest",
  "model_pricing": {"codex": 0.006, "claude": 0.015}
}
```

#### Update config

```bash
curl -s -X PUT -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects/{id}/config" \
  -d '{"cli":"claude","flags":"--dangerously-skip-permissions","max_iterations":30,"test_command":"pytest -q","model_pricing":{"claude":0.015}}' | jq
```

---

### Project Files

#### Read AGENTS.md or PROMPT.md

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/files/agents" | jq
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/files/prompt" | jq
```

Response:
```json
{"name": "AGENTS.md", "content": "# AGENTS.md\n..."}
```

#### Update AGENTS.md or PROMPT.md

```bash
curl -s -X PUT -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects/{id}/files/agents" \
  -d '{"content":"# AGENTS.md\n\nUpdated content..."}' | jq
```

---

### Spec Files

#### List specs

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/specs" | jq
```

Response:
```json
[
  {"name": "overview.md", "size": 1234, "modified": "2026-02-08T01:00:00"}
]
```

#### Read a spec

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/specs/{name}" | jq
```

#### Create a spec

```bash
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects/{id}/specs" \
  -d '{"name":"auth.md","content":"# Auth Spec\n..."}' | jq
```

#### Update a spec

```bash
curl -s -X PUT -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects/{id}/specs/{name}" \
  -d '{"content":"# Updated spec\n..."}' | jq
```

#### Delete a spec

```bash
curl -s -X DELETE -H "$AUTH" "$BASE_URL/api/projects/{id}/specs/{name}"
```

---

### Git History

#### Commit log

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/git/log?limit=20&offset=0" | jq
```

#### Commit diff

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/git/diff/{commit_hash}" | jq
```

---

### Notifications

#### Get notification history

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/{id}/notifications" | jq
```

Response:
```json
[
  {
    "timestamp": "2026-02-08T02:30:00+01:00",
    "prefix": "DONE",
    "message": "All tasks complete.",
    "status": "delivered",
    "iteration": 15,
    "details": null,
    "source": "pending-notification.txt"
  }
]
```

---

## Common Workflows

### Check if any loops are running

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects" | jq '[.[] | select(.status == "running")]'
```

### Get a quick status overview of a project

```bash
# Project status + stats in two calls
PROJECT_ID="my-project"
curl -s -H "$AUTH" "$BASE_URL/api/projects/$PROJECT_ID" | jq
curl -s -H "$AUTH" "$BASE_URL/api/projects/$PROJECT_ID/stats" | jq '{tasks: "\(.tasks_done)/\(.tasks_total)", iterations: .total_iterations, cost: .total_cost_usd, velocity: .velocity.tasks_per_hour, errors: .errors_count}'
```

### Inject a decision into a running loop

When the agent asks a question (DECISION/QUESTION notification), answer it:

```bash
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  "$BASE_URL/api/projects/$PROJECT_ID/inject" \
  -d '{"message":"Decision: Use PostgreSQL instead of SQLite for the database layer."}' | jq
```

### Get the latest iteration's log output

```bash
# Get total iterations, then fetch the last one
TOTAL=$(curl -s -H "$AUTH" "$BASE_URL/api/projects/$PROJECT_ID/iterations?limit=1" | jq '.total')
curl -s -H "$AUTH" "$BASE_URL/api/projects/$PROJECT_ID/iterations/$TOTAL" | jq -r '.log_output'
```

### Generate a progress report

```bash
curl -s -H "$AUTH" "$BASE_URL/api/projects/$PROJECT_ID/report" | jq -r '.content'
```

---

## Project Discovery

The dashboard automatically discovers projects by scanning configured directories (default: `~/projects`) for any subdirectory containing `.ralph/`. No manual registration is needed — just ensure your project has a `.ralph/` directory and lives under a scanned path.

Projects can also be registered manually via the API if they live outside the scanned directories.

## Notes

- **Project IDs** are slug-ified directory names (e.g. `my-project` from `~/projects/my-project/`)
- **Token counts** are in thousands (k-tokens) as reported by the CLI tools
- **WebSocket** endpoint at `/api/ws?token=<access_token>` provides real-time events (iteration completions, plan updates, log appends, status changes) — useful for live monitoring but not covered here since agents typically poll
- All timestamps are ISO 8601 with timezone
