import { Suspense, lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import { CreateHabit } from './routes/CreateHabit'
import { Dashboard } from './routes/Dashboard'
import { History } from './routes/History'
import { NotFound } from './routes/NotFound'
import { ScanQr } from './routes/ScanQr'

// The TV login route pulls in the QR renderer, which a Telegram user will
// never see. Splitting it keeps those bytes off the phone entirely.
const TvLogin = lazy(() => import('./routes/TvLogin').then((m) => ({ default: m.TvLogin })))

/**
 * Declarative routing: JSX routes under a layout, no loaders or actions.
 *
 * React Router's data and framework modes expect it to own the server and run
 * loaders there. Here the server is FastAPI on Lambda and this is a static SPA
 * on Vercel, so fetching belongs in components and stores.
 */
export function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* A path-less route is a layout wrapper: it renders chrome around
            every child via <Outlet /> without adding a URL segment. */}
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="habits/new" element={<CreateHabit />} />
          <Route path="history" element={<History />} />
          <Route path="scan" element={<ScanQr />} />
          <Route
            path="tv"
            element={
              <Suspense fallback={<p className="hint">Loading…</p>}>
                <TvLogin />
              </Suspense>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
