import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { StateStorage } from 'zustand/middleware'

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
 * localStorage that cannot throw.
 *
 * Storage access raises rather than returning null in a private window, with
 * site data blocked, and inside some embedded webviews. An unguarded read in
 * the persist middleware would take the whole app down before first paint, so
 * every call falls back to an in-memory map — which behaves exactly like the
 * old non-persisted store, and is the right degradation.
 */
const memoryFallback = new Map<string, string>()

const safeStorage: StateStorage = {
  getItem: (name) => {
    try {
      return localStorage.getItem(name)
    } catch {
      return memoryFallback.get(name) ?? null
    }
  },
  setItem: (name, value) => {
    try {
      localStorage.setItem(name, value)
    } catch {
      memoryFallback.set(name, value)
    }
  },
  removeItem: (name) => {
    try {
      localStorage.removeItem(name)
    } catch {
      memoryFallback.delete(name)
    }
  },
}

/**
 * Where a TV or browser's access token lives.
 *
 * **This persists a bearer token to localStorage, which is a deliberate and
 * explicitly accepted security trade.** Anything running on this origin can
 * read it, and on a shared living-room device it survives until it expires.
 * The alternative — the in-memory store this replaces — forced a fresh QR scan
 * on every page refresh, which was judged the worse problem. Revisit this if
 * the token ever grants more than one account's habit data.
 *
 * `initData` is never stored: Telegram reissues it on every launch, so the
 * Mini App has nothing worth keeping.
 */
export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set) => ({
      token: null,
      setToken: (token) => set({ token }),
      clearToken: () => set({ token: null }),
    }),
    {
      // Versioned key: a future change to what is stored can bump this and
      // leave the old value to be ignored rather than misread.
      name: 'habit-tracker-auth:v1',
      version: 1,
      storage: createJSONStorage(() => safeStorage),
      // Only the token. Actions are functions and must never be serialised.
      partialize: (state) => ({ token: state.token }),
    },
  ),
)

/**
 * The `Authorization` header value for this device, or null when unauthenticated.
 *
 * Inside Telegram the signed `initData` always wins — it is re-issued on every
 * launch and needs no storage. Elsewhere it falls back to a QR-issued bearer
 * token, which now survives a reload.
 */
export function authHeader(): string | null {
  const initData = getWebApp()?.initData
  if (initData) return `tma ${initData}`

  const { token } = useAuthStore.getState()
  return token ? `Bearer ${token}` : null
}
