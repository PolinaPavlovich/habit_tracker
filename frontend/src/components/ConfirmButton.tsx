import { useState } from 'react'

interface ConfirmButtonProps {
  /** The first, harmless tap. */
  label: string
  /** What is about to be lost, shown beside the second tap. */
  prompt: string
  confirmLabel?: string
  /** Renders as a text-only button, for use inside a list row. */
  quiet?: boolean
  onConfirm: () => Promise<void>
}

/**
 * A destructive action that takes two taps.
 *
 * Inline rather than a modal on purpose. A modal needs focus trapping to be
 * usable with a TV remote, and Telegram's own `showConfirm` does not exist in
 * a plain browser. Two ordinary focusable buttons work everywhere this app
 * runs, and mirror the bot's two-tap delete.
 */
export function ConfirmButton({
  label,
  prompt,
  confirmLabel = 'Yes, delete',
  quiet = false,
  onConfirm,
}: ConfirmButtonProps) {
  const [armed, setArmed] = useState(false)
  const [busy, setBusy] = useState(false)

  const variant = quiet ? 'button button--quiet button--danger' : 'button button--danger'

  if (!armed) {
    return (
      <button className={variant} onClick={() => setArmed(true)}>
        {label}
      </button>
    )
  }

  async function confirm() {
    setBusy(true)
    try {
      await onConfirm()
    } finally {
      setBusy(false)
      setArmed(false)
    }
  }

  return (
    <div className="row row--wrap">
      <span className="hint">{prompt}</span>
      <button className="button button--danger" disabled={busy} onClick={() => void confirm()}>
        {busy ? 'Deleting…' : confirmLabel}
      </button>
      <button className="button button--quiet" disabled={busy} onClick={() => setArmed(false)}>
        Keep
      </button>
    </div>
  )
}
