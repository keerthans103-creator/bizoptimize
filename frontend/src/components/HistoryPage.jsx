import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function HistoryPage({ isLoggedIn, onSelect, refreshKey }) {
  const [workflows, setWorkflows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoggedIn) {
      setWorkflows([]);
      return;
    }
    setLoading(true);
    api
      .listWorkflows()
      .then(setWorkflows)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [isLoggedIn, refreshKey]);

  return (
    <section className="panel">
      <h2>Saved workflows</h2>

      {!isLoggedIn && <p className="empty-state">Sign in from the sidebar to see your saved workflows.</p>}
      {isLoggedIn && error && <p className="error small">{error}</p>}
      {isLoggedIn && loading && <p className="muted small">Loading&hellip;</p>}
      {isLoggedIn && !loading && !error && workflows.length === 0 && (
        <p className="empty-state">No saved workflows yet. Run an analysis and save it to see it here.</p>
      )}

      {isLoggedIn && !loading && workflows.length > 0 && (
        <table className="history-table" style={{ marginTop: 12 }}>
          <thead>
            <tr>
              <th>Title</th>
              <th>Tasks</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map((w) => (
              <tr key={w.id} onClick={() => onSelect(w.id)}>
                <td>{w.title}</td>
                <td className="muted">{w.tasks?.length ?? 0}</td>
                <td>{new Date(w.createdAt).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
