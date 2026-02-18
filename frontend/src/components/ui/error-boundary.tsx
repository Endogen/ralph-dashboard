import { Component, type ErrorInfo, type ReactNode } from "react"

type ErrorBoundaryProps = {
  children: ReactNode
  fallback?: ReactNode
}

type ErrorBoundaryState = {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("[ErrorBoundary]", error, errorInfo)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-4 rounded-xl border border-rose-500/20 bg-rose-500/5 p-8">
          <div className="text-center">
            <h2 className="text-lg font-semibold text-rose-600 dark:text-rose-400">
              Something went wrong
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {this.state.error?.message ?? "An unexpected error occurred."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="rounded-md border bg-background px-4 py-2 text-sm font-medium hover:bg-background/80"
          >
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
