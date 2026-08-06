from app.agent import sandbox


def test_seed_inbox_returns_five_unread_unflagged_messages():
    inbox = sandbox.seed_inbox()
    assert len(inbox) == 5
    assert all(not m["replied"] and not m["flagged_for_review"] for m in inbox)


def test_seed_inbox_returns_independent_copies():
    inbox_a = sandbox.seed_inbox()
    inbox_b = sandbox.seed_inbox()
    sandbox.send_reply(inbox_a, "msg-1", "reply")
    assert inbox_a[0]["replied"] is True
    assert inbox_b[0]["replied"] is False  # unaffected by inbox_a's mutation


def test_list_unread_excludes_replied_and_flagged():
    inbox = sandbox.seed_inbox()
    sandbox.send_reply(inbox, "msg-1", "reply")
    sandbox.flag_for_review(inbox, "msg-4", "not a shipping question")

    unread = sandbox.list_unread(inbox)

    assert {m["id"] for m in unread} == {"msg-2", "msg-3", "msg-5"}


def test_send_reply_marks_message_replied():
    inbox = sandbox.seed_inbox()
    result = sandbox.send_reply(inbox, "msg-2", "Your order is on its way!")

    assert result["success"] is True
    assert result["message_id"] == "msg-2"
    message = sandbox.get_message(inbox, "msg-2")
    assert message["replied"] is True
    assert message["reply_text"] == "Your order is on its way!"


def test_send_reply_unknown_message_fails_cleanly():
    inbox = sandbox.seed_inbox()
    result = sandbox.send_reply(inbox, "does-not-exist", "hi")
    assert result["success"] is False


def test_flag_for_review_marks_message_flagged():
    inbox = sandbox.seed_inbox()
    result = sandbox.flag_for_review(inbox, "msg-4", "refund request, not shipping")

    assert result["success"] is True
    message = sandbox.get_message(inbox, "msg-4")
    assert message["flagged_for_review"] is True


def test_draft_shipping_reply_includes_recipient_name():
    inbox = sandbox.seed_inbox()
    draft = sandbox.draft_shipping_reply(inbox, "msg-1")
    assert draft["success"] is True
    assert "Dana" in draft["draft"]
