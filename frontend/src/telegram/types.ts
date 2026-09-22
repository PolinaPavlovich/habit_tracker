/**
 * Hand-written types for the Telegram WebApp surface this app actually uses.
 *
 * Deliberately not the official SDK package: we need roughly a dozen members,
 * and the script itself has to come from telegram.org at runtime anyway, so a
 * dependency would add bundle weight without adding capability.
 */

export interface TelegramMainButton {
  text: string
  isVisible: boolean
  setText(text: string): void
  show(): void
  hide(): void
  enable(): void
  disable(): void
  showProgress(leaveActive?: boolean): void
  hideProgress(): void
  /** Registers a listener. Telegram keeps every one it is given. */
  onClick(callback: () => void): void
  /** Removes a listener **by reference**. A different function removes nothing. */
  offClick(callback: () => void): void
}

export interface TelegramBackButton {
  isVisible: boolean
  show(): void
  hide(): void
  onClick(callback: () => void): void
  offClick(callback: () => void): void
}

export interface TelegramWebApp {
  /** Signed payload. Empty string outside Telegram. */
  initData: string
  colorScheme: 'light' | 'dark'
  MainButton: TelegramMainButton
  BackButton: TelegramBackButton
  ready(): void
  expand(): void
  close(): void
  setHeaderColor(color: string): void
  showAlert(message: string, callback?: () => void): void
  /**
   * Opens the native scanner. The callback fires for **every** decoded frame
   * and must return `true` to close the popup; returning anything falsy leaves
   * it open and scanning.
   */
  showScanQrPopup(params: { text?: string }, callback: (text: string) => boolean): void
  closeScanQrPopup(): void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}
