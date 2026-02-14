import { LayoutDashboard, LogIn, PanelsTopLeft, Settings2 } from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"

import { Button } from "@/components/ui/button"

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/project/demo", label: "Project Detail", icon: PanelsTopLeft },
]

export function AppLayout() {
  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive
        ? "bg-primary text-primary-foreground shadow-sm"
        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
    }`

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-[1200px] gap-4 p-4 md:p-6">
        <aside className="hidden w-72 flex-col rounded-2xl border bg-card/70 p-4 shadow-sm md:flex">
          <header className="space-y-1 border-b pb-4">
            <h1 className="text-lg font-semibold tracking-tight">Ralph Dashboard</h1>
            <p className="text-xs text-muted-foreground">Monitor and control active loop projects</p>
          </header>

          <nav className="mt-4 flex flex-1 flex-col gap-2">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <NavLink key={item.to} to={item.to} className={navLinkClass} end={item.to === "/"}>
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              )
            })}
          </nav>

          <footer className="mt-4 border-t pt-4">
            <Button asChild variant="outline" className="w-full justify-start gap-2">
              <NavLink to="/login">
                <LogIn className="h-4 w-4" />
                Sign In
              </NavLink>
            </Button>
          </footer>
        </aside>

        <main className="flex min-h-[80vh] flex-1 flex-col gap-4 rounded-2xl border bg-card/30 p-4 md:p-6">
          <header className="flex items-center justify-between rounded-xl border bg-background/70 px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Workspace
              </h2>
              <p className="text-sm text-muted-foreground">
                Sidebar, routing shell, and content area are now active.
              </p>
            </div>
            <Settings2 className="h-4 w-4 text-muted-foreground" />
          </header>

          <section className="flex-1">
            <Outlet />
          </section>
        </main>
      </div>
    </div>
  )
}
