"""
The gateway is a thin proxy, so these tests mock out `requests` entirely --
no real ml-service/backend needs to be running. What's actually worth
verifying here: the right method/URL is called for each route, the
Authorization header is forwarded but nothing else is, and upstream
connection failures turn into the right HTTP status instead of a raw
exception leaking to the client.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests as real_requests

import app as gateway_module


@pytest.fixture
def client():
    gateway_module.app.testing = True
    return gateway_module.app.test_client()


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    return mock


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "gateway": "up"}


def test_analyze_workflow_proxies_to_ml_service(client):
    with patch.object(gateway_module.requests, "request") as mock_request:
        mock_request.return_value = _mock_response({"tasks": []})
        resp = client.post("/api/workflows/analyze", json={"workflow_text": "do a thing"})

    assert resp.status_code == 200
    assert resp.get_json() == {"tasks": []}
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == f"{gateway_module.ML_SERVICE_URL}/analyze"
    assert kwargs["json"] == {"workflow_text": "do a thing"}


def test_generate_script_proxies_to_ml_service(client):
    with patch.object(gateway_module.requests, "request") as mock_request:
        mock_request.return_value = _mock_response({"code": "print(1)"})
        resp = client.post("/api/tasks/generate-script", json={"task_text": "do x"})

    assert resp.status_code == 200
    assert resp.get_json() == {"code": "print(1)"}
    args, _ = mock_request.call_args
    assert args[1] == f"{gateway_module.ML_SERVICE_URL}/generate-script"


def test_register_proxies_to_backend(client):
    with patch.object(gateway_module.requests, "request") as mock_request:
        mock_request.return_value = _mock_response({"token": "abc", "email": "a@b.com"})
        resp = client.post("/api/auth/register", json={"email": "a@b.com", "password": "supersecret1"})

    assert resp.status_code == 200
    args, _ = mock_request.call_args
    assert args[1] == f"{gateway_module.BACKEND_URL}/api/auth/register"


def test_forwards_authorization_header_only(client):
    with patch.object(gateway_module.requests, "request") as mock_request:
        mock_request.return_value = _mock_response([])
        client.get("/api/workflows", headers={"Authorization": "Bearer test-token", "X-Other": "nope"})

    _, kwargs = mock_request.call_args
    assert kwargs["headers"] == {"Authorization": "Bearer test-token"}


def test_no_authorization_header_when_absent(client):
    with patch.object(gateway_module.requests, "request") as mock_request:
        mock_request.return_value = _mock_response([])
        client.get("/api/workflows")

    _, kwargs = mock_request.call_args
    assert kwargs["headers"] == {}


def test_proxy_returns_502_on_connection_error(client):
    with patch.object(gateway_module.requests, "request", side_effect=real_requests.exceptions.ConnectionError()):
        resp = client.post("/api/workflows/analyze", json={"workflow_text": "x"})

    assert resp.status_code == 502


def test_proxy_returns_504_on_timeout(client):
    with patch.object(gateway_module.requests, "request", side_effect=real_requests.exceptions.Timeout()):
        resp = client.post("/api/workflows/analyze", json={"workflow_text": "x"})

    assert resp.status_code == 504


def test_full_save_orchestrates_analyze_then_save(client):
    analyze_resp = _mock_response({"tasks": [{"task_text": "x", "score": 80}]})
    save_resp = _mock_response({"id": 1, "title": "wf"})

    with patch.object(gateway_module.requests, "post", side_effect=[analyze_resp, save_resp]) as mock_post:
        resp = client.post(
            "/api/workflows/full-save",
            json={"workflow_text": "do x", "title": "wf"},
            headers={"Authorization": "Bearer tok"},
        )

    assert resp.status_code == 200
    assert resp.get_json() == {"id": 1, "title": "wf"}
    assert mock_post.call_count == 2

    first_call = mock_post.call_args_list[0]
    assert first_call.args[0] == f"{gateway_module.ML_SERVICE_URL}/analyze"

    second_call = mock_post.call_args_list[1]
    assert second_call.args[0] == f"{gateway_module.BACKEND_URL}/api/workflows"
    assert second_call.kwargs["json"]["tasks"] == [{"task_text": "x", "score": 80}]
    assert second_call.kwargs["headers"] == {"Authorization": "Bearer tok"}


def test_full_save_stops_if_analyze_fails(client):
    analyze_resp = _mock_response({"error": "boom"}, status_code=502)

    with patch.object(gateway_module.requests, "post", return_value=analyze_resp) as mock_post:
        resp = client.post("/api/workflows/full-save", json={"workflow_text": "x"})

    assert resp.status_code == 502
    assert mock_post.call_count == 1
