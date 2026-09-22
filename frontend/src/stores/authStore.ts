import { create } from 'zustand'

import { getWebApp } from '../telegram/webapp'

interface AuthState {
  /** Token issued to this device after a QR approval. */
  token: string | null
}

interface AuthActions {
  setToken(token: string): void
  clearToken(): void
}

/**
 * Where a TV's access token lives: in memory, for the lifetime of the tab.
 *
 * Deliberately not wrapped in `persist`. Tokens do not belong in
 * `localStorage` — anything on the page can read it, and a shared living-room
 * device is exactly the wrong place to leave a month-long credential lying
 * around. The cost is that reloading the TV means scanning again, which is
 * accepted.
 */
export const useAuthStore = create<AuthState & AuthActions>()((set) => ({
  token: null,
  setToken: (token) => set({ token }),
  clearToken: () => set({ token: null }),
}))

/**
 * The `Authorization` header value for this device, or null when unauthenticated.
 *
 * Inside Telegram the signed `initData` is always preferred — it is re-issued
 * by Telegram on every launch and needs no storage. Elsewhere it falls back to
 * a QR-issued bearer token.
 */
export function authHeader(): string | null {
  const initData = getWebApp()?.initData
  if (initData) return `tma ${initData}`

  const { token } = useAuthStore.getState()
  return token ? `Bearer ${token}` : null
}
