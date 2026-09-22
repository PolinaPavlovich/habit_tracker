import { CHART_HEIGHT } from './chartHeight'

/** Holds the chart's exact space while its chunk loads, so nothing shifts. */
export function ChartSkeleton() {
  return (
    <div
      style={{
        height: CHART_HEIGHT,
        borderRadius: 6,
        background: 'var(--tg-theme-secondary-bg-color, #f1f1f4)',
      }}
    />
  )
}
