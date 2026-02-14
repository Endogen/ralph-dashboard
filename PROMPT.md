# Ralph BUILDING Loop

## Goal
Build the Ralph Dashboard — a web UI for monitoring, controlling, and analyzing Ralph Loop AI agent sessions. FastAPI backend + React frontend with real-time WebSocket updates.

## Context
- Read: specs/*.md (all 7 specification files — they are comprehensive)
- Read: IMPLEMENTATION_PLAN.md (your task list)
- Read: AGENTS.md (commands, structure, conventions, learnings)

## Rules
1. Pick the highest priority incomplete task from IMPLEMENTATION_PLAN.md
2. Investigate the relevant code BEFORE making changes
3. Implement the task completely
4. Run the backpressure commands from AGENTS.md (lint, test, build check)
5. If tests pass:
   - Commit with a clear, conventional message (feat:, fix:, refactor:, etc.)
   - Mark the task as done in IMPLEMENTATION_PLAN.md: `- [x] Task`
6. If tests fail:
   - Attempt to fix (max 3 tries per task)
   - If still failing after 3 attempts, notify for help
7. Update AGENTS.md with any operational learnings
8. Move to next task

## Important Architecture Notes
- Backend reads all project data from the filesystem (no DB for project data)
- SQLite only for auth/settings
- WebSocket uses watchdog (inotify) for file change detection → push events
- Frontend state managed by Zustand, updated via WebSocket events
- The dashboard runs on the SAME server as the Ralph loops
- Project paths are absolute filesystem paths like /home/endogen/projects/antique-catalogue
- Modified ralph.sh writes .ralph/iterations.jsonl for structured iteration data
- Token counts appear in ralph.log as a number on the line after "tokens used"

## Error Handling
If you encounter issues:
- Missing dependency: Add it to requirements.txt/package.json and install
- Unclear requirement: Check specs/ and AGENTS.md, if still unclear notify
- Repeated test failures: Notify after 3 attempts
- Blocked by external factor: Notify immediately

## Notifications
When you need input or hit milestones, write to the notification file:

```bash
mkdir -p .ralph
cat > .ralph/pending-notification.txt << 'EOF'
{"timestamp":"$(date -Iseconds)","message":"<PREFIX>: <message>","status":"pending"}
EOF
```

Prefixes:
- `DECISION:` — Need human input
- `ERROR:` — Tests failing after 3 attempts
- `BLOCKED:` — Missing something or unclear spec
- `PROGRESS:` — Major milestone complete
- `DONE:` — All tasks complete

## Completion
When ALL tasks in IMPLEMENTATION_PLAN.md are marked done:
1. Run final test suite to verify everything works
2. Add this line to IMPLEMENTATION_PLAN.md:
   ```
   STATUS: COMPLETE
   ```
3. Write completion notification
