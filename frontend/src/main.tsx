import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Imported for its side effects, and imported *first*: it performs the Telegram
// handshake exactly once at module-evaluation time. Putting ready()/expand() in
// a component effect would fire them twice under StrictMode and again on every
// remount.
import './telegram/init'
import './styles/theme.css'

import { App } from './App'

const container = document.getElementById('root')
if (!container) throw new Error('index.html is missing its #root element.')

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
