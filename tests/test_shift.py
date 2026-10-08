"""
Tests for generated shifts: replayable, varied, honest about hidden labels,
guaranteed to contain the cases worth demonstrating, and not copied from the
data the baseline trained on.
"""

import difflib
import re
from collections import Counter

import pytest

from generator import DEFAULT_SIZE, SCENARIOS, generate_shift
from messages import get_sample_messages


# ---------- Replayable but varied ----------

def test_same_seed_replays_identically():
    assert generate_shift(42) == generate_shift(42)


def test_different_seeds_give_different_shifts():
    texts = {tuple(m["raw_text"] for m in generate_shift(s)) for s in range(30)}
    assert len(texts) == 30


def test_shifts_are_not_the_fixed_benchmark():
    benchmark = {m["raw_text"].lower() for m in get_sample_messages()}
    shift = {m["raw_text"].lower() for m in generate_shift(7)}
    assert len(shift & benchmark) <= 2


def test_few_exact_duplicates_within_a_shift():
    dupes = 0
    for seed in range(40):
        texts = [m["raw_text"].lower() for m in generate_shift(seed)]
        dupes += len(texts) - len(set(texts))
    assert dupes / 40 < 0.5  # on average fewer than one repeated message per shift


# ---------- Shape and mix ----------

def test_size_and_urgency_mix():
    shift = generate_shift(3)
    assert len(shift) == DEFAULT_SIZE == 55
    mix = Counter(m["true_urgency"] for m in shift)
    assert mix["low"] > mix["medium"] > mix["high"] > mix["critical"] >= 5  # the haystack


def test_text_is_clean_of_template_artifacts():
    for seed in range(40):
        for m in generate_shift(seed):
            assert m["raw_text"].strip()
            assert "{" not in m["raw_text"] and "}" not in m["raw_text"]


def test_ids_are_unique_and_do_not_collide_with_the_benchmark():
    shift = generate_shift(5)
    assert len({m["message_id"] for m in shift}) == len(shift)
    benchmark_ids = {m["message_id"] for m in get_sample_messages()}
    assert not benchmark_ids & {m["message_id"] for m in shift}


# ---------- Guaranteed demonstration cases ----------

@pytest.mark.parametrize("seed", range(25))
def test_every_shift_contains_the_demo_cases(seed):
    shift = generate_shift(seed)
    scenarios = {m["scenario"] for m in shift}
    for key in ("flood_no_water_old", "child_alone", "medical_collapse", "insulin_fridge", "thanks_feedback"):
        assert key in scenarios, key

    # three like-for-like formal/informal pairs
    pairs = {}
    for m in shift:
        if m["fairness_pair"]:
            pairs.setdefault(m["fairness_pair"], []).append(m)
    assert len(pairs) == 3
    for sides in pairs.values():
        a, b = sides
        assert {a["fairness_style"], b["fairness_style"]} == {"informal", "formal"}
        assert (a["true_urgency"], a["access_status"], a["location"]) == (b["true_urgency"], b["access_status"], b["location"])

    # senders who go silent after a critical message early enough for the 2h dropout window
    by_sender = Counter(m["sender_id"] for m in shift)
    silent = [m for m in shift if m["true_urgency"] == "critical" and by_sender[m["sender_id"]] == 1
              and (m["timestamp"] - shift[0]["timestamp"]).total_seconds() / 60 <= 330]
    assert len(silent) >= 2

    # a sender who follows up (dropout must NOT fire for them)
    assert any(count > 1 for count in by_sender.values())

    # access weighting gets exercised on a non-critical message
    assert any(m["access_status"] != "normal" and m["true_urgency"] in ("low", "medium") for m in shift)


def test_cut_off_only_appears_with_serious_weather_scenarios():
    """Cut-off bumps priority two levels, so it must not be handed to routine mail."""
    weather = {s["key"] for s in SCENARIOS if s["weather"]}
    for seed in range(40):
        for m in generate_shift(seed):
            if m["access_status"] == "cut-off":
                assert m["scenario"] in weather, (m["scenario"], m["raw_text"])
                assert m["true_urgency"] in ("high", "critical"), (m["scenario"], m["raw_text"])


# ---------- Not copied from training data ----------

def _norm(text):
    return re.sub(r"[^a-z0-9 ]", "", text.lower())


def test_templates_are_not_copies_of_the_training_messages():
    """The baseline trains on the 152 hand-written messages, so generated wording
    must not echo them closely or the 'unseen' scores would be quietly rigged."""
    training = [_norm(m["raw_text"]) for m in get_sample_messages()]
    worst = 0.0
    for sc in SCENARIOS:
        for style in ("informal", "formal"):
            for template in sc[style]:
                t = _norm(re.sub(r"\{[a-z_]+\}", "x", template))
                worst = max(worst, max(difflib.SequenceMatcher(None, t, p).ratio() for p in training))
    assert worst < 0.80, f"a template is {worst:.0%} similar to a training message"


# ---------- Community phrases are used when supplied, never invented ----------

def test_community_phrases_are_mixed_in_when_supplied():
    phrases = [{"text": "PLACEHOLDER community phrase", "true_urgency": "low", "language": "test-language"}]
    shift = generate_shift(9, community=phrases)
    tagged = [m for m in shift if m["language"] == "test-language"]
    assert len(tagged) == 1 and tagged[0]["raw_text"] == "PLACEHOLDER community phrase"


def test_no_community_phrases_means_no_language_tags():
    assert all(m["language"] is None for m in generate_shift(9, community=[]))


# ---------- Server: shift mode ----------

def test_server_shift_mode_end_to_end(tmp_path):
    import server

    server._activate("shift", 11)
    state = server._build_state(480, True)

    assert state["shift"] == {"mode": "shift", "seed": 11, "n": 55, "llm_ok": 0}
    assert len(state["messages"]) == 55
    assert all(m["message_id"].startswith("L") for m in state["messages"])
    assert len(state["fairness_pairs"]) == 3

    # No key in tests: honest "LLM unavailable", never a made-up verdict.
    assert all(m["llm_urgency"] is None and m["degraded"] for m in state["messages"])
    assert "No AI verdicts" in state["evaluation"]["llm_source"]

    # The escalation clock still follows the final priority.
    for m in state["messages"]:
        if m["access_adjusted_priority"] == "critical":
            assert m["sla_minutes"] == 15

    # Scored against a hidden key, with the independent benchmark alongside.
    names = [r["name"] for r in state["evaluation"]["rows"]]
    assert any("OUTAGE" in n for n in names) and state["evaluation"]["n"] == 55
    assert state["benchmark_evaluation"]["n"] == 152


def test_without_llm_most_urgent_messages_still_reach_the_fast_lane():
    import server

    recalls = []
    for seed in range(1, 21):
        server._activate("shift", seed)
        recalls.append(server._ACTIVE["evaluation"]["rows"][-1]["urgent_recall"])  # LLM-outage row
    assert sum(recalls) / len(recalls) >= 0.90


def test_new_shift_endpoint_replays_a_seed_and_clears_actions():
    import server

    client = server.app.test_client()
    first = client.post("/api/new_shift", json={"seed": 77, "minutes": 480}).get_json()
    again = client.post("/api/new_shift", json={"seed": 77, "minutes": 480}).get_json()
    assert [m["raw_text"] for m in first["messages"]] == [m["raw_text"] for m in again["messages"]]

    mid = next(m["message_id"] for m in first["messages"] if m["access_adjusted_priority"] == "critical")
    acked = client.post("/api/acknowledge", json={"message_id": mid, "minutes": 480}).get_json()
    assert next(m for m in acked["messages"] if m["message_id"] == mid)["acknowledged"]

    fresh = client.post("/api/new_shift", json={"seed": 78, "minutes": 480}).get_json()
    assert fresh["shift"]["seed"] == 78 and not any(m["acknowledged"] for m in fresh["messages"])

    random_one = client.post("/api/new_shift", json={"minutes": 480}).get_json()
    assert random_one["shift"]["mode"] == "shift" and random_one["shift"]["seed"] is not None

    bench = client.post("/api/new_shift", json={"mode": "benchmark", "minutes": 480}).get_json()
    assert bench["shift"]["mode"] == "benchmark" and bench["messages"][0]["message_id"].startswith("M")
    assert bench["benchmark_evaluation"] is None


def test_hidden_answer_key_never_changes_the_priority():
    """The queue's priority must come from the classifiers, not the hidden label."""
    import server

    server._activate("shift", 5)
    state = server._build_state(480, True)
    flipped = {"low": "critical", "medium": "critical", "high": "low", "critical": "low"}
    for m in server._ACTIVE["messages"]:
        m["true_urgency"] = flipped[m["true_urgency"]]
    assert [m["access_adjusted_priority"] for m in server._build_state(480, True)["messages"]] == \
           [m["access_adjusted_priority"] for m in state["messages"]]


# ---------- Credits: only the buttons you press may spend them ----------

@pytest.fixture
def paid_llm(monkeypatch):
    """Pretend a key is set, and count every call that would have cost money."""
    import server

    calls = []

    def fake(text):
        calls.append(text)
        return {"ok": True, "urgency_score": "high", "flag_reason": "test", "model": "fake"}

    monkeypatch.setattr(server, "classify_urgency", fake)
    monkeypatch.setattr(server, "llm_configured", lambda: True)
    server._LLM_USAGE["live_calls"] = 0
    yield calls
    server._LLM_USAGE["live_calls"] = 0


def test_playing_the_clock_and_using_the_queue_never_spends_credits(paid_llm):
    import server

    server._activate("shift", 3, allow_live=False)
    client = server.app.test_client()
    for minutes in range(0, 481, 15):                      # PLAY / scrubbing
        client.get(f"/api/state?minutes={minutes}&llm=on")
        client.get(f"/api/state?minutes={minutes}&llm=off")  # LLM toggle
    mid = server._ACTIVE["messages"][0]["message_id"]
    client.post("/api/acknowledge", json={"message_id": mid, "minutes": 100})
    client.post("/api/approve_draft", json={"message_id": mid, "minutes": 100})
    client.post("/api/reset", json={"minutes": 100})
    assert paid_llm == []


def test_starting_or_reloading_the_server_never_spends_credits(paid_llm):
    import server

    server._activate("shift", 99, allow_live=False)        # exactly what startup does
    assert paid_llm == []
    assert "not fetched yet" in server._ACTIVE["llm"][server._ACTIVE["messages"][0]["message_id"]]["error"]


def test_new_shift_costs_one_call_per_message_and_a_replay_is_free(paid_llm):
    import server

    client = server.app.test_client()
    client.post("/api/new_shift", json={"seed": 123, "minutes": 60})
    assert len(paid_llm) == 55                              # one per message, never doubled for the outage view
    client.post("/api/new_shift", json={"seed": 123, "minutes": 60})
    assert len(paid_llm) == 55                              # replaying a seed you have run is free
    assert server._LLM_USAGE["live_calls"] == 55


def test_try_a_message_pays_once_per_text(paid_llm):
    import server

    client = server.app.test_client()
    body = {"text": "my aunty collapsed and wont wake up", "minutes": 60}
    client.post("/api/classify", json=body)
    client.post("/api/submit", json=body)                   # "ADD TO QUEUE" of the same text
    assert len(paid_llm) == 1


def test_call_limit_stops_spending(paid_llm, monkeypatch):
    import server

    monkeypatch.setattr(server, "LLM_CALL_LIMIT", 10)
    server._activate("shift", 321)
    assert len(paid_llm) == 10
    errors = [v["error"] for v in server._ACTIVE["llm"].values() if not v.get("ok")]
    assert errors and all("call limit reached" in e for e in errors)
