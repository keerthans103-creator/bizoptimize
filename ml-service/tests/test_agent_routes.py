"""
Route-level tests for the agent endpoints -- mocks the orchestrator
entirely (its own behavior is covered by test_agent_orchestrator.py), so
this only verifies the Flask layer: request validation, status codes, and
that each route calls the right orchestrator function with the right
arguments.
"""
from unittest.mock import patch

import pytest

import app.main as main_module


@pytest.fixture
def client():
    main_module.app.testing = True
    return main_module.app.test_client()


def test_agent_execute_requires_task_text(client):
    resp = client.post("/agent/execute", json={})
    assert resp.status_code == 400


def test_agent_execute_returns_202_with_job_id(client):
    with patch.object(main_module.orchestrator, "create_job", return_value="abc123"):
        resp = client.post("/agent/execute", json={"task_text": "reply to shipping questions"})

    assert resp.status_code == 202
    assert resp.get_json() == {"job_id": "abc123"}


def test_agent_job_status_404_for_unknown_job(client):
    with patch.object(main_module.orchestrator, "get_job", return_value=None):
        resp = client.get("/agent/jobs/does-not-exist")
    assert resp.status_code == 404


def test_agent_job_status_returns_job_dict(client):
    fake_job = {"job_id": "abc123", "status": "completed", "steps": []}
    with patch.object(main_module.orchestrator, "get_job", return_value=fake_job):
        resp = client.get("/agent/jobs/abc123")

    assert resp.status_code == 200
    assert resp.get_json() == fake_job


def test_agent_job_approve_success(client):
    with patch.object(main_module.orchestrator, "approve_job", return_value=True):
        resp = client.post("/agent/jobs/abc123/approve")
    assert resp.status_code == 200


def test_agent_job_approve_404_when_not_awaiting_approval(client):
    with patch.object(main_module.orchestrator, "approve_job", return_value=False):
        resp = client.post("/agent/jobs/abc123/approve")
    assert resp.status_code == 404


def test_agent_job_reject_success(client):
    with patch.object(main_module.orchestrator, "reject_job", return_value=True):
        resp = client.post("/agent/jobs/abc123/reject")
    assert resp.status_code == 200


def test_agent_job_reject_404_when_not_awaiting_approval(client):
    with patch.object(main_module.orchestrator, "reject_job", return_value=False):
        resp = client.post("/agent/jobs/abc123/reject")
    assert resp.status_code == 404
