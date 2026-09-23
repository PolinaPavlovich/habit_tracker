import { useCallback, useEffect, useState } from 'react'

import { ApiError, api } from '../lib/api'
import { ZERO } from '../lib/decimal'
import { addDaysISO, weekdayLabel } from '../lib/time'
import type { Activity, DailyBucket, SummaryResponse } from '../lib/types'
import { useHabitStore } from '../stores/habitStore'

export const SUMMARY_DAYS = 7

/** One habit as the dashboard renders it: the activity plus its window totals. */
export interface HabitView {
  activityId: number
  name: string
  unit: string
  /** Decimal string. */
  total: string
  entriesCount: number
  weeklyStats: DailyBucket[]
}

type DashboardStatus =
  | { kind: 'loading' }
  | { kind: 'ready'; habits: HabitView[] }
  | { kind: 'error'; message: string }

/**
 * Server state for the dashboard.
 *
 * Kept in component state rather than in Zustand on purpose: this is fetched
 * data with a single consumer, and copying it into a global store would mean
 * two sources of truth to keep in step. The store next door holds only the
 * optimistic writes layered on top of this.
 */
export function useDashboardData(): { state: DashboardStatus; reload: () => void } {
  const [state, setState] = useState<DashboardStatus>({ kind: 'loading' })
  const [nonce, setNonce] = useState(0)
  const reconcile = useHabitStore((store) => store.reconcile)

  const reload = useCallback(() => setNonce((value) => value + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    const startedAt = Date.now()

    async function load() {
      try {
        // Parallel, not sequential: neither request depends on the other, and
        // on a cold Lambda two round trips in series is a visible stall.
        const [activities, summary] = await Promise.all([
          api.listActivities(controller.signal),
          api.getSummary(SUMMARY_DAYS, controller.signal),
        ])
        setState({ kind: 'ready', habits: joinHabits(activities, summary) })
        // Anything that settled before this fetch began is now included in the
        // totals above, so its draft can stop being added on top.
        reconcile(startedAt)
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState({
          kind: 'error',
          message: error instanceof ApiError ? error.message : 'Could not load your habits.',
        })
      }
    }

    void load()
    return () => controller.abort()
  }, [nonce, reconcile])

  return { state, reload }
}

/**
 * Left-join activities onto summary rows.
 *
 * `/logs/summary` inner-joins `logs`, so a habit created ten seconds ago with
 * nothing logged against it has no row there at all. Driving the list from
 * `/activities` instead means a brand-new habit still gets a card — with an
 * empty week — rather than silently not existing until its first entry.
 */
function joinHabits(activities: Activity[], summary: SummaryResponse): HabitView[] {
  // Same reasoning as `weekly_stats` below: `items` is the other array this
  // function walks, and a response without it would crash before rendering.
  const items = Array.isArray(summary.items) ? summary.items : []
  const byId = new Map(items.map((item) => [item.activity_id, item]))

  return (Array.isArray(activities) ? activities : []).map((activity) => {
    const item = byId.get(activity.id)
    if (item) {
      return {
        activityId: activity.id,
        name: item.activity_name,
        unit: item.unit,
        total: item.total_amount ?? ZERO,
        entriesCount: item.entries_count ?? 0,
        // Coerced, not trusted. The backend empties `weekly_stats` whenever
        // `days` exceeds 31, and an older deployment may not send the field at
        // all — either way `HabitCard` would reach `undefined.map()` and take
        // the whole render down. This is the API boundary, so it is where the
        // shape gets checked.
        weeklyStats: Array.isArray(item.weekly_stats)
          ? item.weekly_stats
          : emptyWeek(summary.period_start, summary.days),
      }
    }
    return {
      activityId: activity.id,
      name: activity.name,
      unit: activity.unit,
      total: ZERO,
      entriesCount: 0,
      weeklyStats: emptyWeek(summary.period_start, summary.days),
    }
  })
}

/** A zero-filled window for a habit the summary never mentioned. */
function emptyWeek(periodStart: string, days: number): DailyBucket[] {
  // Guard the length: `Array.from({length: NaN})` yields an empty array and a
  // chart with no columns at all, which reads as a rendering bug rather than an
  // empty week.
  const span = Number.isFinite(days) && days > 0 ? Math.min(days, SUMMARY_DAYS) : SUMMARY_DAYS
  return Array.from({ length: span }, (_unused, offset) => {
    const date = addDaysISO(periodStart, offset)
    return { date, label: weekdayLabel(date), value: ZERO }
  })
}
