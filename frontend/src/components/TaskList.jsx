import TaskRow from "./TaskRow.jsx";

const THRESHOLD = 70;

export default function TaskList({ tasks, decisions = {}, onSavingsChange, onPersistSavings }) {
  if (!tasks || tasks.length === 0) return null;

  const automatableCount = tasks.filter((t) => t.score >= THRESHOLD).length;

  return (
    <section className="panel">
      <h2>Ranked tasks</h2>
      <p className="muted small" style={{ marginTop: 0 }}>
        {automatableCount > 0
          ? `${automatableCount} of ${tasks.length} score ${THRESHOLD}%+ — head to Feed to decide which ones to actually automate.`
          : `None of these score ${THRESHOLD}%+ yet, so there's nothing to automate here.`}
      </p>
      <div className="task-table-wrap" style={{ marginTop: 8 }}>
        <table className="task-table">
          <thead>
            <tr>
              <th className="col-score">Score</th>
              <th>Task</th>
              <th className="col-num">Hours/wk</th>
              <th className="col-num">Rate ($)</th>
              <th className="col-num">Est. savings</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task, idx) => (
              <TaskRow
                key={task.id ?? idx}
                task={task}
                decision={decisions[task.text]}
                onSavingsChange={onSavingsChange}
                onPersistSavings={onPersistSavings}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
