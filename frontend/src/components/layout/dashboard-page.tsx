import { BarChart3 } from "lucide-react"

import { Button } from "@/components/ui/button"

export function DashboardPage() {
  return (
    <section className="flex min-h-[60vh] flex-col items-center justify-center gap-5 rounded-2xl border border-dashed border-border/80 bg-card/30 p-10 text-center">
      <BarChart3 className="h-12 w-12 text-primary" />
      <div className="space-y-2">
        <h1 className="text-balance text-3xl font-semibold tracking-tight">Ralph Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Frontend scaffold is ready. Next tasks will populate project data and live controls.
        </p>
      </div>
      <Button variant="outline">Add Project</Button>
    </section>
  )
}
