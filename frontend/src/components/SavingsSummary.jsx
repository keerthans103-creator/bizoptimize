const THRESHOLD = 70;

export default function SavingsSummary({ tasks, savingsByTask }) {
  if (!tasks || tasks.length === 0) return null;

  const avgScore = Math.round(tasks.reduce((sum, t) => sum + t.score, 0) / tasks.length);
  const automatableCount = tasks.filter((t) => t.score >= THRESHOLD).length;
  const automatablePct = Math.round((automatableCount / tasks.length) * 100);

  const totalAnnualSavings = tasks.reduce((sum, t) => {
    const persisted = t.estimatedAnnualSavings;
    const local = savingsByTask[t.text];
    return sum + (persisted ?? local ?? 0);
  }, 0);

  return (
    <section className="panel savings-summary">
      <h2>Savings dashboard</h2>
      <div className="summary-grid">
        <div className="summary-stat">
          <span className="summary-label">Avg. automatability</span>
          <span className="summary-value">{avgScore}%</span>
        </div>
        <div className="summary-stat">
          <span className="summary-label">
            Score {THRESHOLD}%+ ({automatableCount}/{tasks.length})
          </span>
          <span className="summary-value">{automatablePct}%</span>
        </div>
        <div className="summary-stat">
          <span className="summary-label">Projected annual savings</span>
          <span className="summary-value">${Math.round(totalAnnualSavings).toLocaleString()}</span>
        </div>
      </div>
      <p className="muted small summary-footnote">
        Savings = hours/week &times; 52 &times; hourly rate &times; (score / 100), summed across
        tasks where you've entered hours and rate.
      </p>
    </section>
  );
}
