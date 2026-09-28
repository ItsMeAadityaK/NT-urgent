"""
classifier.py

Core urgency classification for the correspondence triage tool.

This is the LLM-based classifier — the main scoring engine.
A separate baseline model (TF-IDF + Logistic Regression) lives in
baseline_model.py for comparison later.

Schema this function produces (matches data/messages.csv columns):
    urgency_score : one of "low", "medium", "high", "critical"
    flag_reason   : short explanation string
    model_source  : "llm"
"""

import os
import json

# Set to True while developing so you don't need an API key / spend API
# calls just to test the pipeline plumbing. Flip to False once you're
# ready to test against the real model.
USE_MOCK = True

URGENCY_LEVELS = ["low", "medium", "high", "critical"]

SYSTEM_PROMPT = """You are an urgency triage assistant for a government
correspondence unit. You are NOT responding to the sender and you are NOT
making the final decision — a human always makes the final call. Your job
is only to help a human prioritise their queue.

Read the message and classify its urgency into exactly one of:
low, medium, high, critical

Base the classification on:
- safety risk (is anyone in physical danger or at risk of harm)
- time-criticality (does this need action today vs this month)
- vulnerability indicators (children, isolation, lack of alternatives)

Do NOT penalise the sender for informal writing style, spelling, or
non-standard English. Judge the substance of what is being reported,
not how it is phrased.

Respond ONLY with valid JSON in this exact shape, nothing else:
{"urgency_score": "<low|medium|high|critical>", "flag_reason": "<one sentence explaining the key signal that drove this classification>"}
"""

# Hardcoded mock responses for pipeline testing without hitting the API.
# Add more test cases here as you think of edge cases.
_MOCK_RESPONSES = {
    "when does my permit renew? just checking the date":
        {"urgency_score": "low", "flag_reason": "Routine administrative query with no time pressure or risk indicators."},
    "no water for 3 days, community cut off by flooding, elderly residents affected":
        {"urgency_score": "critical", "flag_reason": "Immediate health/safety risk (no water) compounded by physical isolation and a vulnerable group (elderly)."},
    "can u help my roof gone in the storm last nite got no where to stay":
        {"urgency_score": "high", "flag_reason": "Loss of shelter following a storm event indicates urgent, time-critical housing need."},
}


def classify_urgency(message_text: str) -> dict:
    """
    Classify a single message's urgency.

    Args:
        message_text: the raw text of the correspondence item.

    Returns:
        dict with keys: urgency_score, flag_reason, model_source
    """
    if USE_MOCK:
        result = _MOCK_RESPONSES.get(
            message_text.strip().lower(),
            {"urgency_score": "medium", "flag_reason": "[MOCK] No canned response for this exact text — default placeholder."}
        )
    else:
        result = _call_llm(message_text)

    result["model_source"] = "llm"
    return result


def _call_llm(message_text: str) -> dict:
    """Real API call path — only used when USE_MOCK = False."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message_text}],
    )

    raw_text = response.content[0].text
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {"urgency_score": "medium", "flag_reason": f"[PARSE ERROR] Raw model output: {raw_text[:200]}"}

    return parsed


if __name__ == "__main__":
    # Quick manual test — run this file directly to sanity-check the pipeline.
    test_messages = [
        "when does my permit renew? just checking the date",
        "no water for 3 days, community cut off by flooding, elderly residents affected",
        "can u help my roof gone in the storm last nite got no where to stay",
    ]

    for msg in test_messages:
        result = classify_urgency(msg)
        print(f"\nMessage: {msg}")
        print(f"  -> {result}")