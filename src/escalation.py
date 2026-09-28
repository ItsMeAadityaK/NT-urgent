"""
escalation.py

Escalation timeout logic ("dead-man's switch").

Core trust-twist requirement from the brief: the system NEVER responds to
the sender itself — it only ever escalates to a human. This module's job
is to make sure a flagged-urgent item doesn't just sit unacknowledged.

Rule of thumb (tune these once you have real data to test against):
    critical -> must be acknowledged within 15 minutes, else escalate
    high     -> must be acknowledged within 1 hour, else escalate
    medium   -> must be acknowledged within 4 hours, else escalate
    low      -> no auto-escalation

Schema this touches (matches data/messages.csv columns):
    acknowledged     : bool
    escalated        : bool
    escalation_time  : timestamp, blank until escalated
"""

from datetime import datetime, timedelta

# Minutes allowed before an unacknowledged item auto-escalates, per urgency level.
TIMEOUT_MINUTES = {
    "critical": 15,
    "high": 60,
    "medium": 240,
    "low": None,  # never auto-escalates
}


def check_escalation_timeout(message: dict, current_time: datetime = None) -> dict:
    """
    Check whether a message has breached its acknowledgement timeout and
    should be auto-escalated.

    Args:
        message: dict with at least:
            urgency_score   (str: low/medium/high/critical)
            timestamp       (datetime: when the message arrived)
            acknowledged    (bool)
        current_time: for testing — defaults to now if not supplied.

    Returns:
        dict: {"should_escalate": bool, "reason": str}
    """
    current_time = current_time or datetime.now()

    if message.get("acknowledged"):
        return {"should_escalate": False, "reason": "Already acknowledged by a human."}

    urgency = message.get("urgency_score", "low")
    timeout = TIMEOUT_MINUTES.get(urgency)

    if timeout is None:
        return {"should_escalate": False, "reason": f"'{urgency}' messages do not auto-escalate."}

    elapsed = current_time - message["timestamp"]
    if elapsed > timedelta(minutes=timeout):
        return {
            "should_escalate": True,
            "reason": f"Unacknowledged '{urgency}' message has been waiting {elapsed} "
                      f"(limit was {timeout} minutes) — auto-escalating to supervisor.",
        }

    return {
        "should_escalate": False,
        "reason": f"Still within the {timeout}-minute window for '{urgency}' items.",
    }


if __name__ == "__main__":
    # Quick manual test — a critical message that arrived 20 minutes ago,
    # still unacknowledged, should trigger escalation.
    test_message = {
        "urgency_score": "critical",
        "timestamp": datetime.now() - timedelta(minutes=20),
        "acknowledged": False,
    }
    print(check_escalation_timeout(test_message))

    # A high message that arrived 5 minutes ago should NOT escalate yet.
    test_message_2 = {
        "urgency_score": "high",
        "timestamp": datetime.now() - timedelta(minutes=5),
        "acknowledged": False,
    }
    print(check_escalation_timeout(test_message_2))