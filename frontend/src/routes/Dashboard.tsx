import { Link } from 'react-router-dom'

import { HabitCard } from '../components/HabitCard'
import { useDashboardData } from '../hooks/useDashboardData'

export function Dashboard() {
  const { state, reload } = useDashboardData()

  if (state.kind === 'loading') return <p className="hint">Loading your habits…</p>
  if (state.kind === 'error') {
    return (
      <>
        <p className="hint">{state.message}</p>
        <button className="button" onClick={reload}>
          Try again
        </button>
      </>
    )
  }

  if (state.habits.length === 0) {
    return (
      <>
        <p className="hint">No habits yet. Create one to start tracking.</p>
        <Link className="button" to="/habits/new">
          New habit
        </Link>
      </>
    )
  }

  return (
    <>
      {state.habits.map((habit) => (
        <HabitCard key={habit.activityId} habit={habit} onLogged={reload} />
      ))}
    </>
  )
}
