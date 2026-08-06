import { act, render, screen, fireEvent } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AgentDemo from "../AgentDemo.jsx";
import { api } from "../../api/client.js";

vi.mock("../../api/client.js", () => ({
  api: {
    executeAgentTask: vi.fn(),
    getAgentJob: vi.fn(),
    approveAgentJob: vi.fn(),
    rejectAgentJob: vi.fn(),
  },
}));

const POLL_INTERVAL_MS = 1500;

function job(overrides) {
  return {
    job_id: "job-1",
    status: "planning",
    error: null,
    steps: [],
    ...overrides,
  };
}

function advance(ms) {
  return act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("AgentDemo", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.resetAllMocks();
  });

  it("starts a job, polls until awaiting_approval, then shows the approval gate", async () => {
    api.executeAgentTask.mockResolvedValue({ job_id: "job-1" });
    api.getAgentJob
      .mockResolvedValueOnce(job({ status: "planning" }))
      .mockResolvedValueOnce(
        job({
          status: "awaiting_approval",
          steps: [{ message_id: "msg-1", action: "send_reply", description: "reply", attempts: 0, status: "pending", risky: true, verification: null }],
        })
      );

    render(<AgentDemo />);
    await act(async () => {
      fireEvent.click(screen.getByText("Run agent"));
    });

    await advance(POLL_INTERVAL_MS);

    expect(screen.getByText("Awaiting your approval")).toBeInTheDocument();
    expect(screen.getByText("Approve")).toBeInTheDocument();
    expect(screen.getByText("Reject")).toBeInTheDocument();
  });

  it("approving resumes polling and eventually shows completed with a replanned step", async () => {
    api.executeAgentTask.mockResolvedValue({ job_id: "job-1" });
    api.getAgentJob.mockResolvedValueOnce(
      job({
        status: "awaiting_approval",
        steps: [{ message_id: "msg-4", action: "send_reply", description: "reply", attempts: 0, status: "pending", risky: true, verification: null }],
      })
    );
    api.approveAgentJob.mockResolvedValue({ status: "approved" });

    render(<AgentDemo />);
    await act(async () => {
      fireEvent.click(screen.getByText("Run agent"));
    });

    api.getAgentJob.mockResolvedValueOnce(
      job({
        status: "completed",
        steps: [
          {
            message_id: "msg-4",
            action: "flag_for_review",
            description: "escalate instead",
            attempts: 2,
            status: "passed",
            risky: true,
            verification: { passed: true, reason: "flagged" },
          },
        ],
      })
    );

    await act(async () => {
      fireEvent.click(screen.getByText("Approve"));
    });
    await advance(POLL_INTERVAL_MS);

    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("attempt 2 (replanned)")).toBeInTheDocument();
    expect(screen.getByText("Run again")).toBeInTheDocument();
  });

  it("rejecting stops the job without executing", async () => {
    api.executeAgentTask.mockResolvedValue({ job_id: "job-1" });
    api.getAgentJob.mockResolvedValueOnce(
      job({
        status: "awaiting_approval",
        steps: [{ message_id: "msg-1", action: "send_reply", description: "reply", attempts: 0, status: "pending", risky: true, verification: null }],
      })
    );
    api.rejectAgentJob.mockResolvedValue({ status: "rejected" });

    render(<AgentDemo />);
    await act(async () => {
      fireEvent.click(screen.getByText("Run agent"));
    });

    api.getAgentJob.mockResolvedValueOnce(
      job({
        status: "rejected",
        steps: [{ message_id: "msg-1", action: "send_reply", description: "reply", attempts: 0, status: "pending", risky: true, verification: null }],
      })
    );

    await act(async () => {
      fireEvent.click(screen.getByText("Reject"));
    });
    await advance(POLL_INTERVAL_MS);

    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.queryByText("Approve")).not.toBeInTheDocument();
  });

  it("shows an error banner when starting the job fails", async () => {
    api.executeAgentTask.mockRejectedValue(new Error("ml-service unreachable"));

    render(<AgentDemo />);
    await act(async () => {
      fireEvent.click(screen.getByText("Run agent"));
    });

    expect(screen.getByText("ml-service unreachable")).toBeInTheDocument();
  });
});
