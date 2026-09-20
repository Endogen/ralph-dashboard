import { readFileSync, readdirSync, statSync } from "node:fs"
import { resolve } from "node:path"

const KIB = 1024
const ENTRY_BUDGET_KIB = 350
// Route chunks load on navigation. Anything heavier than this belongs behind a
// further lazy boundary, unless it is deliberately on demand (see ON_DEMAND).
const ROUTE_BUDGET_KIB = 150
// Deliberately large, loaded only when the feature is opened. The cap still
// catches an unexpected jump; raise it knowingly, not by accident.
const ON_DEMAND = [
  { match: /^monaco-editor-/, budgetKiB: 3000, why: "code editor, opened on demand" },
  { match: /^editor\.worker-/, budgetKiB: 400, why: "monaco web worker" },
  { match: /^project-charts-panel-/, budgetKiB: 500, why: "recharts, rendered on the overview tab" },
]

const sizeKiB = (path) => statSync(resolve("dist", path)).size / KIB
const report = (label, actual, budget) =>
  `${label}: ${actual.toFixed(1)} KiB / ${budget} KiB budget`

const failures = []

// --- Entry: everything index.html pulls in before any navigation ------------
const index = readFileSync("dist/index.html", "utf8")
const entry = new Set([...index.matchAll(/(?:src|href)="([^"?]+\.js)"/g)].map((m) => m[1]))
if (!entry.size) throw new Error("No entry JavaScript found in dist/index.html")
const entryTotal = [...entry].reduce((sum, asset) => sum + sizeKiB(asset.replace(/^\//, "")), 0)
console.log(report("Initial JavaScript", entryTotal, ENTRY_BUDGET_KIB))
if (entryTotal > ENTRY_BUDGET_KIB) {
  failures.push("Initial JavaScript exceeds its budget. Keep optional pages and editors lazy.")
}

// --- Lazy chunks: each one judged on its own ---------------------------------
const entryNames = new Set([...entry].map((asset) => asset.replace(/^\/?assets\//, "")))
const chunks = readdirSync(resolve("dist/assets"))
  .filter((name) => name.endsWith(".js") && !entryNames.has(name))
  .map((name) => ({ name, kib: sizeKiB(`assets/${name}`) }))
  .sort((a, b) => b.kib - a.kib)

for (const { name, kib } of chunks) {
  const exception = ON_DEMAND.find((candidate) => candidate.match.test(name))
  const budget = exception ? exception.budgetKiB : ROUTE_BUDGET_KIB
  const note = exception ? ` (${exception.why})` : ""
  console.log(`  ${report(name, kib, budget)}${note}`)
  if (kib > budget) {
    failures.push(`${name} is ${kib.toFixed(1)} KiB, over its ${budget} KiB budget.`)
  }
}

if (failures.length) {
  throw new Error(`Bundle budget exceeded:\n  - ${failures.join("\n  - ")}`)
}
