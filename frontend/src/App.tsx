import { Suspense, lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import { RequireAuth } from './components/RequireAuth'
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
          {/* Another path-less layout route, this one a gate rather than
              chrome: everything nested under it needs a credential, and an
              unauthenticated browser is sent to /tv to earn one. */}
          <Route element={<RequireAuth />}>
            <Route index element={<Dashboard />} />
            <Route path="habits/new" element={<CreateHabit />} />
            <Route path="history" element={<History />} />
            {/* Telegram-only, and Telegram always satisfies the gate. */}
            <Route path="scan" element={<ScanQr />} />
          </Route>

          {/* Outside the gate: this is where an unauthenticated device lands. */}
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
