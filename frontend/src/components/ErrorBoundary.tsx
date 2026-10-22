import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  failed: boolean;
}

/** Catches unexpected rendering errors so the user sees a message instead of a blank page. */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unexpected UI error", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="app-main" role="alert">
        <h1>Something went wrong</h1>
        <p>An unexpected error occurred. Reloading the page usually fixes it.</p>
        <button type="button" className="btn" onClick={() => window.location.reload()}>
          Reload page
        </button>
      </main>
    );
  }
}
