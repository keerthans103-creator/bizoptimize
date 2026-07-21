import { act, render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SwipeCard from "../SwipeCard.jsx";

const task = {
  id: null,
  text: "Send a reminder email to customers with overdue invoices.",
  hint: "recurring",
  score: 82,
  explanation: "Driven by repetitive language.",
};

// This jsdom version has no global PointerEvent constructor and RTL's
// `fireEvent.pointerX(el, {clientX})` shorthand doesn't reliably carry
// clientX through jsdom's event plumbing either, so build a plain Event and
// attach the properties our handlers read directly (React's synthetic
// pointer handlers just read whatever is on the native event, real
// PointerEvent-ness isn't required). Verified against real drag behavior in
// an actual browser separately.
function firePointer(el, type, clientX, pointerId) {
  const event = new Event(type, { bubbles: true, cancelable: true });
  event.clientX = clientX;
  event.pointerId = pointerId;
  fireEvent(el, event);
}

function drag(card, dx) {
  firePointer(card, "pointerdown", 0, 1);
  firePointer(card, "pointermove", dx, 1);
  firePointer(card, "pointerup", dx, 1);
}

function advance(ms) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

describe("SwipeCard", () => {
  it("calls onDecide('automate') after dragging right past the decision threshold", () => {
    vi.useFakeTimers();
    const onDecide = vi.fn();
    const { container } = render(<SwipeCard task={task} onDecide={onDecide} />);
    drag(container.querySelector(".swipe-card"), 200);

    expect(onDecide).not.toHaveBeenCalled(); // fly-off animation hasn't completed yet
    advance(200);
    expect(onDecide).toHaveBeenCalledWith("automate");
    vi.useRealTimers();
  });

  it("calls onDecide('skip') after dragging left past the decision threshold", () => {
    vi.useFakeTimers();
    const onDecide = vi.fn();
    const { container } = render(<SwipeCard task={task} onDecide={onDecide} />);
    drag(container.querySelector(".swipe-card"), -200);

    advance(200);
    expect(onDecide).toHaveBeenCalledWith("skip");
    vi.useRealTimers();
  });

  it("springs back without deciding when released below the threshold", () => {
    vi.useFakeTimers();
    const onDecide = vi.fn();
    const { container } = render(<SwipeCard task={task} onDecide={onDecide} />);
    drag(container.querySelector(".swipe-card"), 50); // DECIDE_DISTANCE is 110

    advance(500);
    expect(onDecide).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("regression: clicking the automate button works (pointer capture must not swallow the click)", () => {
    vi.useFakeTimers();
    const onDecide = vi.fn();
    render(<SwipeCard task={task} onDecide={onDecide} />);
    fireEvent.click(screen.getByLabelText("Add to automation plan"));

    advance(200);
    expect(onDecide).toHaveBeenCalledWith("automate");
    vi.useRealTimers();
  });

  it("regression: clicking the skip button works", () => {
    vi.useFakeTimers();
    const onDecide = vi.fn();
    render(<SwipeCard task={task} onDecide={onDecide} />);
    fireEvent.click(screen.getByLabelText("Skip automating this"));

    advance(200);
    expect(onDecide).toHaveBeenCalledWith("skip");
    vi.useRealTimers();
  });

  it("regression: a fast swipe (pointerup fired immediately after pointermove, no time between) still registers", () => {
    vi.useFakeTimers();
    const onDecide = vi.fn();
    const { container } = render(<SwipeCard task={task} onDecide={onDecide} />);
    const card = container.querySelector(".swipe-card");

    firePointer(card, "pointerdown", 0, 2);
    firePointer(card, "pointermove", 250, 2);
    firePointer(card, "pointerup", 250, 2);

    advance(200);
    expect(onDecide).toHaveBeenCalledWith("automate");
    vi.useRealTimers();
  });
});
