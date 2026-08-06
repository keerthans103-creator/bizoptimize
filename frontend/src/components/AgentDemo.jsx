import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { BoltIcon, CheckIcon, XIcon } from "./icons.jsx";

const DEMO_TASK_TEXT = "Reply to customer emails about their shipping status using our template";
const POLL_INTERVAL_MS = 1500;
const TERMINAL_STATUSES = new Set(["completed", "failed", "rejected"]);

const STATUS_LABELS = {
  planning: "Planning",
  executing: "Executing",
  awaiting_approval: "Awaiting your approval",
  completed: "Completed",
  failed: "Failed",
  rejected: "Rejected",
};

const STEP_STATUS_LABELS = {
  pending: "Pending",
  passed: "Passed",
  replanned: "Replanning",
  failed: "Failed",
};

function statusClass(status) {
  if (status === "completed" || status === "passed") return "agent-status-success";
  if (status === "failed" || status === "rejected") return "agent-status-danger";
  if (status === "awaiting_approval" || status === "replanned") return "agent-status-warning";
  return "agent-status-neutral";
}

export default function AgentDemo() {
  const [job, setJob] = useState(null);
  const [starting, setStarting] = useState(false);
  const [actionPending, setActionPending] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const pollJob = (jobId) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const latest = await api.getAgentJob(jobId);
        setJob(latest);
        if (TERMINAL_STATUSES.has(latest.status)) {
          clearInterval(pollRef.current);
        }
      } catch (err) {
        setError(err.message);
        clearInterval(pollRef.current);
      }
    }, POLL_INTERVAL_MS);
  };

  const handleRun = async () => {
    setStarting(true);
    setError("");
    setJob(null);
    try {
      const { job_id } = await api.executeAgentTask(DEMO_TASK_TEXT);
      const initial = await api.getAgentJob(job_id);
      setJob(initial);
      if (!TERMINAL_STATUSES.has(initial.status)) pollJob(job_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setStarting(false);
    }
  };

  const handleApprove = async () => {
    if (!job) return;
    setActionPending(true);
    setError("");
    try {
      await api.approveAgentJob(job.job_id);
      pollJob(job.job_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionPending(false);
    }
  };

  const handleReject = async () => {
    if (!job) return;
    setActionPending(true);
    setError("");
    try {
      await api.rejectAgentJob(job.job_id);
      pollJob(job.job_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionPending(false);
    }
  };

  const handleReset = () => {
    clearInterval(pollRef.current);
    setJob(null);
    setError("");
  };

  const isTerminal = job && TERMINAL_STATUSES.has(job.status);

  return (
    <section className="panel agent-panel">
      <h2>Agentic execution layer</h2>
      <p className="muted small" style={{ marginBottom: 16 }}>
        A shared support inbox has 5 unread messages. A planner agent decides how to handle each
        one, a tool-executor runs the action in a sandbox (nothing is really sent), and a verifier
        checks the result &mdash; replanning with a genuinely different approach when it gets one
        wrong instead of just retrying. Anything risky pauses here for your approval before it
        runs.
      </p>

      {error && <div className="error-banner">{error}</div>}

      {!job && (
        <button onClick={handleRun} disabled={starting}>
          {starting ? (
            <>
              <span className="spinner" /> Starting&hellip;
            </>
          ) : (
            <>
              <BoltIcon size={15} /> Run agent
            </>
          )}
        </button>
      )}

      {job && (
        <div className="agent-job">
          <div className="agent-job-status">
            <span className={`agent-status-pill ${statusClass(job.status)}`}>
              {STATUS_LABELS[job.status] || job.status}
            </span>
            {job.error && <span className="error small">{job.error}</span>}
          </div>

          <div className="agent-step-list">
            {job.steps.map((step, idx) => (
              <div className="agent-step" key={`${step.message_id}-${idx}`}>
                <div className="agent-step-header">
                  <span className={`agent-status-pill small ${statusClass(step.status)}`}>
                    {STEP_STATUS_LABELS[step.status] || step.status}
                  </span>
                  <span className="agent-step-message">{step.message_id}</span>
                  {step.attempts > 1 && (
                    <span className="muted small">attempt {step.attempts} (replanned)</span>
                  )}
                </div>
                <p className="agent-step-description">{step.description}</p>
                {step.verification?.reason && (
                  <p className="muted small">{step.verification.reason}</p>
                )}
              </div>
            ))}
          </div>

          {job.status === "awaiting_approval" && (
            <div className="agent-approval-gate">
              <p className="small">
                This plan includes a step flagged as risky. Approve to let the agent continue, or
                reject to stop here before anything executes.
              </p>
              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={handleApprove} disabled={actionPending}>
                  <CheckIcon size={15} /> Approve
                </button>
                <button className="btn-secondary" onClick={handleReject} disabled={actionPending}>
                  <XIcon size={15} /> Reject
                </button>
              </div>
            </div>
          )}

          {isTerminal && (
            <button className="btn-secondary" onClick={handleReset} style={{ marginTop: 16 }}>
              Run again
            </button>
          )}
        </div>
      )}
    </section>
  );
}
