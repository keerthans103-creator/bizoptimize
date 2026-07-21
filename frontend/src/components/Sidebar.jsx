import AuthPanel from "./AuthPanel.jsx";
import { BoltIcon } from "./icons.jsx";

export default function Sidebar({ view, onNavigate, email, onAuthChange }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">
          <BoltIcon size={16} strokeWidth={2.2} />
        </div>
        <h1>BizOptimize AI</h1>
      </div>

      <nav className="sidebar-nav">
        <button
          className={`nav-item ${view === "analyze" ? "active" : ""}`}
          onClick={() => onNavigate("analyze")}
        >
          New analysis
        </button>
        <button
          className={`nav-item ${view === "feed" ? "active" : ""}`}
          onClick={() => onNavigate("feed")}
        >
          Feed
        </button>
        <button
          className={`nav-item ${view === "summary" ? "active" : ""}`}
          onClick={() => onNavigate("summary")}
        >
          Summary
        </button>
        <button
          className={`nav-item ${view === "history" ? "active" : ""}`}
          onClick={() => onNavigate("history")}
        >
          History
        </button>
      </nav>

      <div className="sidebar-footer">
        <p className="sidebar-version">v0.1.0</p>
        <AuthPanel email={email} onAuthChange={onAuthChange} />
      </div>
    </aside>
  );
}
