import { useCallback, useEffect, useState } from 'react'

import { ApiError, api } from '../lib/api'
import { useAuthStore } from '../stores/authStore'

export type QrState =
  | { kind: 'initializing' }
  | { kind: 'waiting'; approveUrl: string; expiresAt: string }
  | { kind: 'approved' }
  | { kind: 'expired' }
  | { kind: 'error'; message: string }

/** Give up rather than hammer a backend that is clearly not answering. */
const MAX_CONSECUTIVE_FAILURES = 6
const BACKOFF_FACTOR = 1.6
const MAX_DELAY_MS = 15_000

/**
 * Open a QR login session and wait for a phone to approve it.
 *
 * Short polling, not a WebSocket: the backend is a Lambda behind a Function
 * URL and holds no connections open.
 *
 * The loop is a chain of `setTimeout` calls rather than `setInterval`.
 * `setInterval` keeps firing while a request is still outstanding, so a slow
 * response stacks overlapping requests; and a browser that throttles a
 * background tab will queue the missed ticks and release them all at once on
 * resume. Chaining means the next poll is scheduled only once the previous one
 * has resolved.
 */
export function useQrSession(enabled: boolean): { state: QrState; restart: () => void } {
  const [state, setState] = useState<QrState>({ kind: 'initializing' })
  const [nonce, setNonce] = useState(0)
  const setToken = useAuthStore((store) => store.setToken)

  const restart = useCallback(() => setNonce((value) => value + 1), [])

  useEffect(() => {
    if (!enabled) return

    // Effect-scoped mutable state rather than refs: it is created fresh on
    // every restart and torn down with the effect, so a stale session can
    // never leak into the next one.
    let cancelled = false
    let timer: number | undefined
    let controller: AbortController | null = null
    let sessionId = ''
    let interval = 3000
    let failures = 0

    const schedule = (delay: number) => {
      if (cancelled) return
      timer = window.setTimeout(() => void poll(), delay)
    }

    async function poll(): Promise<void> {
      if (cancelled) return
      // A hidden tab is throttled to roughly one timer a minute, so polling
      // from it produces stale answers and a burst on resume. Stop, and let
      // the visibility listener restart the chain.
      if (document.visibilityState === 'hidden') return

      controller = new AbortController()
      try {
        const result = await api.qrPoll(sessionId, controller.signal)
        if (cancelled) return
        failures = 0

        if (result.status === 'approved' && result.access_token) {
          setToken(result.access_token)
          setState({ kind: 'approved' })
          return // Terminal: stop the chain.
        }
        if (result.status === 'expired') {
          setState({ kind: 'expired' })
          return // Terminal.
        }
        schedule(interval)
      } catch (error) {
        if (cancelled) return
        if (error instanceof DOMException && error.name === 'AbortError') return

        // A consumed or unknown session is a 404 and will never recover, so
        // treat it the same as expiry rather than retrying into the void.
        if (error instanceof ApiError && error.status === 404) {
          setState({ kind: 'expired' })
          return
        }

        failures += 1
        if (failures >= MAX_CONSECUTIVE_FAILURES) {
          setState({ kind: 'error', message: 'Lost contact with the tracker backend.' })
          return
        }
        // Back off so a cold Lambda or a brief outage is not met with a flood.
        schedule(Math.min(interval * BACKOFF_FACTOR ** failures, MAX_DELAY_MS))
      }
    }

    function onVisibilityChange() {
      if (cancelled) return
      window.clearTimeout(timer)
      // Resume with an immediate poll: the approval may have happened while
      // the tab was in the background.
      if (document.visibilityState === 'visible') schedule(0)
    }

    async function begin(): Promise<void> {
      setState({ kind: 'initializing' })
      try {
        const session = await api.qrInit()
        if (cancelled) return
        sessionId = session.session_id
        interval = session.poll_interval_seconds * 1000
        setState({
          kind: 'waiting',
          approveUrl: session.approve_url,
          expiresAt: session.expires_at,
        })
        schedule(interval)
      } catch (error) {
        if (cancelled) return
        setState({
          kind: 'error',
          message: error instanceof ApiError ? error.message : 'Could not start a login session.',
        })
      }
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    void begin()

    return () => {
      cancelled = true
      window.clearTimeout(timer)
      controller?.abort()
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [enabled, nonce, setToken])

  return { state, restart }
}
