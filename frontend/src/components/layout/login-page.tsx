import { useState } from "react"

import { Button } from "@/components/ui/button"

export function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  return (
    <section className="mx-auto mt-20 w-full max-w-sm space-y-6 rounded-xl border bg-card p-6 shadow-sm">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold">Sign In</h1>
        <p className="text-sm text-muted-foreground">Authenticate to access Ralph Dashboard.</p>
      </header>
      <form className="space-y-4">
        <label className="block text-sm font-medium">
          Username
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input
            type="password"
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <Button type="submit" className="w-full">
          Login
        </Button>
      </form>
    </section>
  )
}
