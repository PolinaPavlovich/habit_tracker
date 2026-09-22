import { useEffect, useRef } from 'react'

import { webApp } from './webapp'

/**
 * MainButton is a process-wide singleton owned by Telegram, not a React node.
 * If two mounted components both claim it they overwrite each other's text and
 * handler in whatever order they happened to mount, and unmounting one hides it
 * out from under the other. This token makes that collision visible in
 * development instead of leaving it as a mystery bug.
 */
let owner: symbol | null = null

interface MainButtonOptions {
  text: string
  onClick: () => void
  enabled?: boolean
  loading?: boolean
}

/**
 * Drive Telegram's native MainButton from a component.
 *
 * The registration effect runs on mount only, and never re-runs when `onClick`
 * changes identity. That matters because `offClick` unregisters **by
 * reference**: handing Telegram a fresh arrow function each render would mean
 * cleanup passes a function Telegram has never seen, the old listener survives,
 * and after two renders a single tap fires the handler twice — two journal
 * entries from one press. Keeping the caller's callback in a ref and
 * registering one stable wrapper avoids that entirely.
 */
export function useMainButton({ text, onClick, enabled = true, loading = false }: MainButtonOptions): void {
  const callbackRef = useRef(onClick)

  // No dependency array: refresh the target after every render so the stable
  // wrapper below always calls the current closure, never a stale one.
  useEffect(() => {
    callbackRef.current = onClick
  })

  useEffect(() => {
    const button = webApp().MainButton
    const handler = () => callbackRef.current()
    const token = Symbol('main-button')

    if (owner !== null && import.meta.env.DEV) {
      console.warn('[useMainButton] Two components are driving MainButton at once.')
    }
    owner = token

    button.onClick(handler)
    button.show()

    return () => {
      // Same reference that was registered, or Telegram keeps the listener.
      button.offClick(handler)
      // Hiding matters as much as unregistering: a button left visible bleeds
      // into the next screen, where its handler belongs to a dead component.
      button.hide()
      if (owner === token) owner = null
    }
  }, [])

  // Split per dependency rather than one effect watching all three: changing
  // the label should not re-run the enable/disable or progress calls.
  useEffect(() => {
    webApp().MainButton.setText(text)
  }, [text])

  useEffect(() => {
    const button = webApp().MainButton
    if (enabled) button.enable()
    else button.disable()
  }, [enabled])

  useEffect(() => {
    const button = webApp().MainButton
    if (loading) button.showProgress()
    else button.hideProgress()
  }, [loading])
}
