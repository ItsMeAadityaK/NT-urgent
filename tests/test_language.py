"""
Tests for text the system cannot read (another language, or too garbled), and for the
inbound endpoint where real channels plug in.
"""

import language_check
from generator import generate_shift
from language_standins import PAIRS, standin
from messages import get_sample_messages
from triage import URGENCY_LEVELS, decide_priority

LLM_DOWN = {"ok": False, "error": "test outage"}
FRESH_ENGLISH = [
    "the creek is rising and i think we should move the horses and the old people to the church",
    "pregnant and bleeding cant reach the clinic", "hello is anybody there my phone is nearly dead",
    "ambulance please quickly", "my neighbour has a snake in her kitchen and she is scared",
    "water in the house", "please help my husband has chest pain", "the generator ran out of diesel last night",
    "we need a lift to the clinic on thursday for my mums appointment", "kids stuck at school road flooded",
    "can someone check on the old fella down the road he has not been seen", "no power and the baby is hot",
]


def test_ordinary_english_is_never_flagged_even_with_typos():
    texts = [m["raw_text"] for m in get_sample_messages()] + FRESH_ENGLISH
    texts += [m["raw_text"] for seed in range(1, 40) for m in generate_shift(seed)]  # typo/SMS/ALL-CAPS noise
    flagged = [t for t in texts if not language_check.check_readable(t)["readable"]]
    assert not flagged, flagged[:5]


def test_every_invented_language_message_is_flagged():
    for english, _ in PAIRS:
        assert not language_check.check_readable(standin(english))["readable"], english


def test_unreadable_text_is_never_ranked_below_high():
    for english, truth in PAIRS:
        d = decide_priority(standin(english), "normal", LLM_DOWN, "low")  # baseline says low: it can't read it either
        assert URGENCY_LEVELS.index(d["access_adjusted_priority"]) >= URGENCY_LEVELS.index("high"), english
        assert d["language_flag"] is True
        assert any("Language not recognised" in step for step in d["steps"])


def test_the_language_rule_only_raises_never_lowers():
    d = decide_priority(standin("my aunty collapsed and wont wake up"), "cut-off", {"ok": True, "urgency_score": "critical",
                        "flag_reason": "test"}, "critical")
    assert d["access_adjusted_priority"] == "critical"          # already above the floor: untouched


def test_check_is_off_until_configured_and_can_be_disabled():
    checker = language_check._checker
    try:
        language_check.disable()
        assert language_check.check_readable(standin("my aunty collapsed"))["readable"] is True
    finally:
        language_check._checker = checker


def test_unreadable_messages_go_to_the_interpreter_desk_with_a_safe_draft():
    import server

    state = server.app.test_client().post("/api/classify", json={"text": standin(PAIRS[0][0]), "llm": "off"}).get_json()
    assert state["route"]["team"] == "Interpreter & community liaison"
    assert state["draft"]["requires_approval"] is True
    assert "language was not recognised" in state["route"]["reason"] or "not recognised" in state["headline"]
    assert "ambulance" not in state["draft"]["draft"].lower()    # the draft never pretends to understand it


# ---------- the inbound endpoint ----------

def test_ingest_puts_an_outside_message_into_the_queue_and_triages_it():
    import server

    client = server.app.test_client()
    client.post("/api/new_shift", json={"mode": "benchmark", "minutes": 120})
    before = len(client.get("/api/state?minutes=120").get_json()["messages"])
    r = client.post("/api/ingest", json={"text": "my aunty collapsed and wont wake up, no ambulance can get in",
                                         "channel": "sms", "from": "+61400000000", "location": "Wadeye",
                                         "access_status": "cut-off"})
    assert r.status_code == 201 and r.get_json()["priority"] == "critical"
    after = client.get("/api/state?minutes=120").get_json()["messages"]
    assert len(after) == before + 1
    mine = next(m for m in after if m["message_id"] == r.get_json()["message_id"])
    assert mine["channel"] == "sms" and mine["location"] == "Wadeye" and mine["true_urgency"] is None


def test_ingest_accepts_a_twilio_style_form_post_and_rejects_empty_text():
    import server

    client = server.app.test_client()
    ok = client.post("/api/ingest", data={"Body": "roof is gone nowhere to stay tonight", "From": "+61411111111"})
    assert ok.status_code == 201
    assert client.post("/api/ingest", json={"text": "   "}).status_code == 400


def test_ingest_requires_the_shared_secret_when_one_is_set(monkeypatch):
    import server

    monkeypatch.setattr(server, "INGEST_TOKEN", "s3cret")
    client = server.app.test_client()
    assert client.post("/api/ingest", json={"text": "hello"}).status_code == 401
    assert client.post("/api/ingest", json={"text": "hello"}, headers={"X-Ingest-Token": "s3cret"}).status_code == 201


def test_a_message_without_its_triage_yet_never_crashes_the_queue():
    """Regression: the page polls while a message is still being triaged (a slow Claude call).
    A half-added message used to crash /api/state with a KeyError."""
    import server
    from datetime import timedelta

    server._submitted.append({"message_id": "NEW999", "timestamp": server.SIMULATION_START + timedelta(minutes=5),
                              "channel": "sms", "sender_id": "x", "raw_text": "half added", "location": "?",
                              "access_status": "normal", "true_urgency": None, "fairness_pair": None,
                              "fairness_style": None})
    state = server._build_state(120, True)          # must not raise
    assert "NEW999" not in {m["message_id"] for m in state["messages"]}
