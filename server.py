"""
server.py

Flask backend for the Correspondence Triage dispatch console.

Pipeline per message (all the decision logic lives in src/, this file
just orchestrates it and holds the officer-action state):

    text ──► LLM (Claude) ─────────┐
         └─► baseline (TF-IDF LR) ─┤► triage.decide_priority ─► routing ─► draft acknowledgement
         └─► safety-net tripwires ─┤      (content → safety floor → access weighting;
    access status ─────────────────┘       nothing can lower a priority)
                                              │
    sim clock + officer acks ────────────────►├─► escalation chain (supervisor → duty manager)
    sender history ──────────────────────────►└─► comms-dropout detector

The system never contacts the sender. Drafts need an officer's approval,
and escalation always goes to a named human role.

LLM source for the dataset: if data/llm_results.json exists (produced by
scripts/run_llm_batch.py) those real Claude outputs are used; otherwise
the hand-authored stand-in values in messages.py are used and the UI says
so. ?llm=off simulates an LLM outage: every item is re-triaged in
degraded mode (baseline + safety net) so you can see the system keeps
working without it.

Run with:
    python server.py
then open http://127.0.0.1:5050
"""

import json
import os
import statistics
import sys
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "data"))

from acknowledgement import draft_acknowledgement  # noqa: E402
from baseline_model import classify_urgency_baseline, train_baseline_from_dataset  # noqa: E402
from classifier import classify_urgency, llm_configured  # noqa: E402
from dropout_detector import check_dropout  # noqa: E402
from escalation import check_escalation_timeout  # noqa: E402
from evaluation import score  # noqa: E402
from explain import headline  # noqa: E402
from messages import SIMULATION_START, get_sample_messages  # noqa: E402
from routing import route_message  # noqa: E402
from safety_net import check_safety_net  # noqa: E402
from triage import decide_priority  # noqa: E402

URGENCY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SIM_MAX_MINUTES = 480  # 8-hour shift — long enough for the 2h/6h dropout thresholds to be reachable.
LLM_RESULTS_PATH = os.path.join(ROOT, "data", "llm_results.json")

app = Flask(__name__, static_folder="static", static_url_path="")

# ---------------------------------------------------------------------------
# Officer-action state (in memory — resets on restart; fine for a demo).
# Every action records the sim minute it happened, so scrubbing the clock
# backwards correctly shows the item as not-yet-actioned.
# ---------------------------------------------------------------------------
_acks = {}             # message_id -> minute acknowledged
_draft_approvals = {}  # message_id -> minute approved
_welfare_checks = {}   # sender_id  -> minute a welfare check was logged

# Messages added live from the "Try a Message" tab via "Add to queue".
# Kept separate from _MESSAGES (the fixed, reproducible 152-message
# dataset the evaluation numbers are measured against) so trying things
# live can never change the headline accuracy/recall figures. Each one
# is triaged once, for both LLM-online and LLM-outage, same as the
# startup dataset below.
_submitted = []
_submitted_static = {True: {}, False: {}}
_submit_counter = [0]

# ---------------------------------------------------------------------------
# Static, clock-independent work done once at startup.
# ---------------------------------------------------------------------------
_MESSAGES = get_sample_messages()
_BASELINE_EVAL = train_baseline_from_dataset(
    [m["raw_text"] for m in _MESSAGES],
    [m["true_urgency"] for m in _MESSAGES],
)
_BASELINE_OOF = dict(zip((m["message_id"] for m in _MESSAGES), _BASELINE_EVAL["oof_predictions"]))


def _load_llm_results():
    if os.path.exists(LLM_RESULTS_PATH):
        with open(LLM_RESULTS_PATH) as f:
            payload = json.load(f)
        results = {mid: {"ok": True, **r} for mid, r in payload["results"].items()}
        label = f"Real Claude outputs ({payload['model']}, cached run {payload['generated_at'][:10]})"
        return results, label, True
    results = {m["message_id"]: {"ok": True, "urgency_score": m["llm_urgency"], "flag_reason": m["llm_reason"]}
               for m in _MESSAGES}
    label = ("Hand-authored stand-in values (not a live model) — run scripts/run_llm_batch.py "
             "with an API key to replace them with real Claude outputs")
    return results, label, False


_LLM_RESULTS, _LLM_SOURCE_LABEL, _LLM_IS_REAL = _load_llm_results()


def _triage(msg: dict, llm_online: bool) -> dict:
    llm = _LLM_RESULTS.get(msg["message_id"]) if llm_online else {"ok": False, "error": "simulated LLM outage"}
    if llm is None:
        llm = {"ok": False, "error": "no cached LLM result for this message"}
    return _finish_triage(msg, llm)


def _finish_triage(msg: dict, llm: dict) -> dict:
    # _BASELINE_OOF only has entries for the fixed 152-message dataset (those are
    # out-of-fold cross-validated predictions). A message typed into "Try a
    # Message" isn't in that dataset, so it gets a normal (in-sample) prediction
    # from the production model instead — still real, just not cross-validated.
    baseline = _BASELINE_OOF.get(msg["message_id"])
    if baseline is None:
        baseline = classify_urgency_baseline(msg["raw_text"])["urgency_score"]
    decision = decide_priority(msg["raw_text"], msg["access_status"], llm, baseline)
    route = route_message(msg["raw_text"], decision["access_adjusted_priority"])
    draft = draft_acknowledgement(msg["message_id"], decision["access_adjusted_priority"],
                                  route["category"], route["team"], msg["channel"])
    return {"llm": llm, "decision": decision, "route": route, "draft": draft, "baseline_urgency": baseline}


def _triage_submitted(msg: dict, llm_online: bool) -> dict:
    """Same resolution rule as /api/classify: a real call if a key is configured
    and we're not simulating an outage, otherwise an honest 'unavailable'."""
    if not llm_online:
        llm = {"ok": False, "error": "simulated LLM outage"}
    elif llm_configured():
        llm = classify_urgency(msg["raw_text"])
    else:
        llm = {"ok": False, "error": "no API key configured on this server"}
    return _finish_triage(msg, llm)


_STATIC = {mode: {m["message_id"]: _triage(m, mode) for m in _MESSAGES} for mode in (True, False)}


def _evaluation():
    ids = [m["message_id"] for m in _MESSAGES]
    truths = [m["true_urgency"] for m in _MESSAGES]
    online, offline = _STATIC[True], _STATIC[False]
    llm_note = "" if _LLM_IS_REAL else "Stand-in values equal the answer key by construction — not a real measurement."
    return {
        "llm_source": _LLM_SOURCE_LABEL,
        "llm_is_real": _LLM_IS_REAL,
        "rows": [
            score("LLM alone", [online[i]["decision"]["content_urgency"] for i in ids], truths, ids, note=llm_note),
            score(f"Baseline alone ({_BASELINE_EVAL['n_folds']}-fold cross-validated)",
                  [_BASELINE_OOF[i] for i in ids], truths, ids),
            score("Safety-net rules alone", [check_safety_net(m["raw_text"])["floor"] or "low" for m in _MESSAGES],
                  truths, ids, note="Rules only ever raise; unmatched messages count as low here."),
            score("Full pipeline — LLM online", [online[i]["decision"]["access_adjusted_priority"] for i in ids],
                  truths, ids, include_accuracy=False, note=llm_note),
            score("Full pipeline — LLM OUTAGE (baseline + safety net + access)",
                  [offline[i]["decision"]["access_adjusted_priority"] for i in ids], truths, ids,
                  include_accuracy=False, note="What still reaches a human if the LLM is unavailable."),
        ],
        "baseline_per_class_recall": _BASELINE_EVAL["per_class_recall"],
    }


_EVALUATION = _evaluation()


def _arrival_minute(msg) -> int:
    return int((msg["timestamp"] - SIMULATION_START).total_seconds() // 60)


# ---------------------------------------------------------------------------
# Clock-dependent state
# ---------------------------------------------------------------------------
def _build_state(minutes_elapsed: int, llm_online: bool):
    minutes_elapsed = max(0, min(SIM_MAX_MINUTES, minutes_elapsed))
    current_time = SIMULATION_START + timedelta(minutes=minutes_elapsed)
    static = {**_STATIC[llm_online], **_submitted_static[llm_online]}
    all_messages = _MESSAGES + _submitted
    arrived = [m for m in all_messages if m["timestamp"] <= current_time]

    # Sender histories for dropout detection, using the triaged content
    # urgency (content + safety floor) as the detector's urgency_score.
    histories = {}
    for m in sorted(arrived, key=lambda m: m["timestamp"]):
        histories.setdefault(m["sender_id"], []).append({
            "timestamp": m["timestamp"],
            "urgency_score": static[m["message_id"]]["decision"]["after_safety_net"],
        })

    processed = []
    for msg in arrived:
        mid = msg["message_id"]
        s = static[mid]
        decision, route, llm = s["decision"], s["route"], s["llm"]
        priority = decision["access_adjusted_priority"]

        ack_minute = _acks.get(mid)
        acknowledged = ack_minute is not None and ack_minute <= minutes_elapsed
        approved_minute = _draft_approvals.get(mid)
        draft_approved = approved_minute is not None and approved_minute <= minutes_elapsed

        escalation = check_escalation_timeout(
            {"urgency_score": priority, "timestamp": msg["timestamp"], "acknowledged": acknowledged},
            current_time,
        )

        dropout = check_dropout(histories[msg["sender_id"]], current_time)
        is_latest = histories[msg["sender_id"]][-1]["timestamp"] == msg["timestamp"]
        welfare_minute = _welfare_checks.get(msg["sender_id"])
        welfare_logged = welfare_minute is not None and welfare_minute <= minutes_elapsed
        # Show the dropout flag once per sender (on their latest message) and
        # clear it once an officer logs a welfare check.
        dropout_flag = dropout["dropout_flag"] and is_latest and not welfare_logged

        processed.append({
            "message_id": mid,
            "timestamp": msg["timestamp"].isoformat(),
            "arrival_minute": _arrival_minute(msg),
            "channel": msg["channel"],
            "sender_id": msg["sender_id"],
            "raw_text": msg["raw_text"],
            "location": msg["location"],
            "access_status": msg["access_status"],
            "true_urgency": msg["true_urgency"],
            "llm_urgency": llm.get("urgency_score") if llm.get("ok") else None,
            "llm_reason": llm.get("flag_reason") if llm.get("ok") else llm.get("error"),
            "baseline_urgency": s["baseline_urgency"],
            "content_urgency": decision["content_urgency"],
            "content_source": decision["content_source"],
            "safety_floor": decision["safety_floor"],
            "safety_signals": decision["safety_signals"],
            "access_adjusted_priority": priority,
            "degraded": decision["degraded"],
            "second_opinion": decision["second_opinion"],
            "steps": decision["steps"],
            "headline": headline(decision, route),
            "category": route["category"],
            "team": route["team"],
            "cc_duty_officer": route["cc_duty_officer"],
            "route_reason": route["reason"],
            "draft": s["draft"]["draft"],
            "draft_note": s["draft"]["officer_note"],
            "draft_approved": draft_approved,
            "acknowledged": acknowledged,
            "ack_minute": ack_minute if acknowledged else None,
            "should_escalate": escalation["should_escalate"],
            "escalation_level": escalation["level"],
            "escalate_to": escalation["escalate_to"],
            "escalation_reason": escalation["reason"],
            "waited_minutes": escalation["waited_minutes"],
            "sla_minutes": escalation["sla_minutes"],
            "dropout_flag": dropout_flag,
            "dropout_reason": dropout["reason"],
            "welfare_logged": welfare_logged,
            "fairness_pair": msg.get("fairness_pair"),
            "fairness_style": msg.get("fairness_style"),
        })

    processed.sort(key=lambda m: (m["acknowledged"], URGENCY_ORDER.get(m["access_adjusted_priority"], 9),
                                  m["timestamp"]))

    fairness_pairs = {}
    for m in processed:
        if m["fairness_pair"]:
            fairness_pairs.setdefault(m["fairness_pair"], {})[m["fairness_style"]] = m

    # Time-to-human: minutes from arrival to acknowledgement, per priority.
    tth = {}
    for m in processed:
        if m["acknowledged"]:
            tth.setdefault(m["access_adjusted_priority"], []).append(m["ack_minute"] - m["arrival_minute"])
    time_to_human = {p: {"median": statistics.median(v), "n": len(v)} for p, v in tth.items()}

    return {
        "current_time": current_time.isoformat(),
        "minutes_elapsed": minutes_elapsed,
        "sim_max_minutes": SIM_MAX_MINUTES,
        "llm_online": llm_online,
        "llm_live_configured": llm_configured(),
        "messages": processed,
        "fairness_pairs": [{"pair_id": pid, **sides} for pid, sides in sorted(fairness_pairs.items())],
        "time_to_human": time_to_human,
        "baseline_eval": {k: v for k, v in _BASELINE_EVAL.items() if k != "oof_predictions"},
        "evaluation": _EVALUATION,
    }


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def _body():
    return request.get_json(force=True, silent=True) or {}


def _minutes(value, default=30) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _llm_flag(value) -> bool:
    return str(value).lower() not in ("off", "false", "0")


def _record(store: dict, key: str, minute: int):
    """Record when an officer action happened. Keep the EARLIEST time: if the demo
    clock was scrubbed back and the action repeated earlier, the earlier one stands."""
    store[key] = min(store.get(key, minute), minute)


def _state_from_body(body):
    return jsonify(_build_state(_minutes(body.get("minutes")), _llm_flag(body.get("llm", "on"))))


@app.get("/api/state")
def api_state():
    return jsonify(_build_state(_minutes(request.args.get("minutes")), _llm_flag(request.args.get("llm", "on"))))


@app.post("/api/acknowledge")
def api_acknowledge():
    body = _body()
    if not body.get("message_id"):
        return jsonify({"error": "message_id required"}), 400
    _record(_acks, body["message_id"], _minutes(body.get("minutes")))
    return _state_from_body(body)


@app.post("/api/approve_draft")
def api_approve_draft():
    body = _body()
    if not body.get("message_id"):
        return jsonify({"error": "message_id required"}), 400
    minute = _minutes(body.get("minutes"))
    _record(_draft_approvals, body["message_id"], minute)
    _record(_acks, body["message_id"], minute)  # approving a reply implies the officer has it
    return _state_from_body(body)


@app.post("/api/welfare_check")
def api_welfare_check():
    body = _body()
    if not body.get("sender_id"):
        return jsonify({"error": "sender_id required"}), 400
    _record(_welfare_checks, body["sender_id"], _minutes(body.get("minutes")))
    return _state_from_body(body)


@app.post("/api/reset")
def api_reset():
    _acks.clear()
    _draft_approvals.clear()
    _welfare_checks.clear()
    _submitted.clear()
    _submitted_static[True].clear()
    _submitted_static[False].clear()
    return _state_from_body(_body())


@app.post("/api/classify")
def api_classify():
    """Triage any text on the spot — the 'Try a message' tab."""
    body = _body()
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    access = body.get("access_status", "normal")
    channel = body.get("channel", "sms")

    if not _llm_flag(body.get("llm", "on")):
        llm = {"ok": False, "error": "simulated LLM outage"}
    elif llm_configured():
        llm = classify_urgency(text)
    else:
        llm = {"ok": False, "error": "no API key configured on this server"}

    baseline = classify_urgency_baseline(text)
    decision = decide_priority(text, access, llm, baseline["urgency_score"])
    route = route_message(text, decision["access_adjusted_priority"])
    draft = draft_acknowledgement("NEW", decision["access_adjusted_priority"], route["category"], route["team"], channel)
    timeout = check_escalation_timeout(
        {"urgency_score": decision["access_adjusted_priority"], "timestamp": SIMULATION_START, "acknowledged": False},
        SIMULATION_START,
    )["sla_minutes"]

    return jsonify({
        "priority": decision["access_adjusted_priority"],
        "headline": headline(decision, route),
        "steps": decision["steps"],
        "degraded": decision["degraded"],
        "llm": llm,
        "baseline": baseline,
        "safety_signals": decision["safety_signals"],
        "route": route,
        "draft": draft,
        "sla_minutes": timeout,
    })


@app.post("/api/submit")
def api_submit():
    """'Add to queue' from the 'Try a message' tab — same text just triaged
    by /api/classify, now actually saved as a live item at the current sim
    minute. Kept separate from _MESSAGES: it never touches the 152-message
    evaluation/fairness dataset, so trying things live can't move those numbers."""
    body = _body()
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    minute = _minutes(body.get("minutes"))

    _submit_counter[0] += 1
    mid = f"NEW{_submit_counter[0]:03d}"
    msg = {
        "message_id": mid,
        "timestamp": SIMULATION_START + timedelta(minutes=minute),
        "channel": body.get("channel", "sms"),
        "sender_id": f"try-a-message-{mid}",
        "raw_text": text,
        "location": "Submitted live (Try a Message)",
        "access_status": body.get("access_status", "normal"),
        "true_urgency": None,
        "fairness_pair": None,
        "fairness_style": None,
    }
    _submitted.append(msg)
    for mode in (True, False):
        _submitted_static[mode][mid] = _triage_submitted(msg, mode)

    state = _build_state(minute, _llm_flag(body.get("llm", "on")))
    state["submitted_id"] = mid
    return jsonify(state)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    # Default 5050, not 5000: on macOS, port 5000 is taken by AirPlay Receiver.
    app.run(debug=True, port=int(os.environ.get("PORT", 5050)))
