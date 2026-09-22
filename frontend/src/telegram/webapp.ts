/** Access to the Telegram WebApp object, and a stand-in for when there isn't one. */

import type { TelegramWebApp } from './types'

/** The real object, or undefined in an ordinary browser. */
export function getWebApp(): TelegramWebApp | undefined {
  return window.Telegram?.WebApp
}

const NOOP = () => {}

/**
 * A do-nothing WebApp used off-platform.
 *
 * Components ask for this rather than branching on `isTelegram` at every call
 * site. A Smart TV has no MainButton, so calling `show()` on it must be
 * harmless instead of a crash — the TV renders its own DOM button and this
 * shim absorbs the calls.
 */
const SHIM: TelegramWebApp = {
  initData: '',
  colorScheme: 'light',
  MainButton: {
    text: '',
    isVisible: false,
    setText: NOOP,
    show: NOOP,
    hide: NOOP,
    enable: NOOP,
    disable: NOOP,
    showProgress: NOOP,
    hideProgress: NOOP,
    onClick: NOOP,
    offClick: NOOP,
  },
  BackButton: { isVisible: false, show: NOOP, hide: NOOP, onClick: NOOP, offClick: NOOP },
  ready: NOOP,
  expand: NOOP,
  close: NOOP,
  setHeaderColor: NOOP,
  // Off-platform there is no native dialog, so fall back to the browser's.
  showAlert: (message, callback) => {
    window.alert(message)
    callback?.()
  },
  showScanQrPopup: NOOP,
  closeScanQrPopup: NOOP,
}

/** Always returns something callable. */
export function webApp(): TelegramWebApp {
  return getWebApp() ?? SHIM
}
