import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ConfirmButton } from '../components/ConfirmButton'
import { HabitForm } from '../components/HabitForm'
import { ApiError, api } from '../lib/api'
import type { ActivityDetail } from '../lib/types'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'ready'; habit: ActivityDetail }
  | { kind: 'missing' }
  | { kind: 'error'; message: string }

function entriesLabel(count: number): string {
  return count === 1 ? '1 entry' : `${count} entries`
}

export function EditHabit() {
  const navigate = useNavigate()
  const { id } = useParams()
  // Anything that is not a positive whole number cannot be a habit id, so it
  // is "missing" without asking the backend.
  const activityId = id && /^[1-9]\d*$/.test(id) ? Number(id) : null

  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    if (activityId === null) {
      setState({ kind: 'missing' })
      return
    }
    const controller = new AbortController()
    setState({ kind: 'loading' })
    api
      .getActivity(activityId, controller.signal)
      .then((habit) => setState({ kind: 'ready', habit }))
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === 'AbortError') return
        if (cause instanceof ApiError && cause.status === 404) {
          setState({ kind: 'missing' })
          return
        }
        setState({
          kind: 'error',
          message: cause instanceof ApiError ? cause.message : 'Could not load that habit.',
        })
      })
    return () => controller.abort()
  }, [activityId])

  if (state.kind === 'loading') return <p className="hint">Loading habit…</p>
  if (state.kind === 'error') return <p className="hint">{state.message}</p>
  if (state.kind === 'missing') {
    return (
      <>
        <p className="hint">That habit no longer exists.</p>
        <Link className="button" to="/">
          Back to today
        </Link>
      </>
    )
  }

  const { habit } = state

  async function remove() {
    setDeleteError(null)
    try {
      await api.deleteActivity(habit.id)
    } catch (cause) {
      // Already gone — deleted from the bot or another tab — is the outcome
      // that was asked for, not a failure.
      if (!(cause instanceof ApiError && cause.status === 404)) {
        setDeleteError(cause instanceof ApiError ? cause.message : 'Could not delete that habit.')
        return
      }
    }
    navigate('/')
  }

  return (
    <>
      <HabitForm
        initial={{ name: habit.name, unit: habit.unit }}
        submitLabel="Save changes"
        savingLabel="Saving…"
        fallbackError="Could not save that habit."
        onSubmit={async (name, unit) => {
          await api.updateActivity(habit.id, {
            ...(name !== habit.name ? { name } : {}),
            ...(unit !== habit.unit ? { unit } : {}),
          })
          navigate('/')
        }}
        onCancel={() => navigate(-1)}
      />
      <p className="hint">
        Changing the unit relabels existing entries. Their numbers are not converted.
      </p>

      <section className="card">
        <div className="row row--spread">
          <span>{entriesLabel(habit.entries_count)} logged</span>
          <Link className="link" to={`/history?habit=${habit.id}`}>
            View entries
          </Link>
        </div>
        <div className="row">
          <ConfirmButton
            label="Delete habit"
            prompt={
              habit.entries_count > 0
                ? `Delete "${habit.name}" and its ${entriesLabel(habit.entries_count)}? This can't be undone.`
                : `Delete "${habit.name}"? This can't be undone.`
            }
            onConfirm={remove}
          />
        </div>
        {deleteError && <p className="draft-error">{deleteError}</p>}
      </section>
    </>
  )
}
