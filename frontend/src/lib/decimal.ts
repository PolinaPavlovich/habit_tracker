/**
 * Decimal amounts as strings, never as numbers.
 *
 * The API stores amounts in a PostgreSQL `Numeric(10, 2)` and serialises them
 * as JSON strings for a reason: routing them through a JavaScript `number`
 * reintroduces binary floating-point drift — `0.1 + 0.2` is famously not `0.3`
 * — which is exactly what that column type exists to prevent. So nothing here
 * ever calls `Number()` on an amount. Arithmetic happens in integer cents via
 * `bigint`, and the string form is what crosses the wire in both directions.
 */

/** `Numeric(10, 2)` allows ten significant digits, two of them after the point. */
const AMOUNT_PATTERN = /^\d{1,8}(\.\d{1,2})?$/

export const ZERO = '0.00'

/** Parse a decimal string into integer cents. Throws on anything malformed. */
export function toCents(amount: string): bigint {
  const trimmed = amount.trim()
  if (!AMOUNT_PATTERN.test(trimmed)) {
    throw new Error(`Not a valid amount: ${amount}`)
  }
  const [whole = '0', fraction = ''] = trimmed.split('.')
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'))
}

/** Render integer cents back as a two-decimal string. */
export function fromCents(cents: bigint): string {
  const negative = cents < 0n
  const absolute = negative ? -cents : cents
  const whole = absolute / 100n
  const fraction = (absolute % 100n).toString().padStart(2, '0')
  return `${negative ? '-' : ''}${whole}.${fraction}`
}

/** Sum decimal strings exactly. Unparseable entries are skipped, not coerced. */
export function sumAmounts(amounts: readonly string[]): string {
  let total = 0n
  for (const amount of amounts) {
    try {
      total += toCents(amount)
    } catch {
      // A malformed amount contributes nothing rather than poisoning the total
      // with NaN, which is what Number() would have produced.
    }
  }
  return fromCents(total)
}

/** Normalise user input to the wire format, or return null if it is not usable. */
export function normaliseAmount(input: string): string | null {
  const trimmed = input.trim().replace(',', '.')
  if (!AMOUNT_PATTERN.test(trimmed)) return null
  const cents = toCents(trimmed)
  return cents > 0n ? fromCents(cents) : null
}

/** Drop a trailing `.00` for display only. Never use the result in a request. */
export function forDisplay(amount: string): string {
  return amount.endsWith('.00') ? amount.slice(0, -3) : amount
}
