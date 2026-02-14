import { type FormEvent, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"

import { apiFetch } from "@/api/client"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/stores/auth-store"

type LoginResponse = {
  access_token: string
  refresh_token: string
  token_type: "bearer"
}

export function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const navigate = useNavigate()
  const location = useLocation()
  const setTokens = useAuthStore((state) => state.setTokens)

  const fromPath = (location.state as { from?: string } | null)?.from ?? "/"

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const response = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      })
      setTokens(response.access_token, response.refresh_token)
      navigate(fromPath, { replace: true })
    } catch {
      setError("Invalid username or password.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="mx-auto mt-20 w-full max-w-sm space-y-6 rounded-xl border bg-card p-6 shadow-sm">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold">Sign In</h1>
        <p className="text-sm text-muted-foreground">Authenticate to access Ralph Dashboard.</p>
      </header>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium">
          Username
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input
            type="password"
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && <p className="text-sm font-medium text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Login"}
        </Button>
      </form>
    </section>
  )
}
