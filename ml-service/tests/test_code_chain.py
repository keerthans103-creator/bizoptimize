"""
generate_code's own retriever/LLM construction needs real embeddings and a
live API key, so these tests mock the assembled chain itself rather than
building it -- what's actually worth verifying here (without a network call)
is that generate_code wires call_with_retry around chain.invoke correctly,
and that _format_docs turns retrieved documents into the expected context
string.
"""
from unittest.mock import MagicMock, patch

from app.rag import code_chain


class _FakeDoc:
    def __init__(self, metadata, page_content=""):
        self.metadata = metadata
        self.page_content = page_content


def test_format_docs_combines_title_and_instructions():
    docs = [
        _FakeDoc({"title": "Automated report", "instructions": "use cron + pandas"}),
        _FakeDoc({"title": "Invoice reminder", "instructions": "use a scheduled email job"}),
    ]
    result = code_chain._format_docs(docs)
    assert "Automated report: use cron + pandas" in result
    assert "Invoice reminder: use a scheduled email job" in result


def test_format_docs_falls_back_to_page_content_without_instructions_metadata():
    docs = [_FakeDoc({"title": "X"}, page_content="raw text body")]
    result = code_chain._format_docs(docs)
    assert "X: raw text body" in result


def test_generate_code_retries_transient_error_then_succeeds():
    fake_chain = MagicMock()
    call_count = {"n": 0}

    def fake_invoke(task_text):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise RuntimeError("503 UNAVAILABLE. Model is currently experiencing high demand.")
        return "```python\nprint('hello')\n```"

    fake_chain.invoke.side_effect = fake_invoke

    with patch.object(code_chain, "_get_chain", return_value=fake_chain):
        with patch("app.retry.time.sleep"):
            result = code_chain.generate_code("automate this task")

    assert "hello" in result
    assert call_count["n"] == 2


def test_generate_code_does_not_retry_non_transient_errors():
    fake_chain = MagicMock()
    fake_chain.invoke.side_effect = ValueError("task_text is required")

    with patch.object(code_chain, "_get_chain", return_value=fake_chain):
        try:
            code_chain.generate_code("")
            assert False, "expected ValueError to propagate"
        except ValueError:
            pass

    assert fake_chain.invoke.call_count == 1
