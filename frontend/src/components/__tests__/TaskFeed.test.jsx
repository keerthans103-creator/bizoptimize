import { act, render, screen, fireEvent, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import TaskFeed from "../TaskFeed.jsx";

function makeTask(overrides) {
  return {
    id: null,
    text: "task",
    hint: "",
    score: 80,
    explanation: "",
    automation: [],
    ...overrides,
  };
}

function advance(ms) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

// TaskFeed no longer owns decision state itself (App.jsx does, so it can be
// included in the save payload and restored from history) -- this harness
// mimics that real usage so tests exercise the actual prop contract instead
// of a decision store nothing else uses.
function FeedHarness({ tasks, initialDecisions = {} }) {
  const [decisions, setDecisions] = useState(initialDecisions);
  const onDecide = (text, decision) => setDecisions((prev) => ({ ...prev, [text]: decision }));
  const onRestartDecisions = () => setDecisions({});
  return (
    <TaskFeed
      tasks={tasks}
      decisions={decisions}
      onDecide={onDecide}
      onRestartDecisions={onRestartDecisions}
      onExit={() => {}}
    />
  );
}

describe("TaskFeed", () => {
  it("only includes tasks scoring 70+ in the swipe deck", () => {
    const tasks = [makeTask({ text: "Task A", score: 80 }), makeTask({ text: "Task B", score: 40 })];
    render(<FeedHarness tasks={tasks} />);

    expect(screen.getByText("1 / 1")).toBeInTheDocument();
    expect(screen.getByText("Task A")).toBeInTheDocument();
    expect(screen.queryByText("Task B")).not.toBeInTheDocument();
  });

  it("shows the empty-deck message when nothing qualifies", () => {
    const tasks = [makeTask({ text: "Task B", score: 40 })];
    render(<FeedHarness tasks={tasks} />);

    expect(screen.getByText(/No tasks scored 70%\+/)).toBeInTheDocument();
  });

  it("attributes decisions to the correct task: automate A, skip B -> plan contains only A", () => {
    vi.useFakeTimers();
    const tasks = [makeTask({ text: "Task A", score: 90 }), makeTask({ text: "Task B", score: 85 })];
    const { container } = render(<FeedHarness tasks={tasks} />);

    expect(screen.getByText("Task A")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Add to automation plan"));
    advance(200);

    expect(screen.getByText("Task B")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Skip automating this"));
    advance(200);

    expect(screen.getByText("Automating 1 of 2")).toBeInTheDocument();
    const planItems = container.querySelectorAll(".feed-plan-header");
    expect(planItems).toHaveLength(1);
    expect(within(planItems[0]).getByText("Task A")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("attributes decisions to the correct task the other way around: skip A, automate B -> plan contains only B", () => {
    vi.useFakeTimers();
    const tasks = [makeTask({ text: "Task A", score: 90 }), makeTask({ text: "Task B", score: 85 })];
    const { container } = render(<FeedHarness tasks={tasks} />);

    fireEvent.click(screen.getByLabelText("Skip automating this"));
    advance(200);

    fireEvent.click(screen.getByLabelText("Add to automation plan"));
    advance(200);

    expect(screen.getByText("Automating 1 of 2")).toBeInTheDocument();
    const planItems = container.querySelectorAll(".feed-plan-header");
    expect(planItems).toHaveLength(1);
    expect(within(planItems[0]).getByText("Task B")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("shows 2 of 2 when both candidates are automated", () => {
    vi.useFakeTimers();
    const tasks = [makeTask({ text: "Task A", score: 90 }), makeTask({ text: "Task B", score: 85 })];
    render(<FeedHarness tasks={tasks} />);

    fireEvent.click(screen.getByLabelText("Add to automation plan"));
    advance(200);
    fireEvent.click(screen.getByLabelText("Add to automation plan"));
    advance(200);

    expect(screen.getByText("Automating 2 of 2")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("shows 0 of 2 when both candidates are skipped", () => {
    vi.useFakeTimers();
    const tasks = [makeTask({ text: "Task A", score: 90 }), makeTask({ text: "Task B", score: 85 })];
    render(<FeedHarness tasks={tasks} />);

    fireEvent.click(screen.getByLabelText("Skip automating this"));
    advance(200);
    fireEvent.click(screen.getByLabelText("Skip automating this"));
    advance(200);

    expect(screen.getByText("Automating 0 of 2")).toBeInTheDocument();
    expect(screen.getByText(/You skipped everything this round/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("restored decisions (e.g. from a saved workflow) skip straight to the summary, no re-swiping needed", () => {
    const tasks = [makeTask({ text: "Task A", score: 90 }), makeTask({ text: "Task B", score: 85 })];
    const { container } = render(
      <FeedHarness tasks={tasks} initialDecisions={{ "Task A": "automate", "Task B": "skip" }} />
    );

    expect(screen.getByText("Automating 1 of 2")).toBeInTheDocument();
    const planItems = container.querySelectorAll(".feed-plan-header");
    expect(planItems).toHaveLength(1);
    expect(within(planItems[0]).getByText("Task A")).toBeInTheDocument();
  });

  it("only asks about tasks that don't already have a restored decision", () => {
    const tasks = [
      makeTask({ text: "Task A", score: 90 }),
      makeTask({ text: "Task B", score: 85 }),
      makeTask({ text: "Task C", score: 88 }),
    ];
    render(<FeedHarness tasks={tasks} initialDecisions={{ "Task A": "automate" }} />);

    // Only B and C are undecided, so the deck should have 2 remaining, not 3.
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    expect(screen.queryByText("Task A")).not.toBeInTheDocument();
  });
});
