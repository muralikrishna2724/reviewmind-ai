import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center p-8">
          <div className="max-w-lg">
            <h1 className="text-lg font-bold text-red-400 mb-2">Something went wrong</h1>
            <pre className="text-xs text-gray-400 bg-gray-900 p-4 rounded overflow-auto">
              {(this.state.error as Error).message}
            </pre>
            <button
              onClick={() => this.setState({ error: null })}
              className="mt-4 px-4 py-2 bg-blue-700 text-white text-sm rounded"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
