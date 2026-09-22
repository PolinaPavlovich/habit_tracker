import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError, api } from '../lib/api'
import { isTelegram } from '../lib/platform'
import { useBackButton } from '../telegram/useBackButton'
import { useMainButton } from '../telegram/useMainButton'

export function CreateHabit() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [unit, setUnit] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const ready = name.trim().length > 0 && unit.trim().length > 0

  async function submit() {
    if (!ready || saving) return
    setSaving(true)
    setError(null)
    try {
      await api.createActivity(name.trim(), unit.trim())
      navigate('/')
    } catch (cause) {
      // 409 is the backend telling us this name is already taken for this
      // account — a normal outcome worth wording properly, not a crash.
      if (cause instanceof ApiError && cause.status === 409) {
        setError(`You already have a habit called "${name.trim()}".`)
      } else {
        setError(cause instanceof ApiError ? cause.message : 'Could not create that habit.')
      }
      setSaving(false)
    }
  }

  // Native Telegram chrome. Off-platform both calls land on the shim and the
  // DOM buttons below carry the flow instead.
  useMainButton({
    text: 'Create habit',
    enabled: ready && !saving,
    loading: saving,
    onClick: () => void submit(),
  })
  useBackButton(() => navigate(-1))

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
            {saving ? 'Creating…' : 'Create habit'}
          </button>
          <button className="button button--quiet" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      )}
    </section>
  )
}
