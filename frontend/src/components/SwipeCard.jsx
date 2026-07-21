import { useRef, useState } from "react";
import { CheckIcon, XIcon } from "./icons.jsx";

const THRESHOLD = 70;
const FLY_DISTANCE = 900;
const DECIDE_DISTANCE = 110;

function scoreColor(score) {
  if (score >= THRESHOLD) return "score-high";
  if (score >= 40) return "score-medium";
  return "score-low";
}

export default function SwipeCard({ task, onDecide, onDragChange, interactive = true }) {
  const cardRef = useRef(null);
  const dragState = useRef({ startX: 0, dragging: false });
  // Refs (not just state) for anything read inside finishDrag/fly: on a fast
  // swipe, pointerup can fire before React flushes the pointermove state
  // update, so reading `dragX`/`flying` state there sees a stale value and
  // the release silently springs back instead of registering the decision.
  // Refs update synchronously, so they're always current at call time.
  const dragXRef = useRef(0);
  const flyingRef = useRef(false);
  const [dragX, setDragX] = useState(0);
  const [flying, setFlying] = useState(false);

  if (!task) return null;

  const updateDrag = (value) => {
    dragXRef.current = value;
    setDragX(value);
    onDragChange?.(value);
  };

  const fly = (direction) => {
    if (flyingRef.current) return;
    flyingRef.current = true;
    setFlying(true);
    updateDrag(direction === "right" ? FLY_DISTANCE : -FLY_DISTANCE);
    setTimeout(() => onDecide(direction === "right" ? "automate" : "skip"), 200);
  };

  const handlePointerDown = (e) => {
    if (!interactive || flyingRef.current) return;
    dragState.current = { startX: e.clientX, dragging: true };
    cardRef.current?.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e) => {
    if (!interactive || !dragState.current.dragging) return;
    updateDrag(e.clientX - dragState.current.startX);
  };

  const finishDrag = () => {
    if (!interactive || !dragState.current.dragging) return;
    dragState.current.dragging = false;
    const finalDrag = dragXRef.current;
    if (finalDrag > DECIDE_DISTANCE) fly("right");
    else if (finalDrag < -DECIDE_DISTANCE) fly("left");
    else updateDrag(0);
  };

  // Buttons live inside the draggable card, so their own pointerdown must
  // never reach the card's handler -- otherwise setPointerCapture() on the
  // card hijacks the click event and the button silently does nothing.
  const stopForButton = (e) => e.stopPropagation();

  const style = interactive
    ? {
        transform: `translateX(${dragX}px) rotate(${dragX / 18}deg)`,
        transition: flying ? "transform 200ms ease-in" : dragState.current.dragging ? "none" : "transform 200ms ease-out",
      }
    : undefined;

  const automateOpacity = interactive ? Math.min(Math.max(dragX / DECIDE_DISTANCE, 0), 1) : 0;
  const skipOpacity = interactive ? Math.min(Math.max(-dragX / DECIDE_DISTANCE, 0), 1) : 0;

  return (
    <div
      className={`swipe-card ${interactive ? "" : "swipe-card-behind"}`}
      ref={cardRef}
      style={style}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={finishDrag}
      onPointerCancel={finishDrag}
    >
      {interactive && (
        <>
          <span className="swipe-stamp swipe-stamp-automate" style={{ opacity: automateOpacity }}>
            Automate
          </span>
          <span className="swipe-stamp swipe-stamp-skip" style={{ opacity: skipOpacity }}>
            Skip
          </span>
        </>
      )}

      <span className={`feed-score ${scoreColor(task.score)}`}>{task.score}%</span>
      <p className="feed-score-label">Automatability</p>
      <h2 className="feed-task-text">{task.text}</h2>
      {task.hint && <p className="feed-hint">{task.hint}</p>}
      <p className="feed-explanation">{task.explanation}</p>

      {interactive && (
        <div className="swipe-actions">
          <button
            className="swipe-btn swipe-btn-skip"
            onPointerDown={stopForButton}
            onClick={() => fly("left")}
            aria-label="Skip automating this"
          >
            <XIcon size={20} />
          </button>
          <button
            className="swipe-btn swipe-btn-automate"
            onPointerDown={stopForButton}
            onClick={() => fly("right")}
            aria-label="Add to automation plan"
          >
            <CheckIcon size={20} />
          </button>
        </div>
      )}
    </div>
  );
}
