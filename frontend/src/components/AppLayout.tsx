import { NavLink, Outlet } from 'react-router-dom'

import { isTelegram } from '../lib/platform'

export function AppLayout() {
  return (
    <div className="app">
      <nav className="nav">
        {/* `end` stops the dashboard link matching every nested route. */}
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : undefined)}>
          Today
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => (isActive ? 'active' : undefined)}>
          History
        </NavLink>
        <NavLink to="/habits/new" className={({ isActive }) => (isActive ? 'active' : undefined)}>
          New habit
        </NavLink>
        {/* Scanning needs Telegram's native camera; the TV is the thing being
            scanned, so it never shows this. */}
        {isTelegram && (
          <NavLink to="/scan" className={({ isActive }) => (isActive ? 'active' : undefined)}>
            Log in a TV
          </NavLink>
        )}
      </nav>
      <Outlet />
    </div>
  )
}
