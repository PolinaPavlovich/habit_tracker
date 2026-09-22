/**
 * One-time Telegram handshake, run as an import side effect.
 *
 * Imported by `main.tsx` *before* `createRoot`, and deliberately not placed in
 * a component's `useEffect`. Effects run twice under StrictMode in development
 * and again on every remount, so `ready()`/`expand()` would fire repeatedly;
 * a module body runs exactly once per page load. Off-platform every call lands
 * on the shim and does nothing.
 */

import { webApp } from './webapp'

const tg = webApp()

// Tells Telegram the interface is painted and it can drop its loading state.
tg.ready()
// Mini Apps open at roughly half height; without this the dashboard opens
// inside a short viewport the user has to drag upward.
tg.expand()
// Matches the native header to the theme the page is about to render.
tg.setHeaderColor('bg_color')
