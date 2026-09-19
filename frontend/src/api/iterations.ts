import { apiFetch } from "@/api/client"
import type { IterationListResponse, IterationSummary } from "@/types/project"

/** Fetch summaries in bounded pages; logs are fetched separately on demand. */
export async function fetchIterationHistory(projectId: string): Promise<IterationListResponse> {
  const entries = new Map<number, IterationSummary>()
  let offset = 0
  let total = 0
  do {
    const page = await apiFetch<IterationListResponse>(`/projects/${projectId}/iterations?status=all&sort=asc&limit=500&offset=${offset}`)
    page.iterations.forEach((iteration) => entries.set(iteration.number, iteration))
    total = page.total
    offset += page.iterations.length
    if (!page.iterations.length) break
  } while (offset < total)
  return { iterations: [...entries.values()], total }
}
