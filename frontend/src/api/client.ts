import { useAuthStore } from "@/stores/auth-store"

const API_BASE = "/api"

type RefreshResponse = {
  access_token: string
  token_type: "bearer"
}

let refreshInFlight: Promise<string | null> | null = null

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

async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) {
    return refreshInFlight
  }

  const { refreshToken, setTokens, clearTokens } = useAuthStore.getState()
  if (!refreshToken) {
    return null
  }

  refreshInFlight = (async () => {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) {
      clearTokens()
      return null
    }

    const payload = (await response.json()) as RefreshResponse
    setTokens(payload.access_token, refreshToken)
    return payload.access_token
  })()

  try {
    return await refreshInFlight
  } finally {
    refreshInFlight = null
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const request = async (accessToken: string | null): Promise<Response> =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      headers: buildHeaders(init?.headers, accessToken),
    })

  const state = useAuthStore.getState()
  let response = await request(state.accessToken)

  if (response.status === 401 && state.refreshToken) {
    const refreshedToken = await refreshAccessToken()
    if (refreshedToken) {
      response = await request(refreshedToken)
    }
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail ? `API request failed (${response.status}): ${detail}` : `API request failed (${response.status})`)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
