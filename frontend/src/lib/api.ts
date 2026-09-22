/**
 * The only place this app talks to the backend.
 *
 * Two rules the backend's history makes non-negotiable:
 *
 * 1. **No trailing slashes.** Collection routes are declared `""` server-side.
 *    Behind the Lambda Function URL a trailing slash is stripped before
 *    Starlette sees it, which once produced an infinite 307 redirect loop that
 *    surfaced to users as "backend unreachable".
 * 2. **Amounts stay strings.** See `lib/decimal`.
 */

import { API_BASE } from '../env'
import { authHeader } from '../stores/authStore'
import type {
  Activity,
  LogListItem,
  QrInitResponse,
  QrPollResponse,
  SummaryResponse,
} from './types'

/**
 * A failed API call.
 *
 * `status === null` means the request never reached the API at all — DNS,
 * offline, CORS, an aborted fetch. Callers branch on that to tell "the server
 * said no" apart from "we never got to ask".
 */
export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T | null> {
  const { method = 'GET', body, signal } = options

  const headers: Record<string, string> = {}
  const auth = authHeader()
  if (auth) headers['Authorization'] = auth
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (cause) {
    // An aborted request is a caller decision, not a failure to report.
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiError('Could not reach the tracker backend.', null)
  }

  if (!response.ok) {
    throw new ApiError(await describeFailure(response), response.status)
  }

  // DELETE answers 204 with no body, and `response.json()` on an empty body
  // throws a SyntaxError that would escape every catch above it. This guard is
  // the same one the Telegram bot's client needed for the same reason.
  if (response.status === 204) return null
  const text = await response.text()
  if (!text) return null
  return JSON.parse(text) as T
}

/** Pull FastAPI's `detail` out of an error body, falling back to the status. */
async function describeFailure(response: Response): Promise<string> {
  try {
    const payload: unknown = JSON.parse(await response.text())
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      const { detail } = payload as { detail: unknown }
      if (typeof detail === 'string') return detail
      // 422 bodies carry a list of field errors rather than a sentence.
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: unknown }
        if (typeof first?.msg === 'string') return first.msg
      }
    }
  } catch {
    // Fall through to the generic message below.
  }
  return `Request failed (${response.status}).`
}

/** Narrow the nullable result for endpoints that always return a body. */
async function requireBody<T>(path: string, options?: RequestOptions): Promise<T> {
  const result = await request<T>(path, options)
  if (result === null) throw new ApiError('The backend returned an empty response.', null)
  return result
}

export const api = {
  listActivities: (signal?: AbortSignal) =>
    requireBody<Activity[]>('/activities', { signal }),

  createActivity: (name: string, unit: string) =>
    requireBody<Activity>('/activities', { method: 'POST', body: { name, unit } }),

  getSummary: (days: number, signal?: AbortSignal) =>
    requireBody<SummaryResponse>(`/logs/summary?days=${days}`, { signal }),

  listLogs: (limit: number, offset: number, signal?: AbortSignal) =>
    requireBody<LogListItem[]>(`/logs?limit=${limit}&offset=${offset}`, { signal }),

  /** `amount` is a decimal string — stringifying a number here would defeat the point. */
  createLog: (activityId: number, amount: string, date?: string) =>
    requireBody<{ id: number }>('/logs', {
      method: 'POST',
      body: { activity_id: activityId, amount, ...(date ? { date } : {}) },
    }),

  deleteLog: (logId: number) => request<null>(`/logs/${logId}`, { method: 'DELETE' }),

  qrInit: () => requireBody<QrInitResponse>('/qr-auth/init', { method: 'POST' }),

  qrPoll: (sessionId: string, signal?: AbortSignal) =>
    requireBody<QrPollResponse>(`/qr-auth/poll/${sessionId}`, { signal }),

  qrApprove: (sessionId: string) =>
    requireBody<{ status: string }>(`/qr-auth/approve/${sessionId}`, { method: 'POST' }),
}
