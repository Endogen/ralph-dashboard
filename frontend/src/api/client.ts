import { useAuthStore } from "@/stores/auth-store"

const API_BASE = "/api"

type RefreshResponse = {
  access_token: string
  token_type: "bearer"
}

const revisions = new Map<string, string>()
const responseRevisions = new WeakMap<object, string>()

export function apiRevision(response: object): string {
  return responseRevisions.get(response) ?? ""
}

let refreshInFlight: { sessionVersion: number; promise: Promise<string | null> } | null = null

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = (await response.clone().json()) as unknown
    if (payload && typeof payload === "object" && "detail" in payload) {
      const detail = (payload as { detail?: unknown }).detail
      if (typeof detail === "string" && detail.trim()) {
        return detail.trim()
      }
    }
  } catch {
    // Fall through to plain-text parse.
  }

  try {
    const text = (await response.clone().text()).trim()
    if (text) {
      return text
    }
  } catch {
    // Ignore parse failure and return null.
  }

  return null
}

function buildHeaders(initHeaders: HeadersInit | undefined, accessToken: string | null): Headers {
  const headers = new Headers(initHeaders)
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`)
  }
  return headers
}

export async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, sessionVersion, clearTokens } = useAuthStore.getState()
  if (!refreshToken) return null
  if (refreshInFlight?.sessionVersion === sessionVersion) return refreshInFlight.promise

  const isCurrentSession = () => useAuthStore.getState().sessionVersion === sessionVersion
  const promise = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!isCurrentSession()) return null
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          clearTokens()
          return null
        }
        throw new Error(`Token refresh failed (${response.status})`)
      }

      const payload = (await response.json()) as RefreshResponse
      if (!isCurrentSession()) return null
      // Refresh the access token within this session; login and logout advance its version.
      useAuthStore.setState({ accessToken: payload.access_token })
      return payload.access_token
    } catch (error) {
      if (!isCurrentSession()) return null
      throw error
    }
  })()
  const pending = { sessionVersion, promise }
  refreshInFlight = pending
  try {
    return await promise
  } finally {
    if (refreshInFlight === pending) refreshInFlight = null
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!headers.has("If-Match") && ["PUT", "DELETE"].includes(init?.method ?? "") && revisions.has(path)) {
    headers.set("If-Match", revisions.get(path)!)
  }
  const request = async (accessToken: string | null): Promise<Response> =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      headers: buildHeaders(headers, accessToken),
    })

  const state = useAuthStore.getState()
  let response = await request(state.accessToken)

  if (response.status === 401 && state.refreshToken &&
      useAuthStore.getState().sessionVersion === state.sessionVersion) {
    const refreshedToken = await refreshAccessToken()
    if (refreshedToken) {
      response = await request(refreshedToken)
    }
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail ? `API request failed (${response.status}): ${detail}` : `API request failed (${response.status})`)
  }

  const revision = response.headers.get("ETag")
  if (revision) revisions.set(path, revision)
  if (revisions.size > 500) revisions.delete(revisions.keys().next().value!)

  if (response.status === 204) {
    return undefined as T
  }
  const payload = await response.json()
  if (revision && payload && typeof payload === "object") responseRevisions.set(payload, revision)
  return payload as T
}

export async function freshAccessToken(): Promise<string | null> {
  const token = useAuthStore.getState().accessToken
  if (!token) return null
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")))
    if (payload.exp * 1000 > Date.now() + 30000) return token
  } catch { /* Refresh malformed or expired tokens. */ }
  return refreshAccessToken()
}
