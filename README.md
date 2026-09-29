# Correspondence Triage — Dispatch Console

**CDU IT Code Fair 2026 · AI Challenge · Brief #5: Getting urgent messages to a human, fast**

> **How might we** make sure a vulnerable person's urgent message never gets buried in a
> high-volume government inbox and reaches a human quickly?

A working triage console for an NT government correspondence/complaints unit during a
wet-season event. It classifies every incoming item, detects urgency, routes it to the right
team, drafts an acknowledgement and explains each decision in plain English. Anything serious
goes to a named human and keeps escalating until someone picks it up.

**Trust twist, built in:** the system never replies to the public. Every draft waits for an
officer's approval, and every escalation goes to a person, never to an automated response.

---

## The brief, point by point

| Brief asks for | What we built | Where |
|---|---|---|
| Classification + urgency detection | Claude LLM classifier (structured JSON output) + local TF‑IDF baseline + deterministic safety tripwires, combined in a fixed order where **nothing can lower a priority** | `src/classifier.py`, `baseline_model.py`, `safety_net.py`, `triage.py` |
| Routes and prioritises | Access-aware priority (a sender who is cut off is bumped up) and rule-based routing to one of 10 teams. Critical items also copy in the Duty Officer | `access_scoring.py`, `routing.py` |
| Drafts acknowledgements | Template drafts per priority and channel, **never auto-sent**. Personal-safety drafts use safety-aware wording that doesn't repeat what was reported | `acknowledgement.py` |
| Explanation for each call | One-line "Why:" on every item, plus the full step-by-step reasoning, routing rule, both models' outputs and matched tripwires | `explain.py`, `triage.py` |
| Escalation path is the design goal | Dead-man's switch: critical 15 min → shift supervisor, then duty manager at 2× the limit. A "Needs a human now" panel is pinned to the top, and silent senders are flagged for a welfare check | `escalation.py`, `dropout_detector.py` |
| Escalate, never respond | No code path sends anything (a test checks this). Drafts need an officer's click | `tests/test_safety.py` |

---

## Design principles (the "why" behind the build)

1. **Asymmetric errors.** Over-escalating costs an officer a few minutes. Under-escalating can
   cost a person help. So every step in the pipeline can only *raise* a priority, and the LLM
   is told to pick the more urgent level when unsure.
2. **Fail loud, fail up.** If the LLM errors, times out, declines or returns junk, the item is
   marked *NOT LLM-CHECKED* and triaged by the baseline plus safety net. It never silently
   defaults to "medium". (The earlier version did exactly that on a parse error.)
3. **Defence in depth.** Three independent signals:
   - the **LLM** understands context and informal writing;
   - the **baseline model** runs offline;
   - the **safety tripwires** can be audited line by line and can't be prompt-injected.

   If any one of them catches a message, it can't be buried.
4. **Works when the network doesn't.** Wet-season outages are the NT's reality. Toggle
   **LLM: OUTAGE** in the console: every critical message still reaches a human (measured below).
5. **Human owns the decision.** The AI sorts, explains and drafts. A person acknowledges,
   approves and responds.

---

## Pipeline

```
 message ─┬─► Claude LLM ────────────┐  content urgency (LLM, or baseline if LLM is down)
          ├─► TF-IDF baseline ───────┤
          └─► safety tripwires ──────┼─► raise to safety floor ─► raise for access (cut-off/limited)
 access status ──────────────────────┘                                   │
                                                                          ▼
                       routing (team + Duty Officer cc) ─► draft acknowledgement (awaits officer)
                                                                          │
 sim clock + officer acks ─► escalation chain: supervisor → duty manager  │
 sender history ───────────► comms-dropout: "sender went silent" → welfare check
```

---

## Results: measured, not assumed

All 152 messages, scored against the ground-truth `true_urgency` label. **Urgent recall** means:
of the messages that really are high/critical, how many landed in the fast lane? That's the
brief's failure mode, so it's the headline number.

| Approach | Exact accuracy | Urgent recall | Critical recall | Routine items pushed to fast lane |
|---|---|---|---|---|
| Baseline alone (5-fold cross-validated) | 70% | 85% | 52% | 9 / 97 |
| Safety tripwires alone | — | 65% | 70% | 0 / 97 |
| **Full pipeline, LLM OUTAGE** (baseline + tripwires + access) | — | **98%** | **100%** | 12 / 97 |
| Full pipeline, LLM online | — | 100%* | 100%* | 5 / 97 |

\* See the honesty notes below. The live console's **Evaluation** tab regenerates this table.

**What it shows:** the baseline alone misses half of the critical messages. Layering the
tripwires and access weighting on top closes that gap to zero missed critical items, even with
the LLM completely offline. The cost is 12 routine items (of 97) getting a faster look than they
needed.

**Fairness audit:** five formal/informal pairs describing identical situations. The baseline is
inconsistent on 2 of 5. On FP1 it actually rates the *formal* version lower (medium vs critical).
The **final priority is consistent on 5 of 5**, because the tripwires and access weighting stop
writing style from changing the outcome.

### Honesty notes (read before quoting numbers)

- **LLM row.** Until `scripts/run_llm_batch.py` is run with an API key, the LLM values are
  hand-authored stand-ins that match the answer key by construction. The console says so
  prominently. Run the script (a few cents) to replace them with real Claude outputs, and the
  numbers become a genuine measurement.
- **Tripwires** were written by the team with this dataset in view, so their recall here is
  optimistic. The baseline numbers are clean: every prediction shown is out-of-fold, from a model
  that never saw that message.
- **Synthetic data.** The 152 messages are synthetic (see `data/messages.py` for the design
  rationale). Real deployment would need evaluation on real, consented correspondence.

---

## How to run it

```bash
pip install -r requirements.txt
python3 server.py
```

Open **http://127.0.0.1:5050**. (Not 5000: on macOS that port belongs to AirPlay Receiver.
Override with `PORT=8000 python3 server.py`.)

Optional, to use real Claude outputs:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/run_llm_batch.py      # classifies all 152 once → data/llm_results.json
python3 server.py                     # now uses the cached real outputs; "Try a message" calls Claude live
```

Run the tests:

```bash
python3 -m pytest -q
```

35 tests cover the safety guarantees: nothing lowers a priority, prompt injection can't bury a
flagged message, every critical message survives an LLM outage, escalation climbs, drafts always
need approval, and no module imports a message-sending library.

---

## Demo script (≈5 minutes)

1. **The problem (30s).** Wet-season shift, 152 messages, most routine. 23 of them are life or
   death. Point at the "Needs a human now" panel: it's empty at 06:30.
2. **The needle (60s).** Press **PLAY**. As the clock runs, criticals arrive and the 15-minute
   clock starts. Unacknowledged items climb to *Shift supervisor* and then *Duty manager*. Open
   M019 → **full reasoning + draft reply**. Show the plain-English steps and the **safety-aware
   draft** that doesn't repeat the disclosure, in case the person causing harm reads the phone.
3. **Acknowledge (30s).** Click ACKNOWLEDGE. The item leaves the escalation panel and the
   **time-to-human** tile updates. Scrub the clock backwards: the acknowledgement is time-aware.
4. **Silence is a signal (30s).** At about +2h, senders who reported a critical situation and
   then went quiet show **SENDER SILENT**. Log a welfare check.
5. **Pull the plug (60s).** Click **LLM: ONLINE** to simulate an outage. Everything is re-triaged
   in degraded mode and flagged *NOT LLM-CHECKED*. Open **Evaluation**: 100% of critical messages
   still reach the fast lane.
6. **Try to break it (60s).** **Try a Message** → *Prompt injection* example: the text tells the AI
   it's low priority, and it still comes out CRITICAL → Duty Officer. Invite a judge to type
   their own message.
7. **Fairness (30s).** The Fairness tab shows the baseline marking a formal message *lower* than
   its informal twin, while the final priority stays consistent.

---

## Project structure

```
server.py                 Flask API + officer-action state (acks, draft approvals, welfare checks)
src/triage.py             Final-priority decision: content → safety floor → access (raise-only)
src/classifier.py         Claude classifier: structured output, injection-resistant, fails loud
src/baseline_model.py     TF-IDF + logistic regression, 5-fold cross-validated
src/safety_net.py         Deterministic tripwires (priority floors)
src/access_scoring.py     Access-aware bump (normal / limited / cut-off)
src/routing.py            Team routing, ordered most-serious-first
src/acknowledgement.py    Draft replies: always need approval, safety-aware wording
src/escalation.py         Dead-man's switch: supervisor → duty manager
src/dropout_detector.py   "Sender went silent" detection
src/explain.py            One-line "Why:" for each item
src/evaluation.py         Recall-first scoring against ground truth
scripts/run_llm_batch.py  One-off real Claude run over the dataset
data/messages.py          152-message synthetic wet-season shift
static/                   Hand-built dispatch-console frontend
tests/test_safety.py      Safety-guarantee tests
```

---

## Limitations and what production would need

- **Real data and evaluation.** Retest on real, consented correspondence. The keyword tripwires
  and routes need review by duty officers and a family-violence practitioner.
- **Persistence and audit trail.** Officer actions are in memory (reset on restart). Production
  needs a database, officer identity, and an immutable log of who saw, acknowledged and approved what.
- **Channel ingestion.** Channels (SMS, email, webform, phone notes) are labelled, not ingested
  from live systems.
- **Access status** is supplied per message. In production it would come from road-closure and
  outage feeds (e.g. NT Road Report) matched to the sender's location.
- **Language.** Many NT residents speak an Aboriginal language or Kriol as their first language.
  English-only tripwires will miss some messages, so production would need co-designed phrase
  lists and interpreter pathways. This is the biggest open fairness question.
- **Privacy.** Sending message text to an external LLM needs a privacy impact assessment and
  data-residency review. The offline mode is also the privacy-preserving fallback.

## Dataset

`data/messages.py`: 152 synthetic messages simulating one high-volume wet-season shift
(low 56 · medium 41 · high 32 · critical 23), deliberately skewed toward routine items because
that skew *is* the needle-in-a-haystack problem. It covers one consistent weather event (Top End
monsoon flooding, with no bushfires since those are dry-season), two geographic clusters (flood-hit
Top End, unaffected Central Australia/Barkly), five like-for-like fairness pairs, and repeat
senders who either go silent (should flag) or follow up (shouldn't).
