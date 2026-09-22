import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from 'recharts'

import type { DailyBucket } from '../lib/types'
import { CHART_HEIGHT } from './chartHeight'

interface MiniBarChartProps {
  data: DailyBucket[]
  unit: string
}

/**
 * Seven days of one habit.
 *
 * Lazy-loaded by `HabitCard`: Recharts is by far the heaviest dependency here
 * and the dashboard shell should paint without waiting for it.
 */
export function MiniBarChart({ data, unit }: MiniBarChartProps) {
  // The one place a decimal string becomes a number. It decides a bar's height
  // in pixels and is never sent anywhere or added to anything, so the rounding
  // that makes floats unsafe for money is irrelevant here. The exact string is
  // carried alongside for the tooltip.
  const points = data.map((bucket) => ({
    label: bucket.label,
    date: bucket.date,
    height: Number(bucket.value),
    exact: bucket.value,
  }))

  return (
    <div style={{ height: CHART_HEIGHT }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fill: 'var(--tg-theme-hint-color, #8a8a8e)' }}
            interval={0}
          />
          <Tooltip
            cursor={false}
            contentStyle={{
              background: 'var(--tg-theme-bg-color, #ffffff)',
              border: '1px solid var(--tg-theme-hint-color, #d0d0d4)',
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(_value, _name, entry) => [
              `${(entry?.payload as { exact?: string } | undefined)?.exact ?? '0'} ${unit}`,
              '',
            ]}
            labelFormatter={(_label, payload) =>
              (payload?.[0]?.payload as { date?: string } | undefined)?.date ?? ''
            }
          />
          <Bar
            dataKey="height"
            radius={[3, 3, 0, 0]}
            // Paints a full-height track behind every category, so all seven
            // days read as a grid even when most of them are zero.
            background={{ fill: 'var(--tg-theme-secondary-bg-color, #f1f1f4)', radius: 3 }}
            // Recharts draws nothing at all for a zero-height rect. This gives
            // an empty day a 2px stub so it is visibly *empty* rather than
            // visibly absent. Padding the data itself — 0 becomes 0.01 — was
            // rejected: it would lie to the tooltip and skew the axis.
            minPointSize={(value: number | null | undefined) => (value ? 0 : 2)}
            isAnimationActive={false}
          >
            {points.map((point) => (
              <Cell
                key={point.date}
                fill={
                  point.height === 0
                    ? 'var(--tg-theme-hint-color, #c7c7cc)'
                    : 'var(--tg-theme-button-color, #2481cc)'
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
