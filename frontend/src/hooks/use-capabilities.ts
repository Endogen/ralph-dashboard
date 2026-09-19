import { useEffect, useState } from "react"
import { apiFetch } from "@/api/client"

type Capabilities = { project_dirs: string[]; agents: Record<string, boolean> }
let cached: Promise<Capabilities> | null = null
export function useCapabilities() {
  const [value, setValue] = useState<Capabilities | null>(null)
  useEffect(() => {
    let active = true
    cached ??= apiFetch<Capabilities>("/capabilities")
    cached.then((result) => { if (active) setValue(result) }).catch(() => { cached = null })
    return () => { active = false }
  }, [])
  return value
}
