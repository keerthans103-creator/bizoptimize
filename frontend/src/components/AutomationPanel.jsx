export default function AutomationPanel({ matches }) {
  if (!matches || matches.length === 0) {
    return <p className="muted small">No automation scripts retrieved for this task.</p>;
  }

  return (
    <div className="automation-panel">
      {matches.map((match) => (
        <div key={match.id} className="automation-entry">
          <div className="automation-entry-header">
            <strong>{match.title}</strong>
            <span className="tag">{match.category}</span>
            <span className="similarity">{(match.similarity * 100).toFixed(0)}% match</span>
          </div>
          <p>{match.instructions}</p>
          <div className="tags">
            {match.tags.map((tag) => (
              <span key={tag} className="tag-chip">
                {tag}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
