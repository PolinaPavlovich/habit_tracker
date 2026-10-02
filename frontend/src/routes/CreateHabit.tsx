import { useNavigate } from 'react-router-dom'

import { HabitForm } from '../components/HabitForm'
import { api } from '../lib/api'

export function CreateHabit() {
  const navigate = useNavigate()

  return (
    <HabitForm
      submitLabel="Create habit"
      savingLabel="Creating…"
      fallbackError="Could not create that habit."
      onSubmit={async (name, unit) => {
        await api.createActivity(name, unit)
        navigate('/')
      }}
      onCancel={() => navigate(-1)}
    />
  )
}
