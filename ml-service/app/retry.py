"""
Small explicit retry helper for transient upstream (Gemini) failures.

Written by hand rather than pulling in a retry library because the retry
policy here is narrow and worth being able to read in one glance: back off
and retry only on the specific transient conditions we've actually observed
(503 "model overloaded" during testing), fail fast on everything else
(bad request, auth, quota-exceeded -- retrying those just wastes time since
they won't resolve themselves).
"""
import logging
import time

logger = logging.getLogger(__name__)

_TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "overloaded", "high demand")


def _is_transient(exc: Exception) -> bool:
    message = str(exc)
    return any(marker.lower() in message.lower() for marker in _TRANSIENT_MARKERS)


def call_with_retry(fn, *args, max_attempts: int = 3, base_delay: float = 1.0, **kwargs):
    """Calls fn(*args, **kwargs), retrying with exponential backoff only on
    transient-looking errors. Re-raises immediately on anything else, and
    re-raises the last error once max_attempts is exhausted."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 -- intentionally broad, see docstring
            last_exc = exc
            if not _is_transient(exc) or attempt == max_attempts - 1:
                raise
            delay = base_delay * (2**attempt)
            logger.warning(
                "Transient error on attempt %d/%d, retrying in %.1fs: %s",
                attempt + 1,
                max_attempts,
                delay,
                exc,
            )
            time.sleep(delay)
    raise last_exc  # pragma: no cover -- unreachable, loop always returns or raises
