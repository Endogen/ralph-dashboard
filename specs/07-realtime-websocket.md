# Real-Time Updates & WebSocket

## Architecture

### Server-Side
1. **File Watcher** (`watchdog` library) monitors project directories
2. On file change → parser extracts meaningful data
3. Parsed events → broadcast to WebSocket hub
4. WebSocket hub → sends to all subscribed clients

### Client-Side
1. On page load → establish WebSocket connection
2. Send subscription message with project IDs
3. Receive events → update Zustand store → React re-renders

## File Watcher Configuration

Per registered project, watch these paths:

| Path | Parser | Events Generated |
|------|--------|-----------------|
| `.ralph/ralph.log` | Log line parser | `log_append`, `iteration_started`, `iteration_completed` |
| `.ralph/iterations.jsonl` | JSON line parser | `iteration_completed` (structured) |
| `.ralph/pending-notification.txt` | JSON parser | `notification` |
| `.ralph/ralph.pid` | PID checker | `status_changed` |
| `.ralph/pause` | Existence check | `status_changed` (paused/resumed) |
| `IMPLEMENTATION_PLAN.md` | Markdown parser | `plan_updated` |
| `AGENTS.md` | Hash change | `file_changed` |
| `PROMPT.md` | Hash change | `file_changed` |
| `specs/*` | Hash change | `file_changed` |

### Debouncing
- File changes debounced at 500ms (files may be written in chunks)
- Log file: special handling — tail new lines immediately, parse after 200ms idle

### Efficient Log Tailing
- Track file position (byte offset) per project
- On modify event, read only new bytes from last position
- Parse new lines for iteration markers, token counts, errors
- Buffer partial lines (log writes may not be line-aligned)

## WebSocket Protocol

### Connection
```
WS /api/ws?token={jwt_access_token}
```

### Client → Server Messages

**Subscribe to projects:**
```json
{ "action": "subscribe", "projects": ["antique-catalogue", "ralph-dashboard"] }
```

**Unsubscribe:**
```json
{ "action": "unsubscribe", "projects": ["antique-catalogue"] }
```

**Ping (keepalive):**
```json
{ "action": "ping" }
```

### Server → Client Messages

All events have this envelope:
```json
{
  "type": "<event_type>",
  "project": "<project_id>",
  "timestamp": "<ISO-8601>",
  "data": { ... }
}
```

**Event: iteration_started**
```json
{
  "type": "iteration_started",
  "project": "antique-catalogue",
  "timestamp": "2026-02-08T01:23:41+01:00",
  "data": {
    "iteration": 5,
    "max": 50
  }
}
```

**Event: iteration_completed**
```json
{
  "type": "iteration_completed",
  "project": "antique-catalogue",
  "timestamp": "2026-02-08T01:26:00+01:00",
  "data": {
    "iteration": 5,
    "max": 50,
    "duration_seconds": 139,
    "tokens": 62.698,
    "status": "success",
    "health": "productive",
    "tasks_completed": ["1.5"],
    "commit": "abc1234",
    "test_passed": true,
    "errors": []
  }
}
```

**Event: plan_updated**
```json
{
  "type": "plan_updated",
  "project": "antique-catalogue",
  "timestamp": "...",
  "data": {
    "tasks_done": 30,
    "tasks_total": 42,
    "phases": [
      { "name": "Phase 1: Backend Setup", "done": 5, "total": 5, "status": "complete" },
      { "name": "Phase 2: Backend Auth", "done": 7, "total": 7, "status": "complete" },
      { "name": "Phase 3: Backend Collections", "done": 3, "total": 4, "status": "in_progress" }
    ]
  }
}
```

**Event: log_append**
```json
{
  "type": "log_append",
  "project": "antique-catalogue",
  "timestamp": "...",
  "data": {
    "lines": "[01:26:00] Running: codex exec ...\nOpenAI Codex v0.98.0...\n"
  }
}
```

**Event: notification**
```json
{
  "type": "notification",
  "project": "antique-catalogue",
  "timestamp": "...",
  "data": {
    "prefix": "ERROR",
    "message": "Tests failing after 3 attempts on task 5.3",
    "iteration": 15,
    "details": "..."
  }
}
```

**Event: status_changed**
```json
{
  "type": "status_changed",
  "project": "antique-catalogue",
  "timestamp": "...",
  "data": {
    "status": "paused",
    "previous": "running"
  }
}
```

**Event: file_changed**
```json
{
  "type": "file_changed",
  "project": "antique-catalogue",
  "timestamp": "...",
  "data": {
    "file": "AGENTS.md"
  }
}
```

**Pong:**
```json
{ "type": "pong" }
```

## Frontend WebSocket Integration

### Zustand Store
```typescript
interface WebSocketStore {
  connected: boolean;
  reconnecting: boolean;
  connect: (token: string) => void;
  disconnect: () => void;
  subscribe: (projects: string[]) => void;
}
```

### Reconnection Strategy
- On disconnect: attempt reconnect after 1s, 2s, 4s, 8s, 16s, 30s (exponential backoff, max 30s)
- Show "Connection lost, reconnecting..." banner
- On reconnect: re-subscribe to projects + fetch full state (to catch missed events)
- On token expiry during reconnect: redirect to login

### State Hydration on Reconnect
After reconnecting, fetch current state for all subscribed projects:
1. `GET /api/projects` (list with summaries)
2. For each open project: fetch iterations, plan, stats
3. Merge with store (WebSocket events resume for future updates)
