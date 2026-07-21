import pytest

from app.retry import call_with_retry


def test_succeeds_on_first_try_without_retrying():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    result = call_with_retry(fn, max_attempts=3, base_delay=0)
    assert result == "ok"
    assert len(calls) == 1


def test_retries_transient_error_then_succeeds():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("503 UNAVAILABLE. Model is currently experiencing high demand.")
        return "recovered"

    result = call_with_retry(fn, max_attempts=5, base_delay=0)
    assert result == "recovered"
    assert len(calls) == 3


def test_raises_after_exhausting_retries_on_persistent_transient_error():
    calls = []

    def fn():
        calls.append(1)
        raise RuntimeError("503 UNAVAILABLE. overloaded")

    with pytest.raises(RuntimeError, match="503"):
        call_with_retry(fn, max_attempts=3, base_delay=0)
    assert len(calls) == 3


def test_does_not_retry_non_transient_errors():
    calls = []

    def fn():
        calls.append(1)
        raise ValueError("task_text is required")

    with pytest.raises(ValueError, match="task_text is required"):
        call_with_retry(fn, max_attempts=3, base_delay=0)
    assert len(calls) == 1
