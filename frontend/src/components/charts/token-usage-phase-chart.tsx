import { useMemo } from "react"

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

import { displayTokens } from "@/lib/utils"
import type { PhaseTokenUsage } from "@/types/project"

const PHASE_COLORS = [
  "#2563EB",
  "#0891B2",
  "#0D9488",
  "#65A30D",
  "#D97706",
  "#DC2626",
  "#7C3AED",
  "#DB2777",
] as const

type TokenUsagePhaseChartProps = {
  data: PhaseTokenUsage[]
  totalTokens: number
}

type TokenTooltipProps = {
  active?: boolean
  payload?: Array<{ name: string; value: number; payload: { tokens: number; phase: string } }>
}

function formatTokens(value: number): string {
  // Convert from k-tokens to actual tokens for display
  return displayTokens(value).toLocaleString("en-US")
}

function TokenTooltip({ active, payload }: TokenTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const item = payload[0]
  if (!item) {
    return null
  }

  return (
    <div className="rounded-md border bg-background px-3 py-2 text-xs shadow-lg">
      <p className="font-semibold">{item.name}</p>
      <p className="mt-1">{item.value.toLocaleString("en-US")} tokens</p>
    </div>
  )
}

export function TokenUsagePhaseChart({ data, totalTokens }: TokenUsagePhaseChartProps) {
  const chartData = useMemo(() => {
    return data
      .filter((item) => item.tokens > 0)
      .sort((left, right) => right.tokens - left.tokens)
      // Convert k-tokens to actual tokens for chart display
      .map((item) => ({ phase: item.phase, tokens: displayTokens(item.tokens) }))
  }, [data])

  return (
    <section className="max-w-full overflow-hidden p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold">Token Usage by Phase</h3>
        <p className="break-words text-sm text-muted-foreground">Token consumption distribution across implementation phases.</p>
      </header>

      {chartData.length === 0 ? (
        <div className="flex h-[300px] items-center justify-center rounded-lg border bg-background/40 text-sm text-muted-foreground">
          No phase token data available yet.
        </div>
      ) : (
        <div className="relative h-[300px] w-full overflow-hidden">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="tokens"
                nameKey="phase"
                cx="50%"
                cy="50%"
                innerRadius={62}
                outerRadius={102}
                paddingAngle={2}
                stroke="var(--color-background)"
                strokeWidth={1}
              >
                {chartData.map((entry, index) => (
                  <Cell key={entry.phase} fill={PHASE_COLORS[index % PHASE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<TokenTooltip />} />
              <Legend verticalAlign="bottom" height={40} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="rounded-md border bg-background/90 px-3 py-2 text-center">
              <p className="text-xs text-muted-foreground">Total Tokens</p>
              <p className="text-sm font-semibold">{formatTokens(totalTokens)}</p>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
