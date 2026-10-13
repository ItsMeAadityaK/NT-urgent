# NT Correspondence Triage

**Team AIC023 · CDU IT Code Fair 2026 · AI Challenge, Brief 5: "Getting urgent messages to a human, fast"**

> How might we make sure a vulnerable person's urgent message never gets buried in a high-volume government
> inbox and reaches a human quickly?

A working triage console for a Northern Territory government correspondence unit in the wet season. It sorts
every message into low, medium, high or critical, explains the call in plain English, routes it to a team, drafts
an acknowledgement, and **escalates to a named person if nobody acts. It never replies to the public by itself**
(a test checks that no code path can).

Urgency comes from three readers that can only ever *raise* a priority: the **Claude API**, a small **baseline ML
model** trained on our data, and **fixed safety rules**. Senders cut off by floods are raised further, and text
the system cannot read goes to an interpreter desk instead of sinking to the bottom.

---

## What is in this submission

| Item | Where |
|---|---|
| Project report (PDF and editable Word) | `report/AIChallenge_Team AIC023_Report.pdf`, `.docx` |
| Presentation slides (+ static PDF copy) | `presentation/NT-Triage-Deck.pptx`, `NT-Triage-Deck-handout.pdf` |
| Source code (Python, commented at the key steps) | `src/`, `server.py`, `scripts/`, `tests/` |
| Web console (HTML, CSS, JavaScript) | `static/` |
| Data (synthetic, written by us) and saved AI answers | `data/` |
| Reproduction instructions | this file |

**Data sources.** There is no external dataset. All messages are synthetic and were written by the team:
`data/messages.py` (152 hand-written benchmark messages), `src/generator.py` (a seeded generator of 55-message
shifts) and `data/language_standins.py` (invented letter-swapped text, not a real language). Real-world
statistics and policy sources are cited, with links, in the report's reference list.

---

## Quick start (about two minutes, no API key needed)

Python 3.10 or newer (developed on 3.12).

```bash
pip install -r requirements.txt
python -m pytest -q          # 97 tests, no network
python server.py             # then open http://127.0.0.1:5050
```

The console opens on a generated shift (seed 2026) and replays **saved real Claude API verdicts**
(`data/llm_cache.json`, `data/llm_results.json`), so it works offline and spends nothing.

Things to try:

- **Message Queue**: press PLAY (or drag the timeline) and watch messages arrive. The dark "Needs a human now"
  panel shows what is overdue or silent. Open a row for the full reasoning and the draft reply.
- **How It Works**: pick a message and press REPLAY to see it travel through every check.
- **Try a Message**: type anything. Try the "Prompt injection" and "Unreadable language (stand-in)" examples.
- **Evaluation / Fairness Audit**: scores against a hidden answer key, and matched formal/informal pairs.
- **NT Map**, **Welfare Checks**, **Activity Log**: where messages come from, silent senders, and who did what.
- `?t=240` in the address opens the shift at +240 minutes; `#journey`, `#try`, `#compare` open a tab.

Pressing **NEW SHIFT** with no seed generates brand-new messages and, if an API key is set, asks the Claude API to
judge them (roughly 10 to 25 US cents). A seed that has been run before replays for free.

## Using the live Claude API (optional)

**This submission already includes a `.env` file** (a hidden file in the project folder) holding a key with a small credit balance, so you can press NEW SHIFT with an empty seed and see the live Claude API judge a brand-new shift (roughly 10 to 25 US cents each; a built-in cap stops a runaway). Please do not share it. To use your own key instead, replace the line in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Then `python server.py` reads it itself. Settings (environment variables): `TRIAGE_MODEL` (default
`claude-sonnet-5-5`), `LLM_CALL_LIMIT` (hard cap on live calls, default 300), `SHIFT_SEED` (first shift),
`PORT`, `INGEST_TOKEN`, `TRIAGE_SECOND_OPINION_FLOOR=0` (switch the second-opinion floor off),
`TRIAGE_NO_DOTENV=1` (ignore `.env`). Without a key, rows are honestly marked *NOT AI-CHECKED* and triaged by the
baseline model and the safety rules; no AI verdict is ever invented.

`python scripts/run_llm_batch.py` classifies the 152 benchmark messages once with the real API and saves
`data/llm_results.json` (already included).

---

## Reproducing the numbers in the report

Every number in the report is read from the running system, not typed:

```bash
python report/collect_results.py before     # without the second-opinion floor  -> report/results_before.json
python report/collect_results.py after      # the current system                -> report/results_after.json
python scripts/language_parity.py           # the unreadable-text test (8 of 8 urgent buried before, 0 after)
```

To rebuild the report itself (optional): `pip install -r requirements-report.txt`, then
`python report/figures.py`, `python report/build_report.py` (PDF) and `python report/build_docx.py` (Word).
The interface figures are the ready-made `report/fig_*.png` files (the large raw screenshots they were cropped from are left out to keep the ZIP small; `figures.py` skips any that are missing).

---

## How it works

```
message ─► readers ──────────────────────────────┐  content urgency
           Claude API (meaning, typos, slang)    │
           baseline ML (TF-IDF + logistic regr.) ┤  (baseline only if the API is down)
                                                 ▼
        safety tripwires (61 patterns, 10 groups) → readability check (unreadable → at least high)
                 → access weighting (limited +1, cut-off +2) → second-opinion floor (backup says
                   high/critical, AI lower → at least high)
                                                 ▼
        final priority → route (12 teams) + draft reply (never sent) → officer
        → clock: critical 15 min, high 60, medium 240 → shift supervisor → duty manager at twice the limit
        → a sender who goes quiet is flagged for a welfare check
```

Design rules: nothing can lower a priority; if the AI fails the item is marked and the other layers carry on; the
safety rules ignore instructions written inside a message; the AI sees the message as untrusted data.

## Results (152 hand-written messages, real Claude API verdicts)

| Approach | Urgent caught (of 55) | Critical caught (of 23) | Routine escalated (of 97) |
|---|---|---|---|
| Backup ML model alone (5-fold cross-validation) | 47 (85.5%) | 12 (52.2%) | 9 |
| Safety rules alone | 36 (65.5%) | 16 (69.6%) | 0 |
| Claude API alone | 52 (94.5%) | 21 (91.3%) | 0 |
| **Full system** | **54 (98.2%)** | **23 (100%)** | 10 |
| Full system, Claude API switched off | 54 (98.2%) | 23 (100%) | 12 |

Two generated shifts (seeds 2026, 4242) with real verdicts are in the report's appendix. These scores come from
synthetic data we wrote, so real-world results will be lower; the report says so and recommends a shadow-mode pilot.

---

## Repository layout

```
server.py                    Flask app and JSON API (state, acknowledge, classify, ingest, new shift)
src/classifier.py            Claude API call: untrusted-data prompt, JSON schema, fails loud
src/baseline_model.py        TF-IDF + logistic regression, out-of-fold predictions
src/safety_net.py            deterministic tripwires (can only raise a priority)
src/language_check.py        unreadable-text check -> interpreter desk
src/triage.py                the single place a final priority is decided, with plain-English steps
src/access_scoring.py        access weighting         src/routing.py          keyword routing to teams
src/escalation.py            clocks and ladder        src/dropout_detector.py silent-sender check
src/acknowledgement.py       draft replies (never sent)   src/generator.py     seeded shifts, hidden answer key
data/                        benchmark, language stand-ins, saved Claude API answers
static/                      the console (index.html, app.js, journey.js, fx.js, style.css) and /script.html
scripts/                     run_llm_batch.py, language_parity.py
tests/                       97 tests: safety guarantees, replayable shifts, language, inbound endpoint
report/                      the report, its build scripts, figures and results
presentation/                the deck and its build scripts
```

`POST /api/ingest` is where a real channel (an SMS gateway, an email forwarder, a web form) would plug in; a
message posted there is triaged by the same pipeline and appears in the queue within seconds.

## Limitations and next steps

Synthetic data; a simulated clock; officer actions held in memory (no database); no live SMS or email feed;
English-language text only; one AI model. Sending real messages to an external API needs a privacy impact
assessment and Australian hosting first. No Aboriginal-language or Kriol text was invented anywhere; real phrase
lists would have to come from speakers, under community control. The report's recommendations and roadmap set out
what a real pilot would need.
