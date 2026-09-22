/** Local-calendar date helpers. */

/**
 * Today in `YYYY-MM-DD`, in the *viewer's* timezone.
 *
 * `toISOString()` is deliberately avoided: it converts to UTC first, so anyone
 * east of Greenwich late in the evening would log against tomorrow's date, and
 * anyone west of it early in the morning against yesterday's.
 */
export function todayISO(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

/**
 * Parse `YYYY-MM-DD` as a *local* date.
 *
 * `new Date('2026-09-16')` is specified to parse as UTC midnight, which in any
 * timezone behind UTC renders as the 15th. Building the date from its parts
 * keeps it on the calendar day it says.
 */
export function parseISODate(iso: string): Date {
  const [year = 0, month = 1, day = 1] = iso.split('-').map(Number)
  return new Date(year, month - 1, day)
}

/** `YYYY-MM-DD`, `offset` days after `iso`. */
export function addDaysISO(iso: string, offset: number): string {
  const date = parseISODate(iso)
  date.setDate(date.getDate() + offset)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/**
 * Short weekday name, matching the `label` the backend sends.
 *
 * Only used for habits the summary omitted entirely — those the backend never
 * built buckets for — so the two labelling paths meet only at the boundary
 * between a habit with entries and one without.
 */
export function weekdayLabel(iso: string): string {
  return parseISODate(iso).toLocaleDateString('en-US', { weekday: 'short' })
}
