"""
Verifier agent: checks whether a step's actual result satisfies the
original message. verify_reply is a real semantic Gemini check, not a
keyword match -- a keyword check couldn't reliably catch a reply that's
actually the wrong topic entirely, which is exactly the failure this
feature needs to demonstrate for the replan path to be genuine rather than
staged. It's deliberately not a strict copy-editor either: real customer
replies vary in phrasing, and a verifier that nitpicks every reasonable
reply would make the replan path look like the norm instead of the
exception, which undersells the point (the agent usually gets it right and
only escalates the genuinely mismatched case).

verify_flag is deliberately NOT an LLM call: whether a message got flagged
is an unambiguous boolean fact, not a judgment call, so a rule check is
both cheaper and more reliable than asking Gemini to confirm the obvious.
"""
import json
import os

from app.retry import call_with_retry

_SYSTEM_PROMPT = """You check whether a customer service reply reasonably addresses what the \
customer asked, using the practical judgment of someone doing a quick QA pass -- not a strict \
copy-editor. A reply that gives real, concrete, non-contradictory information relevant to the \
customer's underlying question should PASS, even if it doesn't use their exact wording or cover \
every minor detail.

Only FAIL a reply if it does one of these:
- Responds to a completely different issue than what the customer raised (e.g. a refund/damage \
complaint answered with a generic shipping update).
- Contradicts itself (e.g. claims the order both has and hasn't shipped).
- Is generic filler that provides no actual information at all.

Respond with ONLY valid JSON, no prose, in this exact shape:
{"passed": true, "reason": "one-sentence justification"}
"""


def _client():
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Export it before starting ml-service."
        )
    return genai.Client(api_key=api_key)


def verify_reply(message: dict, reply_text: str) -> dict:
    from google.genai import types

    client = _client()
    prompt = (
        f"Customer message: {message['subject']!r} -- {message['body']!r}\n\n"
        f"Reply sent: {reply_text!r}"
    )

    response = call_with_retry(
        client.models.generate_content,
        model=os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest"),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    raw = response.text or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"passed": False, "reason": f"verifier did not return valid JSON: {raw[:200]}"}


def verify_flag(message: dict) -> dict:
    if message.get("flagged_for_review"):
        return {"passed": True, "reason": "Message was flagged for human review."}
    return {"passed": False, "reason": "Message was not flagged."}
