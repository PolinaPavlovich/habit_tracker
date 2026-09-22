import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { ApiError, api } from '../lib/api'
import { isTelegram } from '../lib/platform'
import { webApp } from '../telegram/webapp'

/**
 * Matches the session id inside a scanned deep link.
 *
 * Hoisted to module scope: rebuilding a regexp inside the scan callback would
 * recompile it for every decoded camera frame.
 */
const SESSION_PATTERN = /startapp=qr_([0-9a-fA-F]{32})/

/** The phone half of QR login: scan a TV's code and approve it. */
export function ScanQr() {
  const [busy, setBusy] = useState(false)

  // Closing the scanner on unmount matters: navigating away with the popup
  // open leaves the camera running over the next screen.
  useEffect(() => () => webApp().closeScanQrPopup(), [])

  if (!isTelegram) return <Navigate to="/tv" replace />

  function openScanner() {
    const tg = webApp()
    setBusy(true)

    tg.showScanQrPopup({ text: 'Point at the code on your TV' }, (text) => {
      const match = SESSION_PATTERN.exec(text)
      if (!match?.[1]) {
        tg.showAlert('That does not look like a habit tracker login code.')
        // Falsy keeps the scanner open so the user can try another code.
        return false
      }

      void approve(match[1], tg)
      // True closes the popup. Returning anything falsy here leaves it
      // scanning and re-firing this callback on every subsequent frame.
      return true
    })
  }

  async function approve(sessionId: string, tg: ReturnType<typeof webApp>) {
    try {
      await api.qrApprove(sessionId)
      tg.showAlert('Your TV is now logged in.')
    } catch (cause) {
      const status = cause instanceof ApiError ? cause.status : null
      tg.showAlert(
        status === 404
          ? 'That code has expired or was already used. Ask the TV for a new one.'
          : 'Could not approve that code. Please try again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <p>Log a TV or browser into your account by scanning the code it shows.</p>
      <div className="row">
        <button className="button" disabled={busy} onClick={openScanner}>
          {busy ? 'Scanning…' : 'Scan a login code'}
        </button>
      </div>
    </section>
  )
}
