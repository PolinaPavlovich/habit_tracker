import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { AmountInput } from '../components/AmountInput'
import { ConfirmButton } from '../components/ConfirmButton'
import { ApiError, api } from '../lib/api'
import { forDisplay, normaliseAmount } from '../lib/decimal'
import type { Activity, LogListItem } from '../lib/types'

const PAGE_SIZE = 10

export function History() {
  // Paging and the habit filter live in the URL, not in component state: they
  // survive a reload and a shared link, and "View entries" on a habit can link
  // straight to its filtered list.
  const [searchParams, setSearchParams] = useSearchParams()
  const offset = Math.max(0, Number(searchParams.get('offset') ?? '0') || 0)
  const habitParam = searchParams.get('habit') ?? ''
  const habitId = /^[1-9]\d*$/.test(habitParam) ? Number(habitParam) : null

  const [entries, setEntries] = useState<LogListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [habits, setHabits] = useState<Activity[]>([])
  // Bumped after an edit or a delete to refetch the page in view.
  const [nonce, setNonce] = useState(0)
  const [editing, setEditing] = useState<{ id: number; draft: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [rowError, setRowError] = useState<{ id: number; message: string } | null>(null)

  function goTo(nextOffset: number) {
    setSearchParams(
      (previous) => {
        previous.set('offset', String(Math.max(0, nextOffset)))
        return previous
      },
      { replace: true },
    )
  }

  useEffect(() => {
    const controller = new AbortController()
    // The filter is a convenience. If this fails the list below still works,
    // so the failure is not surfaced.
    api
      .listActivities(controller.signal)
      .then(setHabits)
      .catch(() => undefined)
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setError(null)

    // Ask for one more row than we render. Getting it back is what tells us a
    // next page exists, without a count endpoint or a second request.
    api
      .listLogs(PAGE_SIZE + 1, offset, habitId, controller.signal)
      .then((rows) => {
        // Deleting the last row of the last page leaves the offset pointing
        // past the end. Step back rather than show an empty page.
        if (rows.length === 0 && offset > 0) {
          goTo(offset - PAGE_SIZE)
          return
        }
        setEntries(rows)
      })
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === 'AbortError') return
        setError(cause instanceof ApiError ? cause.message : 'Could not load your history.')
      })

    return () => controller.abort()
    // `goTo` is left out on purpose: it only wraps the stable `setSearchParams`.
  }, [offset, habitId, nonce])

  const reload = () => setNonce((value) => value + 1)

  async function saveAmount(entry: LogListItem) {
    const parsed = editing ? normaliseAmount(editing.draft) : null
    if (!parsed || saving) return
    setSaving(true)
    setRowError(null)
    try {
      await api.updateLog(entry.id, parsed)
      setEditing(null)
      reload()
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 404) {
        // Deleted elsewhere while the row was open. Refetching removes it,
        // which says so more plainly than a message on a row about to vanish.
        setEditing(null)
        reload()
      } else {
        setRowError({
          id: entry.id,
          message: cause instanceof ApiError ? cause.message : 'Could not save that amount.',
        })
      }
    } finally {
      setSaving(false)
    }
  }

  async function remove(entry: LogListItem) {
    setRowError(null)
    try {
      await api.deleteLog(entry.id)
    } catch (cause) {
      // Already gone is the outcome that was asked for.
      if (!(cause instanceof ApiError && cause.status === 404)) {
        setRowError({
          id: entry.id,
          message: cause instanceof ApiError ? cause.message : 'Could not delete that entry.',
        })
        return
      }
    }
    reload()
  }

  const filter = habits.length > 0 && (
    <div className="row">
      <label className="hint" htmlFor="history-habit">
        Show
      </label>
      <select
        id="history-habit"
        value={habitId ?? ''}
        onChange={(event) => {
          setEditing(null)
          setSearchParams(
            (previous) => {
              if (event.target.value) previous.set('habit', event.target.value)
              else previous.delete('habit')
              // A different list has different pages.
              previous.delete('offset')
              return previous
            },
            { replace: true },
          )
        }}
      >
        <option value="">All habits</option>
        {habits.map((habit) => (
          <option key={habit.id} value={habit.id}>
            {habit.name}
          </option>
        ))}
      </select>
    </div>
  )

  if (error) return <p className="hint">{error}</p>
  if (!entries) return <p className="hint">Loading history…</p>

  const page = entries.slice(0, PAGE_SIZE)
  const hasNext = entries.length > PAGE_SIZE

  if (page.length === 0) {
    return (
      <>
        {filter}
        <p className="hint">
          {habitId === null ? 'Nothing logged yet.' : 'Nothing logged for this habit yet.'}
        </p>
        <Link className="button" to="/">
          Back to today
        </Link>
      </>
    )
  }

  return (
    <>
      {filter}

      {page.map((entry) => {
        const isEditing = editing?.id === entry.id
        return (
          <div key={entry.id} className="card">
            <div className="card__head">
              <span className="card__name">{entry.activity_name}</span>
              <span className="card__today">
                {forDisplay(entry.amount)} {entry.unit}
              </span>
            </div>
            <div className="hint">{entry.date}</div>

            {isEditing ? (
              <div className="row">
                <AmountInput
                  value={editing.draft}
                  onChange={(draft) => setEditing({ id: entry.id, draft })}
                  placeholder={`New amount (${entry.unit})`}
                  onSubmit={() => void saveAmount(entry)}
                />
                <button
                  className="button"
                  disabled={saving || !normaliseAmount(editing.draft)}
                  onClick={() => void saveAmount(entry)}
                >
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button
                  className="button button--quiet"
                  disabled={saving}
                  onClick={() => setEditing(null)}
                >
                  Cancel
                </button>
              </div>
            ) : (
              <div className="row row--wrap">
                <button
                  className="button button--quiet"
                  onClick={() => {
                    setRowError(null)
                    setEditing({ id: entry.id, draft: forDisplay(entry.amount) })
                  }}
                >
                  Edit
                </button>
                <ConfirmButton
                  quiet
                  label="Delete"
                  prompt={`Delete this entry? "${entry.activity_name}" itself stays.`}
                  onConfirm={() => remove(entry)}
                />
              </div>
            )}

            {rowError?.id === entry.id && <p className="draft-error">{rowError.message}</p>}
          </div>
        )
      })}

      <div className="row">
        <button
          className="button button--quiet"
          disabled={offset === 0}
          onClick={() => goTo(offset - PAGE_SIZE)}
        >
          Previous
        </button>
        <button
          className="button button--quiet"
          disabled={!hasNext}
          onClick={() => goTo(offset + PAGE_SIZE)}
        >
          Next
        </button>
      </div>
    </>
  )
}
