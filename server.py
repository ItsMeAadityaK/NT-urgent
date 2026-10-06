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

import hashlib
import json
import os
import random
import statistics
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "data"))

from acknowledgement import draft_acknowledgement  # noqa: E402
from baseline_model import classify_urgency_baseline, train_baseline_from_dataset  # noqa: E402
from classifier import MODEL, classify_urgency, llm_configured  # noqa: E402
from dropout_detector import check_dropout  # noqa: E402
from escalation import check_escalation_timeout  # noqa: E402
from evaluation import score  # noqa: E402
from explain import headline  # noqa: E402
from generator import (ALL_CLEAR, ALL_CLEAR_FORMAL, DEFAULT_SIZE as SHIFT_SIZE, SCENARIOS,  # noqa: E402
                       generate_shift)
import language_check  # noqa: E402
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
_welfare_checks = {}   # sender_id  -> {"minute", "logged_by", "note"} for a logged welfare check

# Who can log a welfare check. Recorded so the log shows who took responsibility.
WELFARE_ROLES = ("Officer", "Shift supervisor", "Duty manager")

# Messages added live from the "Try a Message" tab via "Add to queue".
# Kept separate from _MESSAGES (the fixed, reproducible 152-message
# dataset the evaluation numbers are measured against) so trying things
# live can never change the headline accuracy/recall figures. Each one
# is triaged once, for both LLM-online and LLM-outage, same as the
# startup dataset below.
_submitted = []
_submitted_static = {True: {}, False: {}}
_submit_counter = [0]
_LAST_MINUTE = [60]  # the sim minute the screen last asked about

# ---------------------------------------------------------------------------
# Static, clock-independent work done once at startup.
# ---------------------------------------------------------------------------
_MESSAGES = get_sample_messages()
_BASELINE_EVAL = train_baseline_from_dataset(
    [m["raw_text"] for m in _MESSAGES],
    [m["true_urgency"] for m in _MESSAGES],
)
_BASELINE_OOF = dict(zip((m["message_id"] for m in _MESSAGES), _BASELINE_EVAL["oof_predictions"]))

# Teach the readability check what ordinary messages look like (so text in a language this
# system cannot read is never ranked low). See src/language_check.py.
language_check.configure(
    [m["raw_text"] for m in _MESSAGES]
    + [t for sc in SCENARIOS for t in sc["informal"] + sc["formal"]] + ALL_CLEAR + ALL_CLEAR_FORMAL
    + ["mum dad nan pop aunty uncle brother kids little ones young children baby small days hours"]
)


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
    route = route_message(msg["raw_text"], decision["access_adjusted_priority"], unreadable=decision["language_flag"])
    draft = draft_acknowledgement(msg["message_id"], decision["access_adjusted_priority"],
                                  route["category"], route["team"], msg["channel"])
    return {"llm": llm, "decision": decision, "route": route, "draft": draft, "baseline_urgency": baseline}


def _triage_submitted(msg: dict, llm_online: bool) -> dict:
    """Same resolution rule as /api/classify: a real call if a key is configured
    and we're not simulating an outage, otherwise an honest 'unavailable'."""
    if not llm_online:
        llm = {"ok": False, "error": "simulated LLM outage"}
    else:
        llm = _llm_one(msg["raw_text"])
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


# ---------------------------------------------------------------------------
# Live shifts: a freshly generated, seeded set of messages with a HIDDEN answer
# key. The 152 hand-written messages above stay as (a) the baseline's training
# data and (b) an independent benchmark. A shift is what the queue shows by default.
# ---------------------------------------------------------------------------
LLM_CACHE_PATH = os.path.join(ROOT, "data", "llm_cache.json")
_ACTIVE = {}


def _reset_actions():
    _acks.clear()
    _draft_approvals.clear()
    _welfare_checks.clear()
    _submitted.clear()
    _submitted_static[True].clear()
    _submitted_static[False].clear()
    _submit_counter[0] = 0


def _text_key(text: str) -> str:
    # Includes the model, so switching models never replays another model's verdicts.
    return hashlib.sha1(f"{MODEL}\n{text}".encode("utf-8")).hexdigest()


def _read_llm_cache() -> dict:
    try:
        with open(LLM_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------------------
# The ONLY place this server spends API credits is _live_call(). Every call is
# counted and capped, and a verdict already saved in the cache is never paid for
# twice. Moving the clock (PLAY), acknowledging, toggling the LLM, switching tabs
# and replaying a seed you have run before all cost nothing.
# ---------------------------------------------------------------------------
LLM_CALL_LIMIT = int(os.environ.get("LLM_CALL_LIMIT", "300"))
_LLM_USAGE = {"live_calls": 0}
_llm_lock = threading.Lock()


def _live_call(text: str) -> dict:
    with _llm_lock:
        if _LLM_USAGE["live_calls"] >= LLM_CALL_LIMIT:
            return {"ok": False, "error": f"call limit reached ({LLM_CALL_LIMIT} per server run) - this protects your credits"}
        _LLM_USAGE["live_calls"] += 1
    return classify_urgency(text)


def _remember(pairs: list):
    """Save verdicts (text, result) to the cache file so they replay free next time."""
    with _llm_lock:
        cache = _read_llm_cache()
        for text, r in pairs:
            if r.get("ok"):
                cache[_text_key(text)] = {"urgency_score": r["urgency_score"], "flag_reason": r["flag_reason"],
                                          "model": r.get("model", MODEL)}
        try:
            with open(LLM_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=1)
        except OSError:
            pass


def _llm_one(text: str) -> dict:
    """One message: saved verdict if we have it, otherwise one live call (then saved)."""
    hit = _read_llm_cache().get(_text_key(text))
    if hit:
        return {"ok": True, **hit, "cached": True}
    if not llm_configured():
        return {"ok": False, "error": "no API key configured on this server"}
    r = _live_call(text)
    _remember([(text, r)])
    return r


def _llm_for_messages(messages: list, allow_live: bool = True) -> dict:
    """LLM verdict per generated message. A saved verdict is reused (so a shift can be
    replayed offline and for free); otherwise, if a key is configured AND live calls are
    allowed, the messages are classified for real; otherwise the LLM is honestly
    'unavailable'. The first call is a probe: if it fails (no network, bad key) the rest
    are not attempted, so a dead connection can never stall or drain anything."""
    cache = _read_llm_cache()
    out, todo = {}, []
    for m in messages:
        hit = cache.get(_text_key(m["raw_text"]))
        if hit:
            out[m["message_id"]] = {"ok": True, **hit, "cached": True}
        else:
            todo.append(m)

    if todo and allow_live and llm_configured():
        probe = _live_call(todo[0]["raw_text"])
        results = [probe]
        if probe.get("ok"):
            with ThreadPoolExecutor(max_workers=8) as pool:
                results += list(pool.map(lambda m: _live_call(m["raw_text"]), todo[1:]))
        else:
            results += [probe] * (len(todo) - 1)
        for m, r in zip(todo, results):
            out[m["message_id"]] = r
        _remember([(m["raw_text"], r) for m, r in zip(todo, results)])

    for m in todo:
        why = ("no API key configured on this server" if not llm_configured()
               else "not fetched yet (press NEW SHIFT to have Claude judge this shift)")
        out.setdefault(m["message_id"], {"ok": False, "error": why})
    return out


def _per_class_recall(preds: list, truths: list) -> dict:
    out = {}
    for level in ("low", "medium", "high", "critical"):
        idx = [i for i, t in enumerate(truths) if t == level]
        if idx:
            out[level] = sum(preds[i] == level for i in idx) / len(idx)
    return out


def _evaluate_shift(messages: list, static: dict, llm: dict) -> dict:
    ids = [m["message_id"] for m in messages]
    truths = [m["true_urgency"] for m in messages]
    online, offline = static[True], static[False]
    n_ok = sum(1 for i in ids if llm[i].get("ok"))
    llm_all = n_ok == len(ids)
    base_preds = [online[i]["baseline_urgency"] for i in ids]

    if llm_all:
        cached = sum(1 for i in ids if llm[i].get("cached"))
        source = (f"Real Claude verdicts on this shift ({len(ids) - cached} fetched live, {cached} replayed from cache)")
    elif n_ok:
        source = f"Real Claude verdicts for only {n_ok} of {len(ids)} messages (the rest failed), so the LLM rows are omitted"
    else:
        source = "No LLM verdicts for this shift (no API key, or the calls failed). Only the baseline and safety net are scored."

    rows = []
    if llm_all:
        rows.append(score("LLM alone", [online[i]["decision"]["content_urgency"] for i in ids], truths, ids))
    rows.append(score("Baseline alone (trained on the 152 hand-written messages, never saw this shift)",
                      base_preds, truths, ids))
    rows.append(score("Safety-net rules alone", [check_safety_net(m["raw_text"])["floor"] or "low" for m in messages],
                      truths, ids, note="Rules only ever raise; unmatched messages count as low here."))
    if llm_all:
        rows.append(score("Full pipeline — LLM online", [online[i]["decision"]["access_adjusted_priority"] for i in ids],
                          truths, ids, include_accuracy=False))
    rows.append(score("Full pipeline — LLM OUTAGE (baseline + safety net + access)",
                      [offline[i]["decision"]["access_adjusted_priority"] for i in ids], truths, ids,
                      include_accuracy=False, note="What still reaches a human if the LLM is unavailable."))
    return {
        "title": "This shift",
        "n": len(ids),
        "caveat": ("These messages were written by us as templates, so the wording overlaps with what the baseline "
                   "trained on. Treat these scores as optimistic; the hand-written benchmark below is the independent check."),
        "llm_source": source,
        "llm_is_real": llm_all,
        "llm_ok": n_ok,
        "rows": rows,
        "baseline_per_class_recall": _per_class_recall(base_preds, truths),
    }


def _activate(mode: str = "shift", seed=None, allow_live: bool = True):
    """Make `mode` the live queue: a generated shift (default) or the 152 benchmark.
    Clears all officer actions, since message ids differ between shifts."""
    _reset_actions()
    if mode == "benchmark":
        _ACTIVE.update(mode="benchmark", seed=None, messages=_MESSAGES, static=_STATIC,
                       evaluation={**_EVALUATION, "title": "Benchmark", "n": len(_MESSAGES)}, llm={})
        return
    try:
        seed = int(seed)
    except (TypeError, ValueError):
        seed = random.SystemRandom().randint(1000, 9999)
    messages = generate_shift(seed, n=SHIFT_SIZE)
    llm = _llm_for_messages(messages, allow_live=allow_live)
    outage = {"ok": False, "error": "simulated LLM outage"}
    static = {
        True: {m["message_id"]: _finish_triage(m, llm[m["message_id"]]) for m in messages},
        False: {m["message_id"]: _finish_triage(m, outage) for m in messages},
    }
    _ACTIVE.update(mode="shift", seed=seed, messages=messages, static=static,
                   evaluation=_evaluate_shift(messages, static, llm), llm=llm)


# Starting (or auto-reloading) the server must never spend credits, so it only ever replays saved
# verdicts. It opens on the demo seed; NEW SHIFT is what fetches a brand-new shift from Claude.
DEMO_SEED = 2026
_activate("shift", os.environ.get("SHIFT_SEED") or DEMO_SEED, allow_live=False)


def _welfare_log(arrived: list, static: dict, minutes_elapsed: int) -> list:
    """Welfare checks logged so far on the sim clock, newest first. Each entry says
    which message triggered it, who logged it, and whether the sender has made
    contact again since (the best evidence they're OK)."""
    by_sender = {}
    for m in sorted(arrived, key=lambda m: m["timestamp"]):
        by_sender.setdefault(m["sender_id"], []).append(m)

    log = []
    for sender_id, check in _welfare_checks.items():
        if check["minute"] > minutes_elapsed or sender_id not in by_sender:
            continue
        msgs = by_sender[sender_id]
        before = [m for m in msgs if _arrival_minute(m) <= check["minute"]] or msgs[:1]
        after = [m for m in msgs if _arrival_minute(m) > check["minute"]]
        trigger = before[-1]
        log.append({
            "sender_id": sender_id,
            "minute": check["minute"],
            "time": (SIMULATION_START + timedelta(minutes=check["minute"])).isoformat(),
            "logged_by": check["logged_by"],
            "note": check["note"],
            "message_id": trigger["message_id"],
            "raw_text": trigger["raw_text"],
            "location": trigger["location"],
            "access_status": trigger["access_status"],
            "priority": static[trigger["message_id"]]["decision"]["access_adjusted_priority"],
            "silent_minutes": check["minute"] - _arrival_minute(trigger),
            "followup": ({"message_id": after[0]["message_id"], "time": after[0]["timestamp"].isoformat(),
                          "raw_text": after[0]["raw_text"]} if after else None),
        })
    return sorted(log, key=lambda e: -e["minute"])


def _arrival_minute(msg) -> int:
    return int((msg["timestamp"] - SIMULATION_START).total_seconds() // 60)


# ---------------------------------------------------------------------------
# Clock-dependent state
# ---------------------------------------------------------------------------
def _build_state(minutes_elapsed: int, llm_online: bool):
    minutes_elapsed = max(0, min(SIM_MAX_MINUTES, minutes_elapsed))
    _LAST_MINUTE[0] = minutes_elapsed
    current_time = SIMULATION_START + timedelta(minutes=minutes_elapsed)
    all_messages = _ACTIVE["messages"] + _submitted
    static = {**_ACTIVE["static"][llm_online], **_submitted_static[llm_online]}
    arrived = [m for m in all_messages if m["message_id"] in static and m["timestamp"] <= current_time]

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
        welfare_minute = (_welfare_checks.get(msg["sender_id"]) or {}).get("minute")
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
        "welfare_log": _welfare_log(arrived, static, minutes_elapsed),
        "current_time": current_time.isoformat(),
        "minutes_elapsed": minutes_elapsed,
        "sim_max_minutes": SIM_MAX_MINUTES,
        "llm_online": llm_online,
        "llm_live_configured": llm_configured(),
        "llm_usage": {"live_calls": _LLM_USAGE["live_calls"], "limit": LLM_CALL_LIMIT},
        "messages": processed,
        "fairness_pairs": [{"pair_id": pid, **sides} for pid, sides in sorted(fairness_pairs.items())],
        "time_to_human": time_to_human,
        "baseline_eval": {k: v for k, v in _BASELINE_EVAL.items() if k != "oof_predictions"},
        "evaluation": _ACTIVE["evaluation"],
        "benchmark_evaluation": {**_EVALUATION, "title": "Benchmark", "n": len(_MESSAGES)}
                                if _ACTIVE["mode"] != "benchmark" else None,
        "shift": {
            "mode": _ACTIVE["mode"],
            "seed": _ACTIVE["seed"],
            "n": len(_ACTIVE["messages"]),
            "llm_ok": _ACTIVE["evaluation"].get("llm_ok"),
        },
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
    minute = _minutes(body.get("minutes"))
    logged_by = body.get("logged_by") if body.get("logged_by") in WELFARE_ROLES else "Officer"
    note = str(body.get("note") or "").strip()[:300]
    existing = _welfare_checks.get(body["sender_id"])
    # Keep the earliest check (same rule as acknowledgements: scrubbing the demo
    # clock back and logging again earlier replaces the later record).
    if existing is None or minute < existing["minute"]:
        _welfare_checks[body["sender_id"]] = {"minute": minute, "logged_by": logged_by, "note": note}
    return _state_from_body(body)


@app.post("/api/reset")
def api_reset():
    _reset_actions()
    return _state_from_body(_body())


@app.post("/api/new_shift")
def api_new_shift():
    """Generate a brand-new shift (random seed, or replay one by passing `seed`),
    or switch to the fixed 152-message benchmark with mode="benchmark"."""
    body = _body()
    _activate("benchmark" if body.get("mode") == "benchmark" else "shift", body.get("seed"))
    return _state_from_body(body)


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
    else:
        llm = _llm_one(text)

    baseline = classify_urgency_baseline(text)
    decision = decide_priority(text, access, llm, baseline["urgency_score"])
    route = route_message(text, decision["access_adjusted_priority"], unreadable=decision["language_flag"])
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


def _enqueue(text: str, channel: str, access: str, minute: int, sender_id=None,
             location: str = "Submitted live (Try a Message)") -> str:
    """Put one message into the live queue at `minute` and triage it (both LLM views)."""
    _submit_counter[0] += 1
    mid = f"NEW{_submit_counter[0]:03d}"
    msg = {
        "message_id": mid,
        "timestamp": SIMULATION_START + timedelta(minutes=minute),
        "channel": channel,
        "sender_id": sender_id or f"try-a-message-{mid}",
        "raw_text": text,
        "location": location,
        "access_status": access,
        "true_urgency": None,
        "fairness_pair": None,
        "fairness_style": None,
    }
    results = {mode: _triage_submitted(msg, mode) for mode in (True, False)}  # slow part first (may call Claude)
    for mode in (True, False):
        _submitted_static[mode][mid] = results[mode]
    _submitted.append(msg)  # only now can a request reading the queue see it, triage already in place
    return mid


@app.post("/api/submit")
def api_submit():
    """'Add to queue' from the 'Try a message' tab — same text just triaged
    by /api/classify, now actually saved as a live item at the current sim
    minute. Kept separate from the evaluation dataset: it never touches the
    scored messages, so trying things live can't move those numbers."""
    body = _body()
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    minute = _minutes(body.get("minutes"))
    mid = _enqueue(text, body.get("channel", "sms"), body.get("access_status", "normal"), minute)

    state = _build_state(minute, _llm_flag(body.get("llm", "on")))
    state["submitted_id"] = mid
    return jsonify(state)


INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "")  # if set, callers must send it as X-Ingest-Token


@app.post("/api/ingest")
def api_ingest():
    """Where a real channel plugs in. An SMS gateway (e.g. a Twilio webhook, which posts `Body`
    and `From`), an email forwarder or a web form POSTs a message here; it is triaged by the same
    pipeline as everything else and appears in the queue within a few seconds (the page polls).

    JSON or form fields: text (or Body/body), channel (sms/email/webform/phone), from (or From),
    location, access_status. Set INGEST_TOKEN to require a shared secret header."""
    if INGEST_TOKEN and request.headers.get("X-Ingest-Token") != INGEST_TOKEN:
        return jsonify({"error": "missing or wrong X-Ingest-Token"}), 401
    data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
    text = str(data.get("text") or data.get("Body") or data.get("body") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    channel = str(data.get("channel") or ("sms" if "Body" in data else "webform")).lower()
    if channel not in ("sms", "email", "webform", "phone"):
        channel = "webform"
    access = data.get("access_status") if data.get("access_status") in ("normal", "limited", "cut-off") else "normal"
    sender = str(data.get("from") or data.get("From") or "").strip()[:60] or None
    location = str(data.get("location") or "").strip()[:60] or "Inbound (location unknown)"

    minute = _LAST_MINUTE[0]
    mid = _enqueue(text, channel, access, minute, sender_id=sender, location=location)
    s = _submitted_static[True][mid]
    return jsonify({
        "message_id": mid,
        "priority": s["decision"]["access_adjusted_priority"],
        "team": s["route"]["team"],
        "language_not_recognised": s["decision"]["language_flag"],
        "queued_at_sim_minute": minute,
    }), 201


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    # Default 5050, not 5000: on macOS, port 5000 is taken by AirPlay Receiver.
    # The auto-reloader ignores installed libraries: a pip install in another window must never
    # restart a running demo (a restart wipes acknowledgements and drops connections).
    app.run(debug=True, port=int(os.environ.get("PORT", 5050)),
            exclude_patterns=["*/site-packages/*", r"*\site-packages\*", "*/.git/*"])
