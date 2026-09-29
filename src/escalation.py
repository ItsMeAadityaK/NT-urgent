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


# Escalation chain. Level 1 fires when the timeout is breached; level 2
# fires at twice the timeout if it's STILL unacknowledged — a dead-man's
# switch that keeps climbing rather than alerting once and going quiet.
ESCALATION_CHAIN = {
    1: "Shift supervisor",
    2: "Duty manager",
}


def check_escalation_timeout(message: dict, current_time: datetime = None) -> dict:
    """
    Check whether a message has breached its acknowledgement timeout and
    should be auto-escalated.

    Args:
        message: dict with at least:
            urgency_score   (str: low/medium/high/critical) — pass the FINAL
                            priority the officer sees (after access weighting
                            and safety-net floors), so the clock matches the
                            colour on screen.
            timestamp       (datetime: when the message arrived)
            acknowledged    (bool)
        current_time: for testing — defaults to now if not supplied.

    Returns:
        dict: {"should_escalate": bool, "level": 0|1|2, "escalate_to": str|None,
               "waited_minutes": int, "sla_minutes": int|None, "reason": str}
    """
    current_time = current_time or datetime.now()
    urgency = message.get("urgency_score", "low")
    timeout = TIMEOUT_MINUTES.get(urgency)
    waited = int((current_time - message["timestamp"]).total_seconds() // 60)
    base = {"waited_minutes": waited, "sla_minutes": timeout}

    if message.get("acknowledged"):
        return {**base, "should_escalate": False, "level": 0, "escalate_to": None,
                "reason": "Already acknowledged by a human."}

    if timeout is None:
        return {**base, "should_escalate": False, "level": 0, "escalate_to": None,
                "reason": f"'{urgency}' messages do not auto-escalate."}

    if waited > timeout:
        level = 2 if waited > 2 * timeout else 1
        target = ESCALATION_CHAIN[level]
        return {
            **base, "should_escalate": True, "level": level, "escalate_to": target,
            "reason": f"Unacknowledged '{urgency}' item has waited {waited} min "
                      f"(limit {timeout} min) \u2014 escalated to {target}"
                      + (" (second escalation: limit breached twice over)." if level == 2 else "."),
        }

    return {
        **base, "should_escalate": False, "level": 0, "escalate_to": None,
        "reason": f"Within the {timeout}-minute window for '{urgency}' items ({timeout - waited} min left).",
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