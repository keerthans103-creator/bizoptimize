"""Verifies parse_workflow actually retries transient Gemini errors at the
real call site -- test_retry.py covers the retry helper in isolation, this
covers that workflow_parser.py is actually wired up to use it."""
import json
from unittest.mock import MagicMock, patch

from app.nlp import workflow_parser


class _FakeResponse:
    def __init__(self, text):
        self.text = text


def test_parse_workflow_retries_transient_error_then_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    call_count = {"n": 0}

    def fake_generate_content(**kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise RuntimeError("503 UNAVAILABLE. Model is currently experiencing high demand.")
        return _FakeResponse(json.dumps({"tasks": [{"text": "Send an email", "hint": "recurring"}]}))

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = fake_generate_content

    with patch("app.nlp.workflow_parser.genai.Client", return_value=fake_client):
        with patch("app.retry.time.sleep"):
            tasks = workflow_parser.parse_workflow("Send an email every day.")

    assert tasks == [{"text": "Send an email", "hint": "recurring"}]
    assert call_count["n"] == 2
