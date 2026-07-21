"""
Uses Google's Gemini API (free tier -- good fit for a student project) for the
two jobs LLMs are actually good at here: parsing free-form workflow text into
discrete task strings, and generating a short natural-language "feature hint"
per task. The LLM is NOT used to assign the automatability score itself --
that's the Random Forest's job (see app/scoring/classifier.py). Keeping the
LLM out of the scoring loop is what makes the score reproducible and
explainable via feature importances instead of an opaque LLM judgment call.
"""
import json
import os

from google import genai
from google.genai import types

from app.retry import call_with_retry

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

_PARSE_SYSTEM_PROMPT = """You split a business workflow description into discrete, atomic tasks.

Rules:
- Each task should be one distinct unit of work a single employee would perform.
- Preserve any stated frequency, tools, or systems mentioned in the original text -- do not drop details.
- Do not invent tasks that were not implied by the text.
- Also write a one-sentence "hint" per task describing why it might be repetitive, rule-based, judgment-heavy, or tool-integrated, based only on the text given.

Respond with ONLY valid JSON, no prose, in this exact shape:
{"tasks": [{"text": "...", "hint": "..."}]}
"""


class WorkflowParserError(RuntimeError):
    pass


def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise WorkflowParserError(
            "GEMINI_API_KEY is not set. Export it before starting ml-service. "
            "Get a free key at https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


def parse_workflow(workflow_text: str) -> list:
    """Return a list of {"text": str, "hint": str} dicts for one workflow."""
    client = _client()
    response = call_with_retry(
        client.models.generate_content,
        model=DEFAULT_MODEL,
        contents=workflow_text,
        config=types.GenerateContentConfig(
            system_instruction=_PARSE_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    raw = response.text or ""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkflowParserError(f"Gemini did not return valid JSON: {raw[:500]}") from exc

    tasks = parsed.get("tasks", [])
    if not tasks:
        raise WorkflowParserError("Gemini returned zero tasks for this workflow.")
    return tasks
