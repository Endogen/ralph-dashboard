# Ralph Loop Modifications

## Overview
The existing `ralph.sh` needs several enhancements to support the dashboard. All modifications are backward-compatible — the script works fine without the dashboard.

## Modified Script Location
The modified `ralph.sh` lives at `scripts/ralph.sh` in this project. It replaces the original when the dashboard is installed. The original ralph-loop skill should also be updated.

## Modification 1: Structured Iteration Log (`iterations.jsonl`)

After each iteration completes, append a JSON line to `.ralph/iterations.jsonl`:

```json
{
  "iteration": 5,
  "max": 50,
  "start": "2026-02-08T01:23:41+01:00",
  "end": "2026-02-08T01:26:00+01:00",
  "duration_seconds": 139,
  "tokens": 62.698,
  "status": "success",
  "tasks_completed": ["1.5"],
  "commit": "abc1234",
  "commit_message": "Task 1.5: Add global exception handling",
  "test_passed": true,
  "test_output": "33 passed, 2 skipped",
  "errors": []
}
```

**Implementation:**
- Capture `ITER_START` timestamp before agent runs
- After agent finishes, capture token count from output (regex: line after "tokens used")
- Check git log for new commits since iteration start
- Parse IMPLEMENTATION_PLAN.md for newly checked tasks (diff before/after)
- Capture test results if test command configured
- Write JSON line to `iterations.jsonl`

## Modification 2: Pause Mechanism

Between iterations, after the sleep:

```bash
# Check for pause
if [[ -f "$LOG_DIR/pause" ]]; then
  log "⏸️  Paused — waiting for resume..."
  notify "PROGRESS" "Loop paused at iteration $i/$MAX_ITERS" "Waiting for .ralph/pause to be removed"
  while [[ -f "$LOG_DIR/pause" ]]; do
    sleep 2
  done
  log "▶️  Resumed"
fi
```

## Modification 3: PID File

On script start:
```bash
echo $$ > "$LOG_DIR/ralph.pid"
trap 'rm -f "$LOG_DIR/ralph.pid"; exit' EXIT INT TERM
```

The dashboard checks this PID to determine if the loop is running.

## Modification 4: Config File

Read configuration from `.ralph/config.json` if it exists (env vars still override):

```bash
if [[ -f "$LOG_DIR/config.json" ]]; then
  # Use jq or python to parse JSON
  CONFIG_CLI=$(python3 -c "import json; print(json.load(open('$LOG_DIR/config.json')).get('cli', ''))" 2>/dev/null)
  [[ -n "$CONFIG_CLI" && -z "${RALPH_CLI_SET:-}" ]] && CLI="$CONFIG_CLI"
  # ... same for flags, max_iterations, test_command
fi
```

## Modification 5: Inject File

Between iterations, check for inject file:

```bash
# Check for injection
if [[ -f "$LOG_DIR/inject.md" ]]; then
  log "💉 Injecting instructions into AGENTS.md"
  echo "" >> AGENTS.md
  echo "## Injected Instructions ($(date '+%Y-%m-%d %H:%M'))" >> AGENTS.md
  cat "$LOG_DIR/inject.md" >> AGENTS.md
  rm -f "$LOG_DIR/inject.md"
fi
```

## Modification 6: Iteration Timing

Track precise start/end times:

```bash
ITER_START=$(date -Iseconds)
# ... run agent ...
ITER_END=$(date -Iseconds)
ITER_DURATION=$(($(date -d "$ITER_END" +%s) - $(date -d "$ITER_START" +%s)))
```

## Modification 7: Token Parsing

Capture token count from agent output:

```bash
# Pipe agent output and capture
AGENT_OUTPUT=$($CMD "$(cat PROMPT.md)" 2>&1 | tee -a "$LOG_FILE")
TOKENS=$(echo "$AGENT_OUTPUT" | grep -A1 "tokens used" | tail -1 | tr -d '[:space:]')
```

## Modification 8: Task Diff Detection

Before/after comparison to detect which tasks were completed:

```bash
# Before iteration
TASKS_BEFORE=$(grep -c '^\- \[x\]' "$PLAN_FILE" 2>/dev/null || echo 0)

# ... run iteration ...

# After iteration
TASKS_AFTER=$(grep -c '^\- \[x\]' "$PLAN_FILE" 2>/dev/null || echo 0)
NEW_TASKS=$(diff <(grep '^\- \[x\]' "$PLAN_FILE.before" 2>/dev/null) <(grep '^\- \[x\]' "$PLAN_FILE" 2>/dev/null) | grep '^>' | sed 's/^> //')
```

## Modification 9: SIGTERM Handler

Graceful shutdown with notification:

```bash
cleanup() {
  log "🛑 Ralph loop stopped (signal received)"
  notify "PROGRESS" "Loop stopped at iteration ${CURRENT_ITER:-?}/$MAX_ITERS" "Stopped by signal"
  rm -f "$LOG_DIR/ralph.pid"
  exit 0
}
trap cleanup SIGTERM SIGINT
trap 'rm -f "$LOG_DIR/ralph.pid"' EXIT
```

## Backward Compatibility

All modifications check for file existence and handle gracefully:
- No `config.json`? Use env vars/defaults (existing behavior)
- No `pause` file? Skip check (existing behavior)
- No dashboard connected? `iterations.jsonl` still written (useful for later analysis)
- PID file: cleanup on exit, stale PID detection in dashboard
