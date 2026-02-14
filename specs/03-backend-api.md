# Backend API

## Base URL
`http://localhost:8420/api`

## Authentication

### POST /api/auth/login
Request: `{ "username": "string", "password": "string" }`
Response: `{ "access_token": "string", "refresh_token": "string", "token_type": "bearer" }`

### POST /api/auth/refresh
Request: `{ "refresh_token": "string" }`
Response: `{ "access_token": "string", "token_type": "bearer" }`

All endpoints below require `Authorization: Bearer <token>`.

## Projects

### GET /api/projects
List all discovered projects.
Response:
```json
[{
  "id": "antique-catalogue",
  "name": "antique-catalogue",
  "path": "/home/endogen/projects/antique-catalogue",
  "status": "complete",
  "current_iteration": 46,
  "max_iterations": 50,
  "tasks_done": 42,
  "tasks_total": 42,
  "total_tokens": 2150.5,
  "cli": "codex",
  "last_activity": "2026-02-08T04:48:33+01:00"
}]
```

### GET /api/projects/{id}
Full project details including config, current status, summary stats.

### POST /api/projects
Register a new project. Request: `{ "path": "/absolute/path/to/project" }`

### DELETE /api/projects/{id}
Unregister project (does NOT delete files).

## Loop Control

### POST /api/projects/{id}/start
Start the Ralph loop. Request:
```json
{
  "max_iterations": 50,
  "cli": "codex",
  "flags": "-s workspace-write",
  "test_command": "pytest"
}
```
Uses values from `.ralph/config.json` if not provided.

### POST /api/projects/{id}/stop
Stop the running loop (SIGTERM). Writes notification for OpenClaw.

### POST /api/projects/{id}/pause
Pause between iterations (creates `.ralph/pause` file).

### POST /api/projects/{id}/resume
Resume paused loop (removes `.ralph/pause` file).

### POST /api/projects/{id}/inject
Inject instructions for next iteration.
Request: `{ "message": "Use PostgreSQL instead of SQLite for the users table" }`
Writes to `.ralph/inject.md`.

## Iterations

### GET /api/projects/{id}/iterations
List all iterations with stats.
Query params: `?status=success|error|all&limit=50&offset=0`
Response:
```json
{
  "iterations": [{
    "number": 1,
    "max": 50,
    "start": "2026-02-08T01:07:23+01:00",
    "end": "2026-02-08T01:11:47+01:00",
    "duration_seconds": 264,
    "tokens": 69.31,
    "status": "success",
    "health": "productive",
    "tasks_completed": ["1.1"],
    "commit": "6e9b516",
    "commit_message": "Task 1.1: Initialize backend project",
    "test_passed": true,
    "errors": []
  }],
  "total": 46
}
```

### GET /api/projects/{id}/iterations/{n}
Single iteration with full log output.
Response includes all above fields plus:
- `log_output`: Full text between iteration markers
- `diff`: Git diff for the iteration's commit(s)

### GET /api/projects/{id}/iterations/{n}/diff
Git diff for the iteration (syntax-highlighted-ready).

## Plan

### GET /api/projects/{id}/plan
Parsed implementation plan.
Response:
```json
{
  "status": "COMPLETE",
  "raw": "STATUS: COMPLETE\n\n# Implementation Plan\n...",
  "phases": [{
    "name": "Phase 1: Backend Setup",
    "tasks": [
      { "id": "1.1", "description": "Initialize backend project", "done": true, "completed_iteration": 3, "commit": "6e9b516" },
      { "id": "1.2", "description": "Configure settings", "done": true, "completed_iteration": 4, "commit": "53b1723" }
    ]
  }],
  "tasks_done": 42,
  "tasks_total": 42
}
```

### PUT /api/projects/{id}/plan
Update the plan. Request: `{ "content": "STATUS: READY\n\n# Implementation Plan\n..." }`
Writes directly to `IMPLEMENTATION_PLAN.md`.

## Specs

### GET /api/projects/{id}/specs
List spec files. Response: `[{ "name": "01-overview.md", "size": 3975, "modified": "..." }]`

### GET /api/projects/{id}/specs/{name}
Read a spec file. Response: `{ "name": "01-overview.md", "content": "..." }`

### PUT /api/projects/{id}/specs/{name}
Update a spec file. Request: `{ "content": "..." }`

### POST /api/projects/{id}/specs
Create new spec. Request: `{ "name": "new-spec.md", "content": "..." }`

### DELETE /api/projects/{id}/specs/{name}
Delete a spec file.

## Files (AGENTS.md, PROMPT.md)

### GET /api/projects/{id}/files/{filename}
Read AGENTS.md or PROMPT.md. `filename` must be one of: `agents`, `prompt`.

### PUT /api/projects/{id}/files/{filename}
Update file content. Request: `{ "content": "..." }`

## Git

### GET /api/projects/{id}/git/log
Git commit history. Query: `?limit=50&offset=0`
Response:
```json
[{
  "hash": "6e9b516",
  "author": "Codex",
  "date": "2026-02-07T19:29:58+01:00",
  "message": "Task 1.1: Initialize backend project",
  "files_changed": 12,
  "insertions": 245,
  "deletions": 0
}]
```

### GET /api/projects/{id}/git/diff/{hash}
Diff for a specific commit. Response: `{ "hash": "...", "diff": "..." }`

## Stats

### GET /api/projects/{id}/stats
Aggregated statistics.
Response:
```json
{
  "total_iterations": 46,
  "total_tokens": 2150.5,
  "total_cost_usd": 12.45,
  "total_duration_seconds": 28800,
  "avg_iteration_duration_seconds": 626,
  "avg_tokens_per_iteration": 46.75,
  "tasks_done": 42,
  "tasks_total": 42,
  "errors_count": 3,
  "projected_completion": "2026-02-09T15:00:00+01:00",
  "projected_total_cost_usd": 15.20,
  "velocity": {
    "tasks_per_hour": 1.46,
    "tasks_remaining": 0,
    "hours_remaining": 0
  },
  "health_breakdown": {
    "productive": 38,
    "partial": 5,
    "failed": 3
  },
  "tokens_by_phase": [
    { "phase": "Phase 1: Backend Setup", "tokens": 320.5 }
  ]
}
```

## Notifications

### GET /api/projects/{id}/notifications
Notification history.
Response:
```json
[{
  "timestamp": "2026-02-08T04:48:33+01:00",
  "prefix": "DONE",
  "message": "All tasks complete",
  "iteration": 46,
  "status": "delivered",
  "triage_outcome": "notified_human"
}]
```

## Config

### GET /api/projects/{id}/config
Loop configuration.
Response:
```json
{
  "cli": "codex",
  "flags": "-s workspace-write",
  "max_iterations": 50,
  "test_command": "cd backend && .venv/bin/pytest --timeout=30",
  "model_pricing": { "codex": 0.006, "claude": 0.015 }
}
```

### PUT /api/projects/{id}/config
Update loop config. Writes to `.ralph/config.json`.

## WebSocket

### WS /api/ws?token={access_token}
Authenticated WebSocket connection for real-time events.

After connecting, client sends project subscriptions:
```json
{ "action": "subscribe", "projects": ["antique-catalogue", "ralph-dashboard"] }
```

Server pushes events (see architecture spec for event types).

## Report

### GET /api/projects/{id}/report
Generate a markdown summary report of the entire run.
Response: `{ "content": "# Project Report: antique-catalogue\n\n..." }`

### GET /api/projects/{id}/report?format=pdf
Same but as PDF download.
