"""
triage.py

The single place where a message's final priority is decided. Every
signal is combined here in a fixed, explainable order:

  1. CONTENT URGENCY — what the message says.
       LLM online  -> the LLM's classification.
       LLM offline -> the local baseline model (degraded mode; the item is
                      marked so the officer knows it wasn't LLM-checked).
  2. SAFETY FLOOR   — deterministic tripwires (safety_net.py) can raise
                      content urgency, never lower it.
  2b. READABILITY   — text the system cannot read (another language, or too garbled)
                      is never allowed to rank below 'high' (language_check.py), so
                      a message in a language we don't understand is never buried.
  3. ACCESS WEIGHT  — how reachable the sender is (access_scoring.py) can
                      raise it further, never lower it.
  4. SECOND-OPINION FLOOR — if the backup model thinks a message is high or critical
                      but the AI model rated it lower, the final priority is at least
                      'high', so a person reads it. Two readers disagreeing towards
                      "urgent" is itself a reason to look. It is a plain minimum, applied
                      after access weighting. (TRIAGE_SECOND_OPINION_FLOOR=0 switches it off.)

Nothing in this chain can lower a priority. Each step records what it did
so the officer sees the full reasoning ("why was this prioritised this
way?"), and the escalation clock runs off the FINAL priority, so the
colour on screen and the timer always agree.
"""

import os

from access_scoring import apply_access_weighting
from language_check import check_readable
from safety_net import check_safety_net

URGENCY_LEVELS = ["low", "medium", "high", "critical"]
SECOND_OPINION_FLOOR = os.environ.get("TRIAGE_SECOND_OPINION_FLOOR", "1") != "0"


def _max(a: str, b: str) -> str:
    if b is None:
        return a
    return a if URGENCY_LEVELS.index(a) >= URGENCY_LEVELS.index(b) else b


def decide_priority(text: str, access_status: str, llm_result: dict | None, baseline_urgency: str) -> dict:
    """
    Args:
        text: the raw message.
        access_status: normal / limited / cut-off.
        llm_result: {"ok": True, "urgency_score", "flag_reason"} if the LLM
            classified it; None or {"ok": False, ...} if it's unavailable.
        baseline_urgency: the local model's prediction.

    Returns:
        dict with every intermediate value plus "steps" — a list of
        human-readable explanation strings in the order they were applied.
    """
    steps = []
    llm_ok = bool(llm_result and llm_result.get("ok"))

    if llm_ok:
        content = llm_result["urgency_score"]
        source = "llm"
        steps.append(f"The AI model classified the content as '{content}': {llm_result.get('flag_reason', '')}")
    else:
        content = baseline_urgency
        source = "baseline"
        why = (llm_result or {}).get("error", "AI offline")
        steps.append(f"AI model unavailable ({why}) — DEGRADED MODE: local baseline model classified the "
                     f"content as '{content}'. Not AI-checked; officer should read it in full.")

    safety = check_safety_net(text)
    floored = _max(content, safety["floor"])
    if floored != content:
        steps.append(f"{safety['reason']} Raised '{content}' → '{floored}'.")
    elif safety["floor"]:
        steps.append(f"{safety['reason']} (Already at or above the floor.)")

    readable = check_readable(text)
    if not readable["readable"]:
        raised = _max(floored, "high")
        steps.append(readable["reason"] + (f" Raised '{floored}' → '{raised}' so a person reads it in full."
                                           if raised != floored else " (Already at or above 'high'.)"))
        floored = raised

    access = apply_access_weighting(floored, access_status)
    final = access["access_adjusted_priority"]
    steps.append(access["reason"])

    # Second-opinion floor. Applied last, so it is a plain minimum ("at least high") and is never
    # stacked on top of the access bump: a routine complaint should not jump two levels.
    if (SECOND_OPINION_FLOOR and llm_ok and URGENCY_LEVELS.index(baseline_urgency) >= URGENCY_LEVELS.index("high")
            and URGENCY_LEVELS.index(content) < URGENCY_LEVELS.index("high")):
        raised = _max(final, "high")
        if raised != final:
            steps.append(f"The backup model rates this '{baseline_urgency}' but the AI model said '{content}'. "
                         f"When the two disagree towards urgent, it is held at 'high' until a person has read it.")
            final = raised

    # Second opinion: flag (don't act on) cases where the baseline rates it
    # higher than the LLM did, so the officer can take a second look.
    second_opinion = None
    if llm_ok and URGENCY_LEVELS.index(baseline_urgency) > URGENCY_LEVELS.index(content):
        second_opinion = (f"Second opinion: the baseline model rates this '{baseline_urgency}', higher than "
                          f"the AI model's '{content}'. Worth a second look.")

    return {
        "content_urgency": content,
        "content_source": source,
        "safety_floor": safety["floor"],
        "safety_signals": safety["signals"],
        "after_safety_net": floored,
        "language_flag": not readable["readable"],
        "access_adjusted_priority": final,
        "access_reason": access["reason"],
        "degraded": not llm_ok,
        "second_opinion": second_opinion,
        "steps": steps,
    }
