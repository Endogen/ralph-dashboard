/** Sample only after cumulative values are computed; always retain endpoints. */
export function sampleTimeline<T>(points: T[], limit = 500): T[] {
  if (points.length <= limit) return points
  return Array.from({ length: limit }, (_, index) => points[Math.round(index * (points.length - 1) / (limit - 1))])
}
