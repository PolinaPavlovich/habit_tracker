import { Component, type ErrorInfo, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  message: string | null
}

/**
 * Last line of defence for a render-time throw.
 *
 * Without a boundary anywhere in the tree React unmounts the whole app on any
 * uncaught render error and the user is left staring at a blank white page with
 * no way back. This keeps the chrome and offers a reload.
 *
 * It catches *render* errors only — a rejected fetch is handled where it is
 * awaited, not here.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { message: null }

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    return { message: error instanceof Error ? error.message : 'Something went wrong.' }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.message === null) return this.props.children

    return (
      <section className="card">
        <p>Something went wrong displaying this screen.</p>
        <p className="hint">{this.state.message}</p>
        <button className="button" onClick={() => window.location.reload()}>
          Reload
        </button>
      </section>
    )
  }
}
