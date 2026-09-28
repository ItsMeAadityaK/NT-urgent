"""
dropout_detector.py

Comms-dropout detection ("silence as a danger signal").

This is one of the project's key differentiators: in a disaster/remote
context, if someone sends an urgent message and then goes silent for
longer than expected, that silence can itself be a risk signal — not
just "they haven't followed up," but possibly "they lost power/network,
or the situation got worse and they can't reach out again."

This module does NOT classify individual messages — it looks across a
sender's message HISTORY to detect gaps that look abnormal given their
last known urgency level.

Schema this touches (matches data/messages.csv columns):
    sender_id     : used to group a sender's message history
    timestamp     : used to compute gaps between messages
    urgency_score : used to decide what counts as a suspicious gap
"""

from datetime import datetime, timedelta

# If a sender's last message was this urgency level, a gap longer than
# this many hours with no follow-up is flagged as a possible dropout.
# (Placeholder values — tune once you have real data to test against.)
DROPOUT_THRESHOLD_HOURS = {
    "critical": 2,
    "high": 6,
    "medium": 24,
    "low": None,  # not worth flagging for routine messages
}


def check_dropout(sender_history: list[dict], current_time: datetime = None) -> dict:
    """
    Check whether a sender has gone suspiciously silent after an urgent message.

    Args:
        sender_history: list of message dicts for ONE sender, each with at
            least "timestamp" and "urgency_score", sorted oldest to newest.
        current_time: for testing — defaults to now if not supplied.

    Returns:
        dict: {"dropout_flag": bool, "reason": str}
    """
    if not sender_history:
        return {"dropout_flag": False, "reason": "No message history for this sender."}

    current_time = current_time or datetime.now()
    last_message = sender_history[-1]
    last_urgency = last_message.get("urgency_score", "low")
    last_timestamp = last_message["timestamp"]

    threshold = DROPOUT_THRESHOLD_HOURS.get(last_urgency)
    if threshold is None:
        return {"dropout_flag": False, "reason": f"Last message was '{last_urgency}' — dropout not tracked at this level."}

    silence_duration = current_time - last_timestamp

    if silence_duration > timedelta(hours=threshold):
        return {
            "dropout_flag": True,
            "reason": f"Sender's last message was '{last_urgency}' urgency, "
                      f"{silence_duration} ago with no follow-up "
                      f"(expected within {threshold}h) — possible comms loss, worth a welfare check.",
        }

    return {
        "dropout_flag": False,
        "reason": f"Still within the expected {threshold}h follow-up window.",
    }


if __name__ == "__main__":
    # Sender sent a critical message 3 hours ago and nothing since -> should flag.
    history = [
        {"timestamp": datetime.now() - timedelta(hours=3), "urgency_score": "critical"},
    ]
    print(check_dropout(history))

    # Sender sent a medium message 1 hour ago -> should NOT flag yet.
    history_2 = [
        {"timestamp": datetime.now() - timedelta(hours=1), "urgency_score": "medium"},
    ]
    print(check_dropout(history_2))