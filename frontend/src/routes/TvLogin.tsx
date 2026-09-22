import { QRCodeSVG } from 'qrcode.react'
import { Link, Navigate } from 'react-router-dom'

import { useQrSession } from '../hooks/useQrSession'
import { isTelegram } from '../lib/platform'

/**
 * The screen a Smart TV shows while it waits to be logged in.
 *
 * Lazy-loaded from the router, so a phone inside Telegram never downloads this
 * route or the QR renderer it pulls in.
 */
export function TvLogin() {
  // Inside Telegram there is already a signed identity; this flow is for
  // devices that have none.
  const { state, restart } = useQrSession(!isTelegram)

  if (isTelegram) return <Navigate to="/" replace />

  if (state.kind === 'approved') {
    return (
      <div className="qr">
        <p>This device is logged in.</p>
        <Link className="button" to="/">
          Open my habits
        </Link>
      </div>
    )
  }

  if (state.kind === 'expired') {
    return (
      <div className="qr">
        <p className="hint">That code expired before it was scanned.</p>
        <button className="button" onClick={restart}>
          Show a new code
        </button>
      </div>
    )
  }

  if (state.kind === 'error') {
    return (
      <div className="qr">
        <p className="hint">{state.message}</p>
        <button className="button" onClick={restart}>
          Try again
        </button>
      </div>
    )
  }

  if (state.kind === 'initializing') {
    return (
      <div className="qr">
        <p className="hint">Preparing a login code…</p>
      </div>
    )
  }

  return (
    <div className="qr">
      <p>Scan this with the Telegram app on your phone.</p>
      {/* Always on a white ground regardless of theme — a dark background
          behind a QR code defeats most scanners. */}
      <div className="qr__frame">
        <QRCodeSVG value={state.approveUrl} size={220} level="M" />
      </div>
      <p className="hint">Open the habit tracker bot, then tap “Log in a TV”.</p>
      <button className="button button--quiet" onClick={restart}>
        Show a new code
      </button>
    </div>
  )
}
