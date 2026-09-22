/**
 * Which shell the app is running inside.
 *
 * Decided once at module load rather than per render: the answer cannot change
 * during a session, and a component re-checking it would invite the value to
 * differ between two renders of the same tree.
 */

import { getWebApp } from '../telegram/webapp'

/**
 * True only when Telegram handed us a signed payload.
 *
 * Checked against non-empty `initData`, not merely `window.Telegram`. The
 * telegram-web-app.js script is loaded unconditionally by index.html, so the
 * object exists in an ordinary browser too — it just has nothing signed in it.
 * Treating the object's presence as proof would send the TV down the Mini App
 * path with no credential to offer.
 */
export const isTelegram: boolean = Boolean(getWebApp()?.initData)
