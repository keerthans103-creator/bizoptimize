"""
Orchestrator tests mock the planner/verifier's Gemini calls (they need a
real API key and network access), not the orchestrator's own control flow
-- what's actually worth verifying here without a network call is the
state machine itself: does a risky step actually pause for approval, does
rejecting actually stop the job, does a verification failure actually
trigger a genuinely different next action rather than a bare retry, and
does exhausting the replan budget actually fail the job instead of looping
forever.
"""
import time
from unittest.mock import patch

from app.agent import orchestrator


def _wait_for_status(job_id, terminal_statuses, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = orchestrator.get_job(job_id)
        if job["status"] in terminal_statuses:
            return job
        time.sleep(0.02)
    raise AssertionError(
        f"job {job_id} did not reach {terminal_statuses} within {timeout}s "
        f"(last status: {orchestrator.get_job(job_id)['status']})"
    )


def test_non_risky_step_completes_without_approval_gate():
    plan = [{"message_id": "msg-4", "action": "flag_for_review", "description": "not a shipping question"}]

    with patch.object(orchestrator.planner, "create_initial_plan", return_value=plan):
        with patch.object(
            orchestrator.verifier, "verify_flag", return_value={"passed": True, "reason": "flagged"}
        ):
            job_id = orchestrator.create_job("reply to shipping questions")
            job = _wait_for_status(job_id, {"completed", "failed"})

    assert job["status"] == "completed"
    assert job["steps"][0]["status"] == "passed"
    assert job["steps"][0]["attempts"] == 1


def test_risky_step_pauses_then_completes_on_approve():
    plan = [{"message_id": "msg-1", "action": "send_reply", "description": "shipping question"}]

    with patch.object(orchestrator.planner, "create_initial_plan", return_value=plan):
        with patch.object(
            orchestrator.verifier, "verify_reply", return_value={"passed": True, "reason": "on topic"}
        ):
            job_id = orchestrator.create_job("reply to shipping questions")
            job = _wait_for_status(job_id, {"awaiting_approval", "completed", "failed"})
            assert job["status"] == "awaiting_approval"
            assert job["steps"][0]["status"] == "pending"  # not executed yet

            assert orchestrator.approve_job(job_id) is True
            job = _wait_for_status(job_id, {"completed", "failed"})

    assert job["status"] == "completed"
    assert job["steps"][0]["status"] == "passed"


def test_risky_step_rejected_stops_job_before_executing():
    plan = [{"message_id": "msg-1", "action": "send_reply", "description": "shipping question"}]

    with patch.object(orchestrator.planner, "create_initial_plan", return_value=plan):
        job_id = orchestrator.create_job("reply to shipping questions")
        job = _wait_for_status(job_id, {"awaiting_approval"})
        assert orchestrator.reject_job(job_id) is True
        job = _wait_for_status(job_id, {"rejected", "completed", "failed"})

    assert job["status"] == "rejected"
    assert job["steps"][0]["status"] == "pending"  # rejection happened before execution


def test_verification_failure_triggers_replan_not_bare_retry():
    plan = [{"message_id": "msg-4", "action": "send_reply", "description": "refund question (wrong guess)"}]
    replan_calls = []

    def fake_replan(message, failed_reply, failure_reason):
        replan_calls.append((message["id"], failure_reason))
        return {"action": "flag_for_review", "description": "escalating instead"}

    verify_reply_result = {"passed": False, "reason": "reply does not address the refund request"}
    verify_flag_result = {"passed": True, "reason": "flagged"}

    with patch.object(orchestrator.planner, "create_initial_plan", return_value=plan):
        with patch.object(orchestrator.planner, "replan_step", side_effect=fake_replan):
            with patch.object(orchestrator.verifier, "verify_reply", return_value=verify_reply_result):
                with patch.object(orchestrator.verifier, "verify_flag", return_value=verify_flag_result):
                    job_id = orchestrator.create_job("reply to shipping questions")
                    job = _wait_for_status(job_id, {"awaiting_approval"})
                    orchestrator.approve_job(job_id)
                    job = _wait_for_status(job_id, {"completed", "failed"})

    assert job["status"] == "completed"
    assert len(replan_calls) == 1, "replan should be called exactly once, not looped or skipped"
    step = job["steps"][0]
    assert step["action"] == "flag_for_review", "the executed action must actually change after replanning"
    assert step["attempts"] == 2, "first attempt (send_reply) + second attempt (flag_for_review)"
    assert step["status"] == "passed"


def test_replan_budget_exhausted_fails_job_instead_of_looping_forever():
    plan = [{"message_id": "msg-4", "action": "send_reply", "description": "keeps failing"}]

    with patch.object(orchestrator.planner, "create_initial_plan", return_value=plan):
        with patch.object(
            orchestrator.planner,
            "replan_step",
            return_value={"action": "send_reply", "description": "try again (still wrong)"},
        ):
            with patch.object(
                orchestrator.verifier,
                "verify_reply",
                return_value={"passed": False, "reason": "still wrong"},
            ):
                job_id = orchestrator.create_job("reply to shipping questions")
                job = _wait_for_status(job_id, {"awaiting_approval"})
                orchestrator.approve_job(job_id)
                job = _wait_for_status(job_id, {"completed", "failed"})

    assert job["status"] == "failed"
    assert job["error"] is not None
    assert job["steps"][0]["attempts"] == orchestrator.MAX_REPLANS_PER_STEP + 1


def test_unknown_job_id_returns_none():
    assert orchestrator.get_job("not-a-real-job-id") is None


def test_approve_unknown_job_returns_false():
    assert orchestrator.approve_job("not-a-real-job-id") is False


def test_reject_unknown_job_returns_false():
    assert orchestrator.reject_job("not-a-real-job-id") is False
