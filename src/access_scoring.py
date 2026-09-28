"""
access_scoring.py

Remote-access-aware urgency weighting.

Core idea: two messages with identical content shouldn't necessarily get
the same operational priority if one sender has easy access to
alternative help (nearby services, can drive to a clinic themselves) and
the other doesn't (cut off by flooding, no nearby services, no vehicle
access). This module adjusts/annotates the RAW urgency score from the
classifier with that context.

Important design note: this does NOT overwrite the classifier's urgency
score (that would hide the original signal). It adds a separate
"access_adjusted_priority" so both the raw content-based urgency AND the
logistics context are visible to the human — consistent with the brief's
requirement that the human owns the final call and can see why.

Schema this touches (matches data/messages.csv columns):
    access_status : normal / limited / cut-off
    urgency_score : the LLM/baseline classification (read-only input here)
"""

# How much each access status bumps effective priority, expressed as
# levels-up on the low/medium/high/critical scale. Tune later.
ACCESS_PRIORITY_BUMP = {
    "normal": 0,
    "limited": 1,
    "cut-off": 2,
}

URGENCY_LEVELS = ["low", "medium", "high", "critical"]


def apply_access_weighting(urgency_score: str, access_status: str) -> dict:
    """
    Adjust an urgency score based on how reachable the sender currently is.

    Args:
        urgency_score: the raw classification (low/medium/high/critical)
        access_status: normal / limited / cut-off

    Returns:
        dict: {
            "raw_urgency_score": str,        # unchanged, for transparency
            "access_status": str,
            "access_adjusted_priority": str,  # bumped-up value if applicable
            "reason": str,
        }
    """
    bump = ACCESS_PRIORITY_BUMP.get(access_status, 0)

    if urgency_score not in URGENCY_LEVELS:
        return {
            "raw_urgency_score": urgency_score,
            "access_status": access_status,
            "access_adjusted_priority": urgency_score,
            "reason": f"Unrecognised urgency level '{urgency_score}' — no adjustment applied.",
        }

    current_index = URGENCY_LEVELS.index(urgency_score)
    adjusted_index = min(current_index + bump, len(URGENCY_LEVELS) - 1)
    adjusted_score = URGENCY_LEVELS[adjusted_index]

    if bump == 0:
        reason = "Sender has normal access to alternative help — no adjustment."
    else:
        reason = (f"Sender access status is '{access_status}' (limited alternative help "
                  f"available) — priority bumped from '{urgency_score}' to '{adjusted_score}'.")

    return {
        "raw_urgency_score": urgency_score,
        "access_status": access_status,
        "access_adjusted_priority": adjusted_score,
        "reason": reason,
    }


if __name__ == "__main__":
    # Same underlying "high" urgency, two different access situations.
    print(apply_access_weighting("high", "normal"))
    print(apply_access_weighting("high", "cut-off"))
    print(apply_access_weighting("medium", "limited"))