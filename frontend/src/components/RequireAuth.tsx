import { Navigate, Outlet } from 'react-router-dom'

import { isTelegram } from '../lib/platform'
import { useAuthStore } from '../stores/authStore'

/**
 * Gate for routes that need a credential.
 *
 * Without this the dashboard mounts and fetches unconditionally, so a plain
 * browser with nothing to authenticate with sends a bare request and renders
 * the backend's 401 as if it were a failure. It is not a failure — the device
 * simply has not been logged in yet, and the QR screen is where that happens.
 *
 * The token is read through the store hook rather than `authHeader()` so this
 * re-renders the moment a QR approval lands; a plain function call would leave
 * the user stranded on /tv after a successful scan.
 */
export function RequireAuth() {
  const token = useAuthStore((store) => store.token)

  // Inside Telegram there is always a signed initData, so the gate is open.
  if (!isTelegram && !token) return <Navigate to="/tv" replace />

  return <Outlet />
}
