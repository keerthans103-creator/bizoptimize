"""
Planner agent: structured Gemini calls that select from an explicitly
bounded set of registered tool actions -- never open-ended code generation
or an invented action outside the sandbox's real capabilities. Mirrors the
structured-JSON-response pattern already used in workflow_parser.py.

The initial plan is deliberately only told about one tool (send_reply via
the shipping-status template) -- that's the agent's starting capability.
flag_for_review is only introduced in the replan prompt, once a real
verification failure has actually happened. This isn't scripted: both
calls are genuine Gemini reasoning over the specific message content, but
the tool list each call is told about is what keeps the demo's replan path
reliably reachable instead of hoping the model happens to get the first
pass wrong.
"""
import json
import os

from app.retry import call_with_retry

_INITIAL_SYSTEM_PROMPT = """You are an automation planning agent. You will be given a task \
description and a list of unread inbox messages. For each message, decide what action to \
take using ONLY the tool listed below.

Available tool:
- send_reply: reply to the message using the standard shipping-status template. This is \
the only action currently available to you, so use it for every message.

Respond with ONLY valid JSON, no prose, in this exact shape:
{"steps": [{"message_id": "...", "action": "send_reply", "description": "one-sentence reason for this action"}]}
"""

_REPLAN_SYSTEM_PROMPT = """You are an automation planning agent revising a single failed step.

A previous attempt replied to a message using the shipping-status template, but a \
verification check determined the reply did not actually address what the customer asked. \
You now have a second tool available:

- send_reply: reply using the shipping-status template again (only choose this if you \
believe the failure reason was mistaken).
- flag_for_review: escalate this message to a human instead of guessing at a reply. Use \
this for anything that isn't a straightforward shipping-status question -- refunds, \
complaints, or anything else the template doesn't actually answer.

Respond with ONLY valid JSON, no prose, in this exact shape:
{"action": "flag_for_review", "description": "one-sentence reason for this revised action"}
"""


def _client():
    # Imported here, not at module level -- see workflow_parser.py for why:
    # google-genai is heavy enough to block gunicorn's single worker from
    # answering /health on a cold start if imported eagerly.
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Export it before starting ml-service."
        )
    return genai.Client(api_key=api_key)


def create_initial_plan(task_text: str, messages: list) -> list:
    """One step per unread message. Returns a list of
    {"message_id", "action", "description"} dicts."""
    from google.genai import types

    client = _client()
    message_summaries = "\n".join(
        f"- id={m['id']}, from={m['name']}, subject={m['subject']!r}, body={m['body']!r}"
        for m in messages
    )
    prompt = f"Task: {task_text}\n\nUnread messages:\n{message_summaries}"

    response = call_with_retry(
        client.models.generate_content,
        model=os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest"),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_INITIAL_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    parsed = json.loads(response.text or "{}")
    return parsed.get("steps", [])


def replan_step(message: dict, failed_reply: str, failure_reason: str) -> dict:
    """Called when a step fails verification. Returns a single revised
    {"action", "description"} dict -- a genuinely different next attempt,
    not the same action retried."""
    from google.genai import types

    client = _client()
    prompt = (
        f"Message from {message['name']}: {message['subject']!r} -- {message['body']!r}\n\n"
        f"Attempted reply: {failed_reply!r}\n\n"
        f"Why it failed verification: {failure_reason}"
    )

    response = call_with_retry(
        client.models.generate_content,
        model=os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest"),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_REPLAN_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text or "{}")
