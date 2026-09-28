"""
server.py

Flask backend for the Correspondence Triage console — replaces app.py
(the Streamlit build). All the actual logic (classifier.py,
baseline_model.py, access_scoring.py, dropout_detector.py,
escalation.py) is unchanged; this just exposes it over a small JSON API
so a hand-built frontend (static/) can render it without Streamlit's
layout constraints.

New here (not in the Streamlit build): acknowledgement is now real and
stateful — POST /api/acknowledge actually flips a message's acknowledged
flag server-side, which feeds back into the escalation check. In app.py
this was hardcoded to False.

Also fixed here: dropout_detector.py expects each history entry to have
an "urgency_score" key (see its docstring), but the raw message dicts
from messages.py use "llm_urgency" — that mismatch meant DROPOUT_THRESHOLD_HOURS.get()
always fell through to the "low"/None case and dropout could never fire,
regardless of how long a sender had gone silent. _build_state() below
now translates the key when building history for check_dropout(), which
is the actual fix (dropout_detector.py itself is untouched — its
documented contract was correct, the caller just wasn't honouring it).

Run with:
    python server.py
then open http://127.0.0.1:5000
"""

import os
import sys
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "data"))

from baseline_model import classify_urgency_baseline, train_baseline_from_dataset
from access_scoring import apply_access_weighting
from dropout_detector import check_dropout
from escalation import check_escalation_timeout
from messages import get_sample_messages, get_sender_history, SIMULATION_START

URGENCY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SIM_MAX_MINUTES = 480  # 8-hour dispatch shift — long enough for critical (2h) and
                       # high (6h) dropout thresholds to actually be reachable.

app = Flask(__name__, static_folder="static", static_url_path="")

# In-memory acknowledgement store: message_id -> {"acknowledged": bool, "ack_at_minutes": int}
_ack_store = {}

# Train the baseline on the real 152-message dataset (proper 80/20 split,
# accuracy measured on the held-out test set) once at startup, rather than
# the tiny 10-example placeholder set baseline_model.py shipped with.
_ALL_MESSAGES = get_sample_messages()
_BASELINE_EVAL = train_baseline_from_dataset(
    [m["raw_text"] for m in _ALL_MESSAGES],
    [m["true_urgency"] for m in _ALL_MESSAGES],
)


def _build_state(minutes_elapsed: int):
    minutes_elapsed = max(0, min(SIM_MAX_MINUTES, minutes_elapsed))
    current_time = SIMULATION_START + timedelta(minutes=minutes_elapsed)

    processed = []
    for msg in get_sample_messages():
        if msg["timestamp"] > current_time:
            continue

        ack = _ack_store.get(msg["message_id"], {"acknowledged": False})

        baseline_result = classify_urgency_baseline(msg["raw_text"])
        access_result = apply_access_weighting(msg["llm_urgency"], msg["access_status"])

        # Translate to the {"timestamp", "urgency_score"} shape check_dropout()
        # actually expects (see module docstring above on the key mismatch).
        raw_history = get_sender_history(msg["sender_id"], current_time)
        history = [{"timestamp": h["timestamp"], "urgency_score": h["llm_urgency"]} for h in raw_history]
        dropout_result = check_dropout(history, current_time)

        escalation_result = check_escalation_timeout(
            {
                "urgency_score": msg["llm_urgency"],
                "timestamp": msg["timestamp"],
                "acknowledged": ack["acknowledged"],
            },
            current_time,
        )

        processed.append({
            "message_id": msg["message_id"],
            "timestamp": msg["timestamp"].isoformat(),
            "channel": msg["channel"],
            "sender_id": msg["sender_id"],
            "raw_text": msg["raw_text"],
            "location": msg["location"],
            "access_status": msg["access_status"],
            "llm_urgency": msg["llm_urgency"],
            "llm_reason": msg["llm_reason"],
            "true_urgency": msg["true_urgency"],
            "baseline_urgency": baseline_result["urgency_score"],
            "access_adjusted_priority": access_result["access_adjusted_priority"],
            "access_reason": access_result["reason"],
            "dropout_flag": dropout_result["dropout_flag"],
            "dropout_reason": dropout_result["reason"],
            "acknowledged": ack["acknowledged"],
            "should_escalate": escalation_result["should_escalate"],
            "escalation_reason": escalation_result["reason"],
            "fairness_pair": msg.get("fairness_pair"),
            "fairness_style": msg.get("fairness_style"),
        })

    processed.sort(key=lambda m: (URGENCY_ORDER.get(m["access_adjusted_priority"], 9), m["timestamp"]))

    fairness_pairs = {}
    for m in processed:
        if not m["fairness_pair"]:
            continue
        fairness_pairs.setdefault(m["fairness_pair"], {})[m["fairness_style"]] = m
    fairness_pairs_list = [
        {"pair_id": pid, **sides} for pid, sides in sorted(fairness_pairs.items())
    ]

    return {
        "current_time": current_time.isoformat(),
        "minutes_elapsed": minutes_elapsed,
        "sim_max_minutes": SIM_MAX_MINUTES,
        "messages": processed,
        "fairness_pairs": fairness_pairs_list,
        "baseline_eval": _BASELINE_EVAL,
    }


@app.get("/api/state")
def api_state():
    minutes = request.args.get("minutes", default=30, type=int)
    return jsonify(_build_state(minutes))


@app.post("/api/acknowledge")
def api_acknowledge():
    body = request.get_json(force=True, silent=True) or {}
    message_id = body.get("message_id")
    minutes = body.get("minutes", 30)
    if not message_id:
        return jsonify({"error": "message_id required"}), 400

    _ack_store[message_id] = {"acknowledged": True}
    return jsonify(_build_state(minutes))


@app.post("/api/reset")
def api_reset():
    minutes = (request.get_json(force=True, silent=True) or {}).get("minutes", 30)
    _ack_store.clear()
    return jsonify(_build_state(minutes))


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
