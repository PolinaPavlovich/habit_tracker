import { useCallback } from 'react'
import { create } from 'zustand'
import type { StoreApi } from 'zustand'
import { useShallow } from 'zustand/react/shallow'

import { ApiError, api } from '../lib/api'
import { fromCents, toCents } from '../lib/decimal'
import { todayISO } from '../lib/time'

/**
 * A write in flight, or one that finished and has not been reconciled yet.
 *
 * Discriminated union rather than `isLoading`/`hasError` booleans: those admit
 * impossible combinations (loading *and* errored) that then have to be ruled
 * out by hand at every read.
 */
export type DraftStatus =
  | { kind: 'pending' }
  | { kind: 'settled'; logId: number; settledAt: number }
  | { kind: 'error'; message: string; httpStatus: number | null; retryable: boolean }

export interface ProgressDraft {
  draftId: string
  activityId: number
  /** Decimal string, exactly as it will be sent. */
  amount: string
  date: string
  status: DraftStatus
}

interface HabitState {
  drafts: Record<string, ProgressDraft>
}

interface HabitActions {
  addProgress(input: { activityId: number; amount: string; date?: string }): Promise<boolean>
  retryDraft(draftId: string): Promise<boolean>
  dismissDraft(draftId: string): void
  reconcile(fetchedAt: number): void
}

/**
 * Optimistic writes, and nothing else.
 *
 * This store holds **no server state**. Totals fetched from the API live in the
 * component that fetched them; what lives here is only the set of writes the UI
 * is pretending have already landed. A card renders `serverTotal + drafts`.
 *
 * The rollback design is the reason for that split. The obvious approach —
 * snapshot a habit's total, then restore it if the request fails — is wrong
 * under concurrency: with two writes in flight on one habit, restoring the
 * first one's snapshot on failure also erases the second one's effect, which
 * has nothing to do with the failure. An append-only log of deltas makes
 * rolling one back a single keyed removal that cannot disturb its neighbours.
 */
export const useHabitStore = create<HabitState & HabitActions>()((set, get) => ({
  drafts: {},

  async addProgress({ activityId, amount, date }) {
    const draftId = crypto.randomUUID()
    const draft: ProgressDraft = {
      draftId,
      activityId,
      amount,
      date: date ?? todayISO(),
      status: { kind: 'pending' },
    }

    set((state) => ({ drafts: { ...state.drafts, [draftId]: draft } }))
    return await send(draftId, set, get)
  },

  async retryDraft(draftId) {
    const existing = get().drafts[draftId]
    if (!existing) return false

    set((state) => ({
      drafts: { ...state.drafts, [draftId]: { ...existing, status: { kind: 'pending' } } },
    }))
    return await send(draftId, set, get)
  },

  dismissDraft(draftId) {
    set((state) => {
      const { [draftId]: _removed, ...rest } = state.drafts
      return { drafts: rest }
    })
  },

  reconcile(fetchedAt) {
    // Settled drafts are kept until a fetch that started *after* they settled
    // comes back, because that response is the first one guaranteed to already
    // include them. Dropping them any earlier makes the number visibly dip
    // between the write landing and the refetch arriving.
    set((state) => {
      const remaining: Record<string, ProgressDraft> = {}
      for (const [id, draft] of Object.entries(state.drafts)) {
        const superseded = draft.status.kind === 'settled' && draft.status.settledAt <= fetchedAt
        if (!superseded) remaining[id] = draft
      }
      return { drafts: remaining }
    })
  },
}))

type HabitStore = HabitState & HabitActions
type SetState = StoreApi<HabitStore>['setState']
type GetState = StoreApi<HabitStore>['getState']

/** Perform the write for a draft already present in the store. */
async function send(draftId: string, set: SetState, get: GetState): Promise<boolean> {
  const draft = get().drafts[draftId]
  if (!draft) return false

  const patch = (status: DraftStatus) =>
    set((state) => {
      // Re-read rather than closing over the old object: the draft may have
      // been dismissed while the request was in flight, and resurrecting it
      // would put a row back on screen the user already dismissed.
      const current = state.drafts[draftId]
      if (!current) return state
      return { drafts: { ...state.drafts, [draftId]: { ...current, status } } }
    })

  try {
    const created = await api.createLog(draft.activityId, draft.amount, draft.date)
    patch({ kind: 'settled', logId: created.id, settledAt: Date.now() })
    return true
  } catch (error) {
    const isApiError = error instanceof ApiError
    const httpStatus = isApiError ? error.status : null
    patch({
      kind: 'error',
      message: isApiError ? error.message : 'Something went wrong saving that.',
      httpStatus,
      // A 404 means the habit is gone; retrying will fail identically forever.
      // Network failures and 5xx are worth another attempt.
      retryable: httpStatus === null || httpStatus >= 500,
    })
    return false
  }
}

/** Sum the drafts that should still be shown as added to a habit's total. */
function optimisticCents(
  drafts: Record<string, ProgressDraft>,
  activityId: number,
  onDate?: string,
): bigint {
  let total = 0n
  for (const draft of Object.values(drafts)) {
    if (draft.activityId !== activityId) continue
    if (onDate !== undefined && draft.date !== onDate) continue
    // Errored drafts are shown struck through, not counted — the write failed.
    if (draft.status.kind === 'error') continue
    try {
      total += toCents(draft.amount)
    } catch {
      // Unparseable amounts never reach the store, but never trust that here.
    }
  }
  return total
}

/**
 * The amount to add to a habit's server total, as a decimal string.
 *
 * Returns a primitive, so a change to some *other* habit's drafts produces an
 * identical string and Zustand skips the re-render. Selecting `state.drafts`
 * directly would re-render every card on every keystroke of every card.
 */
export function useOptimisticAmount(activityId: number, onDate?: string): string {
  return useHabitStore(
    useCallback(
      (state) => fromCents(optimisticCents(state.drafts, activityId, onDate)),
      [activityId, onDate],
    ),
  )
}

/** The failed writes for one habit, for the retry row beneath its card. */
export function useFailedDrafts(activityId: number): ProgressDraft[] {
  return useHabitStore(
    useShallow((state) =>
      Object.values(state.drafts).filter(
        (draft) => draft.activityId === activityId && draft.status.kind === 'error',
      ),
    ),
  )
}
