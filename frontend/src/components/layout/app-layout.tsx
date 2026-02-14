import { Outlet } from "react-router-dom"

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-4 p-6">
        <Outlet />
      </main>
    </div>
  )
}
