import { Suspense, lazy, useState } from 'react'

import { forDisplay, normaliseAmount, sumAmounts } from '../lib/decimal'
import { todayISO } from '../lib/time'
import type { HabitView } from '../hooks/useDashboardData'
import { useFailedDrafts, useHabitStore, useOptimisticAmount } from '../stores/habitStore'
import { AmountInput } from './AmountInput'
import { ChartSkeleton } from './ChartSkeleton'

// Recharts is the heaviest thing this app imports and nothing above the fold
// needs it, so it arrives in its own chunk after the shell has painted.
const MiniBarChart = lazy(() =>
  import('./MiniBarChart').then((module) => ({ default: module.MiniBarChart })),
)

interface HabitCardProps {
  habit: HabitView
  onLogged: () => void
}

export function HabitCard({ habit, onLogged }: HabitCardProps) {
  const [draftAmount, setDraftAmount] = useState('')
  const today = todayISO()

  const addProgress = useHabitStore((store) => store.addProgress)
  const retryDraft = useHabitStore((store) => store.retryDraft)
  const dismissDraft = useHabitStore((store) => store.dismissDraft)

  // Only today's drafts: the card's headline figure is today's progress.
  const optimisticToday = useOptimisticAmount(habit.activityId, today)
  const failed = useFailedDrafts(habit.activityId)

  const serverToday = habit.weeklyStats.at(-1)?.value ?? '0.00'
  const displayedToday = sumAmounts([serverToday, optimisticToday])

  // Fold the optimistic total into today's bar so the chart and the number
  // above it never disagree while a write is in flight.
  const chartData = habit.weeklyStats.map((bucket, index) =>
    index === habit.weeklyStats.length - 1 ? { ...bucket, value: displayedToday } : bucket,
  )

  const parsed = normaliseAmount(draftAmount)

  async function submit() {
    if (!parsed) return
    setDraftAmount('')
    await addProgress({ activityId: habit.activityId, amount: parsed, date: today })
    onLogged()
  }

  return (
    <section className="card">
      <div className="card__head">
        <span className="card__name">{habit.name}</span>
        <span className="card__today">
          {forDisplay(displayedToday)} {habit.unit} today
        </span>
      </div>

      <Suspense fallback={<ChartSkeleton />}>
        <MiniBarChart data={chartData} unit={habit.unit} />
      </Suspense>

      <div className="row">
        <AmountInput
          value={draftAmount}
          onChange={setDraftAmount}
          placeholder={`Add ${habit.unit}`}
          onSubmit={() => void submit()}
        />
        <button className="button" disabled={!parsed} onClick={() => void submit()}>
          Add
        </button>
      </div>

      {failed.map((draft) => (
        <div key={draft.draftId} className="draft-error">
          <span className="draft-error__amount">
            {forDisplay(draft.amount)} {habit.unit}
          </span>
          <span>{draft.status.kind === 'error' ? draft.status.message : ''}</span>
          {draft.status.kind === 'error' && draft.status.retryable && (
            <button
              className="button button--quiet"
              onClick={() => void retryDraft(draft.draftId).then(onLogged)}
            >
              Retry
            </button>
          )}
          <button className="button button--quiet" onClick={() => dismissDraft(draft.draftId)}>
            Dismiss
          </button>
        </div>
      ))}

      <div className="hint">
        {forDisplay(habit.total)} {habit.unit} over 7 days · {habit.entriesCount} entries
      </div>
    </section>
  )
}
