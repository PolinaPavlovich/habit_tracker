/**
 * Build-time configuration.
 *
 * Only `VITE_`-prefixed variables are exposed to client code by Vite, and
 * everything so exposed is **public** — it is inlined into the shipped bundle
 * and readable by anyone. Nothing secret belongs here; in particular
 * `INTERNAL_API_KEY` must never be given a `VITE_` prefix.
 */

const rawBase = import.meta.env.VITE_API_URL

if (!rawBase) {
  // Failing at module load beats failing on the first request, where it would
  // surface as an unexplained fetch error against the string "undefined".
  throw new Error('VITE_API_URL is not set. Copy .env.example and fill it in.')
}

/**
 * API base with any trailing slashes removed.
 *
 * Paths are always written `/activities`, so a base ending in `/` would produce
 * `//activities`. Trailing slashes are not cosmetic here: behind the Lambda
 * Function URL they were the cause of a production redirect loop.
 */
export const API_BASE: string = rawBase.replace(/\/+$/, '')
