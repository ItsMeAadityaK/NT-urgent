"""
evaluation.py

Scores each classifier — and the full pipeline — against the dataset's
true_urgency labels, on the metrics that matter for THIS brief.

Plain accuracy is not the headline. The question the brief asks is
"does an urgent message reach a human fast?", so the key numbers are:

  urgent_recall   : of messages that truly are high/critical, how many
                    landed in the fast lane (final priority high/critical)?
  critical_recall : of truly critical messages, how many were marked
                    critical (15-minute escalation clock)?
  false_urgent    : how many truly low/medium messages were pushed into
                    the fast lane — the cost side (officer time / alert
                    fatigue).

Note on pipeline rows: the final priority deliberately includes the
access-weighting bump, which true_urgency (a content-only label) doesn't,
so exact-match accuracy isn't meaningful there and is reported as None.
"""

FAST_LANE = ("high", "critical")


def score(name: str, predictions: list[str], truths: list[str], ids: list[str],
          include_accuracy: bool = True, note: str = "") -> dict:
    urgent = [i for i, t in enumerate(truths) if t in FAST_LANE]
    critical = [i for i, t in enumerate(truths) if t == "critical"]
    routine = [i for i, t in enumerate(truths) if t not in FAST_LANE]

    return {
        "name": name,
        "note": note,
        "accuracy": (sum(p == t for p, t in zip(predictions, truths)) / len(truths)) if include_accuracy else None,
        "urgent_recall": sum(predictions[i] in FAST_LANE for i in urgent) / len(urgent),
        "critical_recall": sum(predictions[i] == "critical" for i in critical) / len(critical),
        "false_urgent": sum(predictions[i] in FAST_LANE for i in routine),
        "n_routine": len(routine),
        "missed_urgent": [ids[i] for i in urgent if predictions[i] not in FAST_LANE],
    }
