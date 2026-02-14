# Architecture

## System Architecture

```
Browser (React SPA)
    │
    ├── REST API (CRUD, auth, files)
    │
    └── WebSocket (real-time events)
         │
    FastAPI Backend
    ├── File Watcher (watchdog) → monitors project files
    ├── Log Parser → extracts iteration data from ralph.log
    ├── Git Service → commit log, diffs
    ├── Process Manager → start/stop/pause ralph.sh
    ├── Auth → JWT + bcrypt
    └── SQLite → auth credentials + settings
         │
    Project Files (filesystem)
    ├── .ralph/ralph.log
    ├── .ralph/iterations.jsonl     ← NEW structured log
    ├── .ralph/ralph.pid            ← NEW pid tracking
    ├── .ralph/config.json          ← NEW dashboard config
    ├── .ralph/pause                ← NEW pause mechanism
    ├── .ralph/inject.md            ← NEW instruction injection
    ├── .ralph/pending-notification.txt
    ├── .ralph/last-notification.txt
    ├── IMPLEMENTATION_PLAN.md
    ├── AGENTS.md
    ├── PROMPT.md
    ├── specs/*.md
    └── .git/
```

## Data Flow

### Live Updates (Push via WebSocket)
1. `watchdog` monitors all relevant files in each registered project
2. On file change, backend parses the change:
   - `ralph.log` → extract new lines, detect iteration boundaries, parse token counts
   - `iterations.jsonl` → parse new JSON line for structured iteration data
   - `IMPLEMENTATION_PLAN.md` → re-parse checkboxes, emit progress
   - `pending-notification.txt` → parse notification, emit event
   - Other files → emit generic file_changed event
3. Parsed events broadcast to all connected WebSocket clients
4. Frontend Zustand stores update reactively

### WebSocket Event Types
```typescript
type WSEvent = 
  | { type: "iteration_started"; project: string; iteration: number; max: number }
  | { type: "iteration_completed"; project: string; data: IterationData }
  | { type: "plan_updated"; project: string; tasks_done: number; tasks_total: number; phases: Phase[] }
  | { type: "log_append"; project: string; lines: string }
  | { type: "notification"; project: string; prefix: string; message: string }
  | { type: "status_changed"; project: string; status: "running" | "paused" | "stopped" | "complete" }
  | { type: "file_changed"; project: string; file: string }
  | { type: "error"; project: string; message: string; iteration?: number }
```

### Process Management
- **Start**: Spawn `ralph.sh` as subprocess, capture PID, write `.ralph/ralph.pid`
- **Stop**: Send SIGTERM to PID, wait, SIGKILL if needed. Write notification for OpenClaw.
- **Pause**: Create `.ralph/pause` file. Ralph.sh checks between iterations.
- **Resume**: Remove `.ralph/pause` file.
- **Inject**: Write to `.ralph/inject.md`. Ralph.sh appends to AGENTS.md and deletes.

### Authentication Flow
1. User submits username + password to `POST /api/auth/login`
2. Backend validates against bcrypt hash stored in config
3. Returns JWT access token (15 min) + refresh token (7 days)
4. All API requests include `Authorization: Bearer <token>`
5. WebSocket authenticates via `?token=<access_token>` query param
6. Frontend stores tokens in localStorage, auto-refreshes

## Project Discovery
- Backend scans configured directories (default: `~/projects/`) for subdirs containing `.ralph/`
- Projects can also be manually registered by path
- Each project gets a slug ID derived from its directory name

## File Parsing

### ralph.log Iteration Extraction
Pattern per iteration:
```
[HH:MM:SS] === Iteration N/M ===
... agent output ...
tokens used
<number>
... more output ...
[HH:MM:SS] === Iteration N+1/M ===
```

Extract:
- Iteration number and max
- Start timestamp
- Token count (line after "tokens used")
- Error indicators (⚠️, ❌, crash messages)
- End timestamp (start of next iteration or EOF)

### iterations.jsonl (NEW - added by modified ralph.sh)
One JSON line per completed iteration:
```json
{"iteration":1,"max":50,"start":"2026-02-08T01:07:23+01:00","end":"2026-02-08T01:11:47+01:00","tokens":69.31,"status":"success","tasks_completed":["1.1"],"commit":"6e9b516","test_passed":true,"test_output":"33 passed","errors":[]}
```

### IMPLEMENTATION_PLAN.md Task Parsing
- `STATUS: <value>` line at top → overall status
- `## Phase N: Name` → phase headers
- `- [x] N.M: Description` → completed task
- `- [ ] N.M: Description` → pending task
- Nested tasks allowed (indented checkboxes under a parent)
