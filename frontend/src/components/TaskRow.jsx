import { useState } from "react";
import { BoltIcon } from "./icons.jsx";

const THRESHOLD = 70;

function scoreColor(score) {
  if (score >= THRESHOLD) return "score-high";
  if (score >= 40) return "score-medium";
  return "score-low";
}

function estimateSavings(hoursPerWeek, hourlyRate, score) {
  if (!hoursPerWeek || !hourlyRate) return null;
  return Math.round(hoursPerWeek * 52 * hourlyRate * (score / 100) * 100) / 100;
}

export default function TaskRow({ task, decision, onSavingsChange, onPersistSavings }) {
  const [hours, setHours] = useState(task.hoursPerWeek ?? "");
  const [rate, setRate] = useState(task.hourlyRate ?? "");

  const liveEstimate =
    task.estimatedAnnualSavings ?? estimateSavings(Number(hours), Number(rate), task.score);

  const handleBlur = () => {
    const h = Number(hours);
    const r = Number(rate);
    if (!h || !r) return;
    onSavingsChange?.(task, h, r);
    if (task.id) onPersistSavings?.(task.id, h, r);
  };

  return (
    <tr className="task-row">
      <td className="col-score">
        <span className={`score-pill ${scoreColor(task.score)}`}>{task.score}%</span>
      </td>
      <td>
        <p className="task-text">{task.text}</p>
        {task.hint && (
          <span className="hint-chip">
            <BoltIcon size={11} />
            {task.hint}
          </span>
        )}
        {decision && (
          <span className={`decision-badge decision-${decision}`}>
            {decision === "automate" ? "Marked to automate" : "Skipped in Feed"}
          </span>
        )}
      </td>
      <td className="col-num">
        <input
          className="table-input"
          type="number"
          min="0"
          step="0.5"
          placeholder="0"
          value={hours}
          onChange={(e) => setHours(e.target.value)}
          onBlur={handleBlur}
        />
      </td>
      <td className="col-num">
        <input
          className="table-input"
          type="number"
          min="0"
          step="1"
          placeholder="0"
          value={rate}
          onChange={(e) => setRate(e.target.value)}
          onBlur={handleBlur}
        />
      </td>
      <td className="col-num">
        {liveEstimate != null ? (
          <span className="savings-value">${liveEstimate.toLocaleString()}</span>
        ) : (
          <span className="muted small">&mdash;</span>
        )}
      </td>
    </tr>
  );
}
