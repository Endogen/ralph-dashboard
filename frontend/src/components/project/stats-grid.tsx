import {
  AlertTriangle,
  BadgeCheck,
  Coins,
  Gauge,
  ListChecks,
  Percent,
  Repeat2,
  Wallet,
} from "lucide-react"

type StatsGridProps = {
  totalTokens: number
  estimatedCostUsd: number
  iterationsCompleted: number
  averageIterationDuration: string
  tasksCompleted: number
  tasksTotal: number
  errorCount: number
  successRate: number
}

type StatItem = {
  label: string
  value: string
  icon: typeof Coins
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function formatInt(value: number): string {
  return new Intl.NumberFormat("en-US").format(value)
}

export function StatsGrid({
  totalTokens,
  estimatedCostUsd,
  iterationsCompleted,
  averageIterationDuration,
  tasksCompleted,
  tasksTotal,
  errorCount,
  successRate,
}: StatsGridProps) {
  const items: StatItem[] = [
    { label: "Total Tokens", value: formatInt(totalTokens), icon: Coins },
    { label: "Estimated Cost", value: formatUsd(estimatedCostUsd), icon: Wallet },
    { label: "Iterations", value: formatInt(iterationsCompleted), icon: Repeat2 },
    { label: "Avg Duration", value: averageIterationDuration, icon: Gauge },
    { label: "Tasks Done", value: `${tasksCompleted}/${tasksTotal}`, icon: ListChecks },
    { label: "Errors", value: formatInt(errorCount), icon: AlertTriangle },
    { label: "Success Rate", value: `${successRate.toFixed(1)}%`, icon: Percent },
    { label: "Health", value: errorCount === 0 ? "Stable" : "Needs Review", icon: BadgeCheck },
  ]

  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => {
        const Icon = item.icon
        return (
          <article key={item.label} className="rounded-lg border bg-card p-3">
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <Icon className="h-3.5 w-3.5" />
              {item.label}
            </p>
            <p className="mt-1 text-sm font-semibold">{item.value}</p>
          </article>
        )
      })}
    </section>
  )
}
