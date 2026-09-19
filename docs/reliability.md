# Reliability and workflow contracts

The dashboard and `ralph-loop` use the same packaged Python runner and `LoopConfig` model. `scripts/ralph.sh` remains the source-checkout entry point. Python 3.12+ and the backend dependencies are required; run `scripts/install.sh` before using it.

## Run lifecycle

- Startup validates the repository, prompt, configuration and agent executable. The API waits for a runner state record before reporting success.
- A lifetime file lock prevents duplicate runners. Process identity includes the PID and process birth time. Stop captures the process group before sending TERM, then escalates against the captured group even if its leader exits.
- Pause takes effect between iterations. Stop interrupts the current agent/test process. The next run continues iteration numbering.
- The runner owns `ralph.log`. Output arrives incrementally; bounded in-memory tails are retained for error reporting. `launcher.log` contains startup failures.
- Every attempted iteration, including provider limits, produces a JSONL record. Completion requires an exact plan marker, a successful agent result and passing configured tests. If no test command is configured, completion does not imply independent test verification.
- Each record stores provider/model, raw usage, cost when provided, and the estimated price used at the time. The legacy `tokens` field remains measured in thousands for compatibility. Old records without usage/cost cannot recover an exact historical bill; their estimates use the legacy baseline.

## Permissions

Restricted Codex runs use the workspace-write sandbox. Restricted Claude runs use `acceptEdits`: project file edits and common filesystem operations are allowed, while other actions follow configured permission rules. Headless runs deny actions that require an interactive decision. See [Claude permission modes](https://code.claude.com/docs/en/permission-modes) and [programmatic usage](https://code.claude.com/docs/en/headless). Claude permission rules are not an OS sandbox. Full access is an explicit setting. Existing configurations with explicit unrestricted flags migrate to full access; an explicit restricted setting takes precedence.

The wizard generates text in a temporary working directory with restricted/read-only tooling. Existing project context is limited to the repository's README, agent instructions, plan and common package manifests. It cannot edit the selected repository during generation. The confirmation screen previews files that will be replaced. File versions are checked again when applying the preview.

New projects are staged and published before discovery/watchers refresh. Git initialization is required; the optional initial commit is skipped with a logged warning if Git identity is unavailable. Existing projects must be stopped before preparation; writes are atomic per file and rolled back on failure. Browser plan, prompt, agent and spec edits use ETags and reject stale saves with HTTP 412.

## Live data and history

Watchers coalesce changes without dropping their final read. Bounded log reads advance by bytes consumed. The log API provides a cursor and generation identifier; the UI reconciles that cursor on updates and periodically after reconnects. The UI retains the most recent 2 MB in its log viewport. Historical iteration details remain available separately.

There is one application websocket. Authentication is the first message, so credentials do not appear in URLs. Reconnection refreshes expired access tokens. Wizard request IDs survive navigation/reload, allowing polling and cancellation to resume. Generation jobs are limited to four concurrent requests and retained for 30 minutes; restarting the server cancels them and the UI offers regeneration.

The dashboard uses one overview request, and iteration parsing is cached by file version. History is paginated without a 500-record cutoff. Cumulative charts sample their computed points to limit rendering cost. Pages and the locally hosted editor load on demand. CI limits initial JavaScript to 350 KiB. Monaco remains a larger optional download (about 2.7 MB before compression), fetched only when an editor opens.

## Deployment

`RALPH_SECRET_KEY` is required and must contain at least 32 characters. Generate it with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. Store it outside Git. Existing installations using the old default must configure a fresh key and sign in again.

For Docker, create a local `.env` containing `RALPH_SECRET_KEY` and an absolute `RALPH_HOST_PROJECT_DIR`. On Linux set `RALPH_UID` and `RALPH_GID` to your host user/group IDs so the container can write the bind-mounted projects. Then:

```sh
docker compose build
docker compose run --rm ralph-dashboard ralph-dashboard-init-user
docker compose run --rm ralph-dashboard codex login --device-auth
# Or authenticate Claude in the persistent agent home:
docker compose run --rm ralph-dashboard claude auth login
docker compose up -d
```

The image runs as an unprivileged user and includes pinned Codex and Claude CLIs plus the packaged runner. Dashboard data and agent authentication have separate persistent volumes. Project build tools beyond Python/Node/Git must be installed in a derived image as needed by the project.

Source installs always run `npm ci` and rebuild the frontend. Use Node 22 LTS. Service installation records the current PATH so installed CLIs remain available to launchd/systemd.

## Validation

Run `python -m pytest -q backend/tests`, `ruff check backend/app backend/tests`, and `npm run lint && npm test && npm run build` in `frontend`. The Python tests include actual subprocess trees and shell entry points, plus an HTTP/WebSocket workflow using a fake agent. `scripts/smoke_container.sh IMAGE` exercises the installed image and both CLI binaries without calling paid providers.

CI runs backend checks on Linux/macOS, frontend checks and an installed-container smoke test. The frontend lockfile includes patched dependency versions; a DOMPurify patch override keeps Monaco's pinned transitive dependency outside known vulnerable ranges. No audit findings are suppressed.
