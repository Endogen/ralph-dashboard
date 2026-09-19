import { readFileSync, statSync } from "node:fs"
import { resolve } from "node:path"

const index = readFileSync("dist/index.html", "utf8")
const assets = new Set([...index.matchAll(/(?:src|href)="([^"?]+\.js)"/g)].map(match => match[1]))
if (!assets.size) throw new Error("No entry JavaScript found in dist/index.html")
const total = [...assets].reduce((sum, asset) => sum + statSync(resolve("dist", asset.replace(/^\//, ""))).size, 0)
const budget = 350 * 1024
console.log(`Initial JavaScript: ${(total / 1024).toFixed(1)} KiB / ${budget / 1024} KiB budget`)
if (total > budget) throw new Error("Initial JavaScript exceeds its size budget. Keep optional pages and editors lazy.")
