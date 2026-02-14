# Charts & Statistics

## Charts

### 1. Progress Timeline (ComposedChart)
The main chart on the Overview tab.

**Axes:**
- X-axis: Time (datetime)
- Left Y-axis: Cumulative tasks completed (0 to tasks_total)
- Right Y-axis: Tokens per iteration

**Series:**
- **Tasks completed** (Area, blue fill, solid line): Cumulative count over time
- **Token usage** (Bar, purple/transparent): Per iteration
- **Projection line** (Line, dashed, gray): Linear extrapolation from current velocity to tasks_total
- **Error markers** (Scatter, red dots): Placed at iterations where errors occurred

**Tooltip:** Shows iteration number, tasks completed (cumulative), tokens used, status, timestamp.

**Projection calculation:**
```
velocity = tasks_completed / elapsed_time
remaining_time = tasks_remaining / velocity
projected_completion = now + remaining_time
```
Only show projection if >= 3 iterations completed.

### 2. Task Burndown (LineChart)
Classic burndown chart.

**Axes:**
- X-axis: Time (or iteration number)
- Y-axis: Tasks remaining (tasks_total down to 0)

**Series:**
- **Ideal line** (Line, dashed gray): Straight line from tasks_total to 0
- **Actual line** (Line, solid blue): Actual tasks remaining at each point

**Visual indicators:**
- If actual > ideal → behind schedule (area between lines red-tinted)
- If actual < ideal → ahead of schedule (area green-tinted)

### 3. Token Usage by Phase (PieChart)
**Data:** Sum tokens for iterations that completed tasks in each phase.
**Appearance:** Donut chart with phase names as labels. Center text: total tokens.

### 4. Iteration Health Timeline (custom component)
A horizontal strip of colored cells, one per iteration.

**Colors:**
- 🟢 Green (#22C55E): Productive — task(s) completed, tests passed
- 🟡 Yellow (#EAB308): Partial — no task completed but progress made (commits exist)
- 🔴 Red (#EF4444): Failed — error, crash, or test failure with no progress

**Interaction:** Hover shows iteration summary tooltip. Click navigates to iteration detail.

**Size:** Compact — each cell ~12-16px wide, height ~24px. Scales to fit container.

### 5. Cost Breakdown (BarChart, optional on stats section)
Stacked bar: cost per phase.

## Statistics

### Calculated Metrics

**Time-based:**
- Total duration: sum of all iteration durations
- Average iteration duration: total_duration / iterations
- Running time: wall clock time from first iteration start to last iteration end
- Projected remaining time: tasks_remaining × avg_time_per_task_completion

**Token-based:**
- Total tokens: sum across all iterations
- Average tokens per iteration
- Tokens per completed task
- Token trend: increasing/decreasing/stable (linear regression over last 10)

**Cost-based:**
- Cost = tokens × price_per_token (model-specific)
- Default pricing (configurable):
  - codex (gpt-5.2-codex): Check and set a reasonable default
  - claude: Check and set a reasonable default
- Cost per iteration, cumulative, projected total

**Progress-based:**
- Tasks completed / total (count and percentage)
- Phases completed / total
- Current phase being worked on
- Velocity: tasks per hour (rolling average over last 5 completed tasks)
- Projected completion: current time + (tasks_remaining / velocity)

**Quality-based:**
- Success rate: successful_iterations / total_iterations × 100
- Error count: iterations with errors
- Consecutive successes: current streak
- Test pass rate (if tests configured)
- Health breakdown: productive/partial/failed counts

### Data Aggregation

Stats should be calculated both:
1. **Server-side** in the `/stats` endpoint (for initial load and report generation)
2. **Client-side** from the Zustand store (for real-time updates without extra API calls)

When a new iteration event arrives via WebSocket, the frontend recalculates all derived metrics from the iteration list in the store.

## Report Generation

### Markdown Report (GET /api/projects/{id}/report)

Template:
```markdown
# Project Report: {project_name}

**Generated:** {timestamp}
**Status:** {status}
**Duration:** {start_time} → {end_time} ({total_duration})

## Summary
- **Iterations:** {completed} / {max}
- **Tasks:** {done} / {total} ({percentage}%)
- **Total Tokens:** {tokens}
- **Estimated Cost:** ${cost}
- **Average Velocity:** {tasks_per_hour} tasks/hour

## Phase Breakdown
| Phase | Tasks | Tokens | Duration | Status |
|-------|-------|--------|----------|--------|
| ... | ... | ... | ... | ... |

## Iteration Log
| # | Duration | Tokens | Status | Tasks Completed |
|---|----------|--------|--------|-----------------|
| ... | ... | ... | ... | ... |

## Errors
{list of errors with iteration context}

## Configuration
- CLI: {cli}
- Flags: {flags}
- Test Command: {test_command}
```
