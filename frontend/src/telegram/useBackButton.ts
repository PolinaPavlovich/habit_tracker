import { useEffect, useRef } from 'react'

import { webApp } from './webapp'

/**
 * Drive Telegram's native BackButton.
 *
 * Same reference-identity hazard as MainButton, and the same fix: one stable
 * handler registered once, with the live callback held in a ref. Cleanup must
 * hide the button as well as unregister it — a BackButton left showing on a
 * screen that did not ask for one navigates from the wrong place.
 */
export function useBackButton(onClick: () => void): void {
  const callbackRef = useRef(onClick)

  useEffect(() => {
    callbackRef.current = onClick
  })

  useEffect(() => {
    const button = webApp().BackButton
    const handler = () => callbackRef.current()

    button.onClick(handler)
    button.show()

    return () => {
      button.offClick(handler)
      button.hide()
    }
  }, [])
}
