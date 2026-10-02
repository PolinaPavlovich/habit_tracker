import { useState } from 'react'

import { ApiError } from '../lib/api'
import { isTelegram } from '../lib/platform'
import { useBackButton } from '../telegram/useBackButton'
import { useMainButton } from '../telegram/useMainButton'

interface HabitFormProps {
  /** Present when editing. The form then stays disabled until something differs. */
  initial?: { name: string; unit: string }
  submitLabel: string
  savingLabel: string
  /** Shown when the failure is not one the form knows how to word. */
  fallbackError: string
  /** Receives trimmed values. Reject with an `ApiError` to show it in the form. */
  onSubmit: (name: string, unit: string) => Promise<void>
  onCancel: () => void
}

/**
 * The name + unit form shared by creating and editing a habit.
 *
 * It owns Telegram's MainButton, so only one may be mounted at a time.
 */
export function HabitForm({
  initial,
  submitLabel,
  savingLabel,
  fallbackError,
  onSubmit,
  onCancel,
}: HabitFormProps) {
  const [name, setName] = useState(initial?.name ?? '')
  const [unit, setUnit] = useState(initial?.unit ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const trimmedName = name.trim()
  const trimmedUnit = unit.trim()
  const filled = trimmedName.length > 0 && trimmedUnit.length > 0
  const changed = !initial || trimmedName !== initial.name || trimmedUnit !== initial.unit
  const ready = filled && changed

  async function submit() {
    if (!ready || saving) return
    setSaving(true)
    setError(null)
    try {
      await onSubmit(trimmedName, trimmedUnit)
    } catch (cause) {
      // 409 is the backend telling us this name is already taken for this
      // account — a normal outcome worth wording properly, not a crash.
      if (cause instanceof ApiError && cause.status === 409) {
        setError(`You already have a habit called "${trimmedName}".`)
      } else {
        setError(cause instanceof ApiError ? cause.message : fallbackError)
      }
      setSaving(false)
    }
  }

  // Native Telegram chrome. Off-platform both calls land on the shim and the
  // DOM buttons below carry the flow instead.
  useMainButton({
    text: submitLabel,
    enabled: ready && !saving,
    loading: saving,
    onClick: () => void submit(),
  })
  useBackButton(onCancel)

  return (
    <section className="card">
      <label className="hint" htmlFor="habit-name">
        Name
      </label>
      <div className="row">
        <input
          id="habit-name"
          type="text"
          value={name}
          maxLength={100}
          placeholder="Running"
          onChange={(event) => setName(event.target.value)}
        />
      </div>

      <label className="hint" htmlFor="habit-unit">
        Unit
      </label>
      <div className="row">
        <input
          id="habit-unit"
          type="text"
          value={unit}
          maxLength={32}
          placeholder="km"
          onChange={(event) => setUnit(event.target.value)}
        />
      </div>

      {error && <p className="draft-error">{error}</p>}

      {/* A Smart TV has no MainButton and is driven by a D-pad, so it needs
          real focusable controls. */}
      {!isTelegram && (
        <div className="row">
          <button className="button" disabled={!ready || saving} onClick={() => void submit()}>
            {saving ? savingLabel : submitLabel}
          </button>
          <button className="button button--quiet" onClick={onCancel}>
            Cancel
          </button>
        </div>
      )}
    </section>
  )
}
