import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <>
      <p className="hint">There is nothing at this address.</p>
      <Link className="button" to="/">
        Back to today
      </Link>
    </>
  )
}
