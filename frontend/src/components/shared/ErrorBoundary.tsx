import { Component, type ErrorInfo, type PropsWithChildren, type ReactNode } from "react";

type State = { hasError: boolean };

export class ErrorBoundary extends Component<PropsWithChildren, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Deliberately do not send note or transcript content to telemetry.
    void error;
    void info;
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return <div className="error-boundary" role="alert"><h1>Workspace unavailable</h1><p>The interface encountered an unexpected error. Backend records were not changed.</p><button onClick={() => this.setState({ hasError: false })}>Try again</button></div>;
    }
    return this.props.children;
  }
}
