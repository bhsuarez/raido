import React from 'react'

type Props = {
  children: React.ReactNode
  fallback?: React.ReactNode
}

type State = { hasError: boolean; error?: Error }

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('UI ErrorBoundary caught:', error, info)
  }

  handleReload = () => {
    // Give the user a way to recover
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="card p-6">
            <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
            <p className="text-gray-300 mb-4">The page hit an error and was recovered.</p>
            {this.state.error?.message && (
              <pre className="bg-gray-900 text-red-300 p-3 rounded mb-4 overflow-auto text-sm">
                {this.state.error.message}
              </pre>
            )}
            <button className="btn-primary" onClick={this.handleReload}>Reload</button>
          </div>
        )
      )
    }
    return this.props.children
  }
}
