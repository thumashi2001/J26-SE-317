import { Component } from 'react';

// Shows a readable message instead of a blank page if a screen crashes.
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="panel crash">
        <h2>This page hit a problem</h2>
        <p className="muted">{String(this.state.error.message || this.state.error)}</p>
        <button className="btn" onClick={() => window.location.assign('/')}>
          Back to home
        </button>
      </div>
    );
  }
}
