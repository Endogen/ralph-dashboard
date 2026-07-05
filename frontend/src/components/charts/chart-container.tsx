import { useLayoutEffect, useRef, useState, type ReactElement } from "react"

import { ResponsiveContainer } from "recharts"

type ChartContainerProps = {
  className?: string
  children: ReactElement
}

type Dimension = {
  width: number
  height: number
}

/**
 * Sized wrapper for Recharts' ResponsiveContainer. The container is measured
 * before first paint and passed as `initialDimension`, because the default
 * (-1 x -1) makes ResponsiveContainer log "width(-1) and height(-1) of chart
 * should be greater than 0" warnings and skip the chart until its
 * ResizeObserver fires. Subsequent resizes are still handled by
 * ResponsiveContainer itself.
 */
export function ChartContainer({ className, children }: ChartContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimension, setDimension] = useState<Dimension | null>(null)

  useLayoutEffect(() => {
    const node = containerRef.current
    if (!node) {
      return
    }
    const rect = node.getBoundingClientRect()
    setDimension({ width: Math.round(rect.width), height: Math.round(rect.height) })
  }, [])

  return (
    <div ref={containerRef} className={className}>
      {dimension !== null && (
        <ResponsiveContainer
          width="100%"
          height="100%"
          initialDimension={dimension.width > 0 && dimension.height > 0 ? dimension : undefined}
        >
          {children}
        </ResponsiveContainer>
      )}
    </div>
  )
}
