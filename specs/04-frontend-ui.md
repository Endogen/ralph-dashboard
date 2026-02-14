# Frontend UI

## Layout

### Global Structure
```
┌─────────────────────────────────────────────────────┐
│  Sidebar (collapsible)  │  Main Content Area         │
│  ┌───────────────────┐  │  ┌────────────────────┐   │
│  │ 🐺 Ralph Dashboard│  │  │ Top Bar            │   │
│  │                   │  │  │ Project + Status    │   │
│  │ Projects:         │  │  ├────────────────────┤   │
│  │ 🟢 antique-cat.   │  │  │                    │   │
│  │ ⏸️ ralph-dash.     │  │  │  Tab Content       │   │
│  │ ⏹️ my-api          │  │  │                    │   │
│  │                   │  │  │                    │   │
│  │ + Add Project     │  │  │                    │   │
│  └───────────────────┘  │  ├────────────────────┤   │
│                          │  │ Control Bar        │   │
│                          │  │ [Start][Pause][Stop]│   │
│                          │  └────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Sidebar
- App logo/name at top
- List of registered projects with status indicators:
  - 🟢 Running (green dot, pulsing)
  - ⏸️ Paused (yellow dot)
  - ⏹️ Stopped (gray dot)
  - ✅ Complete (green checkmark)
  - ❌ Error (red dot)
- Each project shows: name, progress bar (mini), iteration count
- "Add Project" button at bottom
- Collapsible (icon-only mode on narrow screens)

### Top Bar
- Current project name
- Status badge (running/paused/stopped/complete)
- Current iteration badge: "Iteration 15/50"
- Running time: "Running for 2h 14m"
- Quick stats: tokens used, cost estimate

### Control Bar (bottom, sticky)
- **Start** button (green) — starts the loop with current config
- **Pause/Resume** toggle (yellow/green)
- **Stop** button (red) — with confirmation dialog
- **Inject** text input + send button
- Status text: "Iteration 15/50 — Running for 2h 14m — 1,245 tokens"

## Pages

### 1. Dashboard (Multi-Project Overview)
Route: `/`

Grid layout of project cards. Each card contains:
- Project name
- Status badge
- Progress bar with percentage
- Current iteration / max
- Total tokens used
- Estimated cost ($)
- Last activity time (relative: "2 hours ago")
- Mini health bar (colored strip showing iteration health)
- Click → navigates to project detail

Empty state: Illustration + "No projects yet. Add a project to get started."

### 2. Login Page
Route: `/login`
- Simple centered form: username, password, login button
- Error display on wrong credentials
- Redirects to dashboard on success

### 3. Project Detail
Route: `/project/:id`

Tabbed interface with 7 tabs:

#### Tab: Overview
Main monitoring view. Components:

**Status Panel** (top, full width)
- Large status badge
- Current iteration / max
- Running time
- CLI being used (codex/claude)
- Mode (PLANNING/BUILDING)

**Stats Grid** (2 rows × 4 columns)
- Total tokens used
- Estimated cost ($)
- Iterations completed
- Average iteration duration
- Tasks completed / total
- Error count
- Success rate (%)
- Projected completion time

**Progress Timeline Chart** (large, full width)
- X-axis: Time (from first iteration to projected completion)
- Left Y-axis: Cumulative tasks completed (area fill, blue)
- Right Y-axis: Tokens per iteration (bars, purple)
- Projection dashed line extending to estimated completion
- Error markers: Red dots where errors occurred
- Hover tooltip: iteration details
- Built with Recharts ComposedChart

**Task Burndown Chart** (half width)
- Tasks remaining over time
- Ideal burndown line (straight diagonal)
- Actual progress line
- Shows if ahead/behind schedule

**Token Usage by Phase** (half width, pie chart)
- Tokens grouped by implementation plan phases
- Hover shows exact values

**Iteration Health Timeline** (full width, compact)
- Horizontal bar: one cell per iteration
- Color: 🟢 productive, 🟡 partial, 🔴 failed
- Click cell → jump to iteration detail

**Recent Activity Feed** (sidebar or below charts)
- Last 10-15 events
- Types: iteration completed, error occurred, task marked done, notification received
- Timestamp + description
- Click → navigate to relevant detail

#### Tab: Plan
Interactive implementation plan editor.

**Layout:**
- Left: Rendered plan view (phases, tasks with checkboxes)
- Right: Raw markdown editor (Monaco, toggleable)

**Rendered View:**
- Phases as collapsible accordion sections
- Each phase shows: name, progress bar, X/Y tasks
- Tasks with interactive checkboxes
- Task metadata on hover/click:
  - Which iteration completed it
  - Git commit link
  - Time spent (if available)
- Status badges per phase (complete ✅, in progress 🔄, pending ⏳)
- Phase sections auto-collapse when complete

**Editor Mode (toggle):**
- Full Monaco editor with markdown syntax highlighting
- Save button → writes to IMPLEMENTATION_PLAN.md
- Live preview pane (optional, split view)

#### Tab: Iterations
Table of all iterations.

**Table Columns:**
| # | Status | Health | Duration | Tokens | Cost | Tasks | Commit | Test |
|---|--------|--------|----------|--------|------|-------|--------|------|

- **Status**: ✅ success, ⚠️ warning, ❌ error
- **Health**: 🟢 productive, 🟡 partial, 🔴 failed
- **Duration**: "2m 34s"
- **Tokens**: "69.3"
- **Cost**: "$0.42"
- **Tasks**: "1.1, 1.2" (tasks completed in this iteration)
- **Commit**: Short hash, clickable
- **Test**: ✅/❌ or N/A

**Filters:**
- Status dropdown (All, Success, Error)
- Health dropdown (All, Productive, Partial, Failed)
- Search in log output

**Expandable Row Detail:**
- Full iteration log output (terminal-styled)
- Git diff viewer (syntax highlighted, side-by-side or unified)
- Token breakdown
- Error details (if any)

#### Tab: Specs
Spec file manager.

**Layout:**
- Left sidebar: file list (specs/*.md)
- Right: Monaco editor with selected file

**Features:**
- Click file to open in editor
- Create new file button
- Delete file (with confirmation)
- Save button (Ctrl+S shortcut)
- Unsaved changes indicator (dot on tab)
- Markdown syntax highlighting

#### Tab: Code
AGENTS.md and PROMPT.md editors + injection + git.

**Layout:**
- **Top section**: Two side-by-side Monaco editors
  - Left: AGENTS.md
  - Right: PROMPT.md
  - Both with save buttons

- **Middle section**: Inject box
  - Text area: "Inject instructions for next iteration..."
  - Send button
  - Shows last injection if any

- **Bottom section**: Git log
  - Scrollable list of commits
  - Each commit: hash, date, message, files changed count
  - Click to expand → show diff (syntax highlighted)

#### Tab: Log
Real-time log viewer.

**Features:**
- Terminal-style display (dark bg, monospace font, colored output)
- Auto-scroll (toggleable with pin button)
- Iteration markers highlighted/navigable (jump to iteration N)
- Search bar (Ctrl+F)
- Filter: show all, errors only, by iteration range
- Line numbers
- Copy selection
- "Scroll to bottom" button when not following

**Performance:**
- Virtualized rendering (only visible lines in DOM)
- Buffer last N lines (configurable, default 10000)
- New lines pushed via WebSocket in real-time

#### Tab: Config
Loop configuration form.

**Fields:**
- CLI: Dropdown (codex, claude, opencode, goose)
- CLI Flags: Text input (default auto-detected)
- Max Iterations: Number input (1-999)
- Test Command: Text input
- Project Directory: Read-only display with copy button

**Model Pricing Section:**
- Table of model prices per 1K tokens
- Editable (for cost calculation accuracy)

**Save button** → writes `.ralph/config.json`

**Note:** Changes take effect on next loop start (or next iteration if config hot-reload is supported).

## Theme
- **Dark mode** by default (respects system preference, toggle available)
- shadcn/ui default theme with customizations:
  - Primary: Blue (#3B82F6)
  - Success: Green (#22C55E)
  - Warning: Yellow (#EAB308)
  - Error: Red (#EF4444)
  - Background: Dark gray (#09090B for dark, white for light)
- Clean, minimal design with proper spacing
- Responsive: works on tablet, degrades gracefully on mobile

## Interactions & UX

### Loading States
- Skeleton screens for initial data load
- Spinner overlays for actions (start/stop/save)
- Optimistic updates where safe (checkbox toggles)

### Error Handling
- Toast notifications for action results (success/error)
- Form validation with inline error messages
- Connection lost banner for WebSocket disconnection
- Auto-reconnect for WebSocket with exponential backoff

### Keyboard Shortcuts
- `Ctrl+S` — Save current editor
- `Ctrl+K` — Quick search/command palette (optional)
- `Esc` — Close modals/dialogs
- `1-7` — Switch tabs (when not in editor)

### Confirmations
- Stop loop: "Are you sure? The current iteration will be interrupted."
- Delete spec: "Delete 01-overview.md? This cannot be undone."
- Overwrite file: "File was modified externally. Overwrite?"
