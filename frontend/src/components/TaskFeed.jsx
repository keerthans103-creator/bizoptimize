import { useEffect, useMemo, useState } from "react";
import AutomationPanel from "./AutomationPanel.jsx";
import CodeGenerator from "./CodeGenerator.jsx";
import SwipeCard from "./SwipeCard.jsx";
import { CheckIcon, XIcon } from "./icons.jsx";

const THRESHOLD = 70;
const TINT_MAX_DRAG = 160;

export default function TaskFeed({ tasks, decisions, onDecide, onRestartDecisions, onExit }) {
  const allQualifying = useMemo(() => tasks.filter((t) => t.score >= THRESHOLD), [tasks]);
  // Snapshot which tasks still need a decision ONCE per session (dependency
  // array intentionally omits `decisions`). Re-filtering this on every new
  // decision would shrink the array out from under `index` mid-swipe -- the
  // task at candidates[index] would silently change to a different one, or
  // index would run past the new shorter length. New decisions made during
  // this session should only advance `index`, not resize this list; only a
  // fresh mount (new Feed session) should re-derive it from current decisions.
  const [sessionKey, setSessionKey] = useState(0);
  const candidates = useMemo(
    () => allQualifying.filter((t) => !decisions[t.text]),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [allQualifying, sessionKey]
  );
  const [index, setIndex] = useState(0);
  const [dragX, setDragX] = useState(0);

  const current = candidates[index];
  const next = candidates[index + 1];
  const done = index >= candidates.length;

  const handleDecide = (decision) => {
    setDragX(0);
    onDecide(current.text, decision);
    setIndex((i) => i + 1);
  };

  const restart = () => {
    onRestartDecisions();
    setIndex(0);
    setDragX(0);
    setSessionKey((k) => k + 1);
  };

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === "Escape") onExit();
      if (allQualifying.length === 0 || done) return;
      if (e.key === "ArrowRight") handleDecide("automate");
      if (e.key === "ArrowLeft") handleDecide("skip");
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, done]);

  const automateList = allQualifying.filter((t) => decisions[t.text] === "automate");
  const skippedCount = allQualifying.length - automateList.length;

  const tintOpacity = Math.min(Math.abs(dragX) / TINT_MAX_DRAG, 0.5);
  const tintStyle = {
    opacity: tintOpacity,
    background: dragX > 0 ? "var(--success)" : "var(--danger)",
  };

  return (
    <div className="feed-overlay">
      {!done && candidates.length > 0 && <div className="feed-tint" style={tintStyle} />}

      <div className="feed-topbar">
        <span className="feed-progress">
          {candidates.length === 0 ? "0 / 0" : `${Math.min(index + 1, candidates.length)} / ${candidates.length}`}
        </span>
        <button className="icon-button feed-exit" onClick={onExit} aria-label="Exit feed">
          <XIcon size={16} />
        </button>
      </div>

      {allQualifying.length === 0 ? (
        <div className="feed-empty">
          <p className="feed-task-text">No tasks scored {THRESHOLD}%+ yet.</p>
          <p className="muted small">
            Automation instructions only exist for tasks that clear the threshold &mdash; nothing to
            decide on here.
          </p>
        </div>
      ) : !done ? (
        <div className="swipe-stack">
          <div className={`feed-hint-banner ${index > 0 ? "feed-hint-hidden" : ""}`}>
            <span className="feed-hint-skip">
              <XIcon size={13} /> Skip
            </span>
            <span className="feed-hint-divider">swipe or tap</span>
            <span className="feed-hint-automate">
              Automate <CheckIcon size={13} />
            </span>
          </div>
          {next && <SwipeCard task={next} interactive={false} />}
          <SwipeCard key={current.id ?? current.text} task={current} onDecide={handleDecide} onDragChange={setDragX} />
        </div>
      ) : (
        <div className="feed-summary">
          <h2 className="feed-summary-title">
            Automating {automateList.length} of {allQualifying.length}
          </h2>
          <p className="muted small" style={{ marginBottom: 22 }}>
            You reviewed {allQualifying.length} task{allQualifying.length === 1 ? "" : "s"} that qualified
            for automation &mdash; {automateList.length} automated, {skippedCount} skipped. Here's the plan
            for the ones you automated.
          </p>

          {automateList.length === 0 ? (
            <p className="muted">You skipped everything this round &mdash; exit and try again anytime.</p>
          ) : (
            <div className="feed-plan-list">
              {automateList.map((task, idx) => (
                <div className="feed-plan-item" key={task.id ?? idx}>
                  <div className="feed-plan-header">
                    <span className="score-pill score-high">{task.score}%</span>
                    <p className="task-text">{task.text}</p>
                  </div>
                  <AutomationPanel matches={task.automation} />
                  <CodeGenerator taskText={task.text} />
                </div>
              ))}
            </div>
          )}

          <button className="btn-secondary" onClick={restart} style={{ marginTop: 22 }}>
            Start over
          </button>
        </div>
      )}
    </div>
  );
}
