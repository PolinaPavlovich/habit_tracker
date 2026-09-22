import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { ApiError, api } from '../lib/api'
import { forDisplay } from '../lib/decimal'
import type { LogListItem } from '../lib/types'

const PAGE_SIZE = 10

export function History() {
  // Paging lives in the URL, not in component state: it survives a reload and
  // a shared link, and the back button steps through pages for free.
  const [searchParams, setSearchParams] = useSearchParams()
  const offset = Math.max(0, Number(searchParams.get('offset') ?? '0') || 0)

  const [entries, setEntries] = useState<LogListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setError(null)

    // Ask for one more row than we render. Getting it back is what tells us a
    // next page exists, without a count endpoint or a second request.
    api
      .listLogs(PAGE_SIZE + 1, offset, controller.signal)
      .then(setEntries)
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === 'AbortError') return
        setError(cause instanceof ApiError ? cause.message : 'Could not load your history.')
      })

    return () => controller.abort()
  }, [offset])

  if (error) return <p className="hint">{error}</p>
  if (!entries) return <p className="hint">Loading history…</p>

  const page = entries.slice(0, PAGE_SIZE)
  const hasNext = entries.length > PAGE_SIZE

  if (page.length === 0) {
    return (
      <>
        <p className="hint">Nothing logged yet.</p>
        <Link className="button" to="/">
          Back to today
        </Link>
      </>
    )
  }

  return (
    <>
      {page.map((entry) => (
        <div key={entry.id} className="card">
          <div className="card__head">
            <span className="card__name">{entry.activity_name}</span>
            <span className="card__today">
              {forDisplay(entry.amount)} {entry.unit}
            </span>
          </div>
          <div className="hint">{entry.date}</div>
        </div>
      ))}

      <div className="row">
        <button
          className="button button--quiet"
          disabled={offset === 0}
          onClick={() =>
            setSearchParams(
              (previous) => {
                previous.set('offset', String(Math.max(0, offset - PAGE_SIZE)))
                return previous
              },
              { replace: true },
            )
          }
        >
          Previous
        </button>
        <button
          className="button button--quiet"
          disabled={!hasNext}
          onClick={() =>
            setSearchParams(
              (previous) => {
                previous.set('offset', String(offset + PAGE_SIZE))
                return previous
              },
              { replace: true },
            )
          }
        >
          Next
        </button>
      </div>
    </>
  )
}
