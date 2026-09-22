/** Shapes the API returns. Amounts are strings; see `lib/decimal`. */

export interface Activity {
  id: number
  name: string
  unit: string
  created_at: string
}

export interface DailyBucket {
  /** Calendar date, `YYYY-MM-DD`. Used as a stable React key. */
  date: string
  /** Weekday label the chart shows on its axis, e.g. `Mon`. */
  label: string
  /** Decimal string. Never a number. */
  value: string
}

export interface ActivitySummary {
  activity_id: number
  activity_name: string
  unit: string
  total_amount: string
  entries_count: number
  /** Exactly seven entries for a seven-day window, zero-filled by the backend. */
  weekly_stats: DailyBucket[]
}

export interface SummaryResponse {
  period_start: string
  period_end: string
  days: number
  items: ActivitySummary[]
}

export interface LogListItem {
  id: number
  activity_id: number
  activity_name: string
  unit: string
  amount: string
  date: string
  notes: string | null
  created_at: string
}

export interface QrInitResponse {
  session_id: string
  approve_url: string
  expires_at: string
  poll_interval_seconds: number
}

export interface QrPollResponse {
  status: 'pending' | 'approved' | 'expired'
  access_token?: string | null
  token_type?: string | null
  expires_in?: number | null
}
