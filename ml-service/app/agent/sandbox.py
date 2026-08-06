"""
Fake shared inbox the agent's tool-executor operates against for the v2
demo task ("check the shared inbox and reply to shipping status questions
using our template" -- the same example used in /analyze demos throughout
this project).

Deliberately NOT global mutable state: every function takes the inbox list
as a parameter and returns/mutates that specific list, so each job gets its
own `seed_inbox()` copy. Two concurrent demo jobs must never see or corrupt
each other's sandbox state.

Deliberately NOT a second Flask service or new routes the executor calls
over HTTP either -- ml-service runs a single gunicorn worker (see
Dockerfile), so an in-process HTTP call back into the same process would
have that one worker waiting on itself. These are plain function calls.
"""
import copy

SHIPPING_TEMPLATE_REPLY = (
    "Hi {name}, thanks for reaching out about order #{order_id}! Good news -- "
    "it has shipped and is on its way, with delivery expected within 3-5 "
    "business days. Tracking number: {tracking_number}. Let us know if you "
    "need anything else!"
)

_SEED_MESSAGES = [
    {
        "id": "msg-1",
        "from": "dana@example.com",
        "name": "Dana",
        "subject": "Where's my order?",
        "body": "Hi, I placed an order 4 days ago and haven't gotten a shipping update. Can you tell me when it'll arrive?",
        "category": "shipping_status",
        "order_id": "58291",
        "tracking_number": "1Z58291A0123456780",
        "replied": False,
        "reply_text": None,
        "flagged_for_review": False,
    },
    {
        "id": "msg-2",
        "from": "marcus@example.com",
        "name": "Marcus",
        "subject": "Shipping status?",
        "body": "Just checking on the status of my shipment, order #48213. Thanks!",
        "category": "shipping_status",
        "order_id": "48213",
        "tracking_number": "1Z48213A0123456781",
        "replied": False,
        "reply_text": None,
        "flagged_for_review": False,
    },
    {
        "id": "msg-3",
        "from": "priya@example.com",
        "name": "Priya",
        "subject": "When will my package ship?",
        "body": "Hey, wondering when my package is going to ship out. It's been a few days since I ordered.",
        "category": "shipping_status",
        "order_id": "60214",
        "tracking_number": "1Z60214A0123456782",
        "replied": False,
        "reply_text": None,
        "flagged_for_review": False,
    },
    {
        "id": "msg-4",
        "from": "jordan@example.com",
        "name": "Jordan",
        "subject": "I want a refund, this is unacceptable",
        "body": "The item I received is damaged and I want a full refund immediately, not a replacement. This is the second time this has happened.",
        # Deliberately NOT shipping_status, and deliberately no order_id/
        # tracking_number -- this is the message that should fail
        # verification if the executor naively applies the shipping
        # template to it, forcing the replan path.
        "category": "refund_request",
        "replied": False,
        "reply_text": None,
        "flagged_for_review": False,
    },
    {
        "id": "msg-5",
        "from": "sam@example.com",
        "name": "Sam",
        "subject": "Tracking number?",
        "body": "Could you send over the tracking number for my order? Want to keep an eye on it.",
        "category": "shipping_status",
        "order_id": "71325",
        "tracking_number": "1Z71325A0123456783",
        "replied": False,
        "reply_text": None,
        "flagged_for_review": False,
    },
]


def seed_inbox() -> list:
    """Fresh, independent copy of the sandbox inbox for one job."""
    return copy.deepcopy(_SEED_MESSAGES)


def list_unread(inbox: list) -> list:
    return [m for m in inbox if not m["replied"] and not m["flagged_for_review"]]


def get_message(inbox: list, message_id: str) -> dict | None:
    return next((m for m in inbox if m["id"] == message_id), None)


def send_reply(inbox: list, message_id: str, reply_text: str) -> dict:
    """Simulates sending a reply -- never a real email. Mutates the given
    inbox in place and returns a result dict describing what happened."""
    message = get_message(inbox, message_id)
    if message is None:
        return {"success": False, "error": f"no such message: {message_id}"}

    message["replied"] = True
    message["reply_text"] = reply_text
    return {
        "success": True,
        "message_id": message_id,
        "recipient": message["from"],
        "reply_text": reply_text,
    }


def flag_for_review(inbox: list, message_id: str, reason: str) -> dict:
    """The 'escalate instead of guessing' action -- what a revised plan
    reaches for after a template reply fails verification on a message that
    doesn't actually match any known template."""
    message = get_message(inbox, message_id)
    if message is None:
        return {"success": False, "error": f"no such message: {message_id}"}

    message["flagged_for_review"] = True
    return {
        "success": True,
        "message_id": message_id,
        "reason": reason,
    }


def draft_shipping_reply(inbox: list, message_id: str) -> dict:
    message = get_message(inbox, message_id)
    if message is None:
        return {"success": False, "error": f"no such message: {message_id}"}

    return {
        "success": True,
        "message_id": message_id,
        "draft": SHIPPING_TEMPLATE_REPLY.format(
            name=message["name"],
            order_id=message.get("order_id", "N/A"),
            tracking_number=message.get("tracking_number", "N/A"),
        ),
    }
