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
- **Generated shifts are optimistic.** The live shifts (below) are built from templates we wrote, so
  their wording overlaps in theme with what the baseline trained on. Their scores sit next to, never
  instead of, the hand-written benchmark above, and the Evaluation tab says so.

---

## Live shifts: new messages every time

The queue no longer shows the same 152 messages every run. By default it shows a **live shift**: about
55 freshly generated messages (`src/generator.py`), arriving front-loaded like a real storm morning.

- **NEW SHIFT** makes a different shift each press. The seed is shown on screen; type a seed into the
  box and press NEW SHIFT (or Enter) to replay a shift exactly. `SHIFT_SEED=1234 python3 server.py`
  sets the first one.
- **True urgency is a hidden answer key.** Messages are created with a secret label that the queue never
  shows and no classifier sees. It is only used to score the system afterwards (Evaluation tab). A test
  checks that flipping every label changes no priority.
- **Variety comes from independent random pieces**: situation, who and how long, writing style
  (formal, SMS, rambling, ALL CAPS), and noise (typos, `u`/`2`/`pls` shorthand, voice-to-text mistakes),
  across 58 scenarios and ~180 templates. The mix is deliberately mostly routine, about 13% critical.
- **Every shift contains the cases worth demonstrating**: a flooded cut-off critical, a child alone, a
  collapse, a medication risk, senders who go silent, a sender who follows up (dropout must *not* fire),
  a routine message from an access-limited sender, and three formal/informal fairness pairs.
- **Not copied from training data.** Templates were checked against the 152 the baseline trains on, and
  a test fails if any is more than 80% similar to one of them.
- **The 152 are still here** as the baseline's training data and an independent benchmark. The Evaluation
  tab shows both. "Use the 152-message benchmark instead" (under the control bar) switches the queue to it.

With a Claude key set, a new shift sends its ~55 messages to Claude once (a few cents), and the verdicts
are cached in `data/llm_cache.json` by message text, so **replaying a seed is free and works offline**.
Do this at home before a demo: run the seed you plan to present, and it replays with the real LLM
verdicts even with no network. Without a key the shift runs honestly on baseline + safety net, every row
is flagged NOT LLM-CHECKED, and no LLM verdict is ever invented.

**Community phrases.** The generator never invents Kriol or Aboriginal-language text. If
`data/community_phrases.json` exists, up to two entries are mixed into each shift. Each entry must be
written or reviewed by a speaker or interpreter:
`[{"text": "...", "true_urgency": "critical", "language": "Kriol", "source": "reviewed by ..."}]`.

---

## How to run it

```bash
pip install -r requirements.txt
python3 server.py
```

Open **http://127.0.0.1:5050**. (Not 5000: on macOS that port belongs to AirPlay Receiver.
Override with `PORT=8000 python3 server.py`.)

Optional, to use real Claude outputs. Put your key in a file called `.env` in the project folder
(it is already git-ignored, so it never reaches GitHub; never paste a key into any other file):

```
ANTHROPIC_API_KEY=sk-ant-...
```

```bash
python3 server.py                     # reads .env itself; "Try a message" and NEW SHIFT now call Claude
python3 scripts/run_llm_batch.py      # optional: classify the 152 benchmark messages → data/llm_results.json
```

The default model is Claude Sonnet 5.5 (`TRIAGE_MODEL=claude-haiku-4-5` for cheaper, or
`claude-opus-5-5` for the most capable). Tests never read `.env`, so they cost nothing.

Run the tests:

```bash
python3 -m pytest -q
```

78 tests cover the safety guarantees (nothing lowers a priority, prompt injection can't bury a
flagged message, every critical message survives an LLM outage on the benchmark, escalation climbs,
drafts always need approval, no module imports a message-sending library) and the generated shifts
(replayable, varied, contain the demo cases, hidden labels never affect priority). Tests never call
the API, whatever is in your shell.

---

## Demo script (≈5 minutes)

1. **The problem (30s).** Press **NEW SHIFT**: a wet-season shift of ~55 freshly generated messages,
   most of them routine, about 7 life or death. Nobody (including us) knows in advance which ones;
   the true urgency is a hidden answer key. Drag the clock back to the start of the shift.
2. **The needle (60s).** Press **PLAY**. As the clock runs, criticals arrive and the 15-minute
   clock starts. Unacknowledged items climb to *Shift supervisor* and then *Duty manager*. Open
   a critical item → **full reasoning + draft reply**. Show the plain-English steps and the **safety-aware
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
src/generator.py          Seeded random shifts: scenarios x style x noise, hidden answer key
scripts/run_llm_batch.py  One-off real Claude run over the dataset
data/messages.py          152 hand-written messages: baseline training data + independent benchmark
static/                   Hand-built dispatch-console frontend
tests/test_safety.py      Safety-guarantee tests
tests/test_shift.py       Generated-shift tests (replay, variety, demo cases, no leakage)
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
