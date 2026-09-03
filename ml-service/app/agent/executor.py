"""
Tool-executor agent: runs one plan step against the sandbox (see
sandbox.py) -- never a real external system, never browser automation.
Deliberately a thin dispatch layer with no decision-making of its own; the
planner decides *what* to do, this only *does* it against sandboxed data.
"""
from app.agent import sandbox

# Actions that touch something conceptually "sent" (even though sandboxed)
# require a human-approval gate before executing. flag_for_review is
# internal-only -- it never leaves the sandbox, so it doesn't need one.
RISKY_ACTIONS = {"send_reply"}


def execute_step(inbox: list, action: str, message_id: str, **kwargs) -> dict:
    if action == "send_reply":
        draft = sandbox.draft_shipping_reply(inbox, message_id)
        if not draft.get("success"):
            return draft
        return sandbox.send_reply(inbox, message_id, draft["draft"])

    if action == "flag_for_review":
        reason = kwargs.get(
            "reason", "Escalated by the agent after a failed automated attempt."
        )
        return sandbox.flag_for_review(inbox, message_id, reason)

    return {"success": False, "error": f"unknown action: {action}"}
