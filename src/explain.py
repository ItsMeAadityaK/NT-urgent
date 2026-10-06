"""
explain.py

Builds the one-line "why" an officer sees on every item without clicking
anything. The full step-by-step reasoning (triage.decide_priority's
"steps") sits behind the "why?" toggle; this is the at-a-glance version.

Kept deliberately plain: an officer triaging 150 items in a shift needs
to know in one read what drove the call and who owns it.
"""


def headline(decision: dict, route: dict) -> str:
    parts = []

    src = "LLM" if decision["content_source"] == "llm" else "baseline (LLM offline)"
    parts.append(f"{src} said {decision['content_urgency']}")

    if decision["safety_floor"] and decision["after_safety_net"] != decision["content_urgency"]:
        sig = decision["safety_signals"][0]
        parts.append(f"safety tripwire “{sig['matched']}” → {decision['after_safety_net']}")

    if decision.get("language_flag"):
        parts.append("language not recognised → at least high, a person must read it in full")

    if decision["access_adjusted_priority"] != decision["after_safety_net"]:
        parts.append(f"sender access limited → {decision['access_adjusted_priority']}")

    parts.append(f"routed to {route['team']}")
    return " · ".join(parts)
