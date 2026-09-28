# Correspondence Triage — Dispatch Console

AI Challenge (CDU IT Code Fair 2026) — Brief #5: Getting urgent messages to a human, fast.

## What this is

A working urgency-triage system for a government correspondence unit, with
NT-specific differentiators:
- **Access-aware priority weighting** — same content, different real-world
  priority depending on how reachable the sender currently is (normal /
  limited / cut-off).
- **Comms-dropout detection** — flags when a sender goes silent for longer
  than expected after an urgent message, treating the silence itself as a
  possible risk signal.
- **Escalation timeout ("dead-man's switch")** — unacknowledged urgent items
  auto-escalate rather than silently sitting in a queue.
- **Dual classification** — an LLM-based classifier and a locally-trained
  TF-IDF/Logistic Regression baseline run side by side, so disagreements
  between them can be examined (useful for the fairness/ethics discussion).
  The baseline is evaluated properly: trained on an 80% split of the real
  152-message dataset, accuracy measured on the 20% it never saw.
- **Fairness audit tab** — five formal-vs-informal phrasing pairs (one per
  urgency band, low through critical) testing whether each classifier
  scores identical situations consistently regardless of writing style.
- **Real acknowledgement** — clicking ACKNOWLEDGE on a message actually
  persists server-side and feeds back into the escalation check, so an
  acknowledged critical item stops auto-escalating (this was hardcoded
  `False` in the earlier Streamlit build).
- **NT map view** — a schematic (not-to-scale) map spanning the Top End to
  Central Australia, pins per location coloured by the highest active
  priority there and pulsing when something at that location needs
  escalation. Click a pin to filter to that location's messages.

## Architecture

The triage logic (`src/classifier.py`, `baseline_model.py`,
`access_scoring.py`, `dropout_detector.py`, `escalation.py`) is unchanged
from the original build and unopinionated about UI. It's now served by a
small Flask API (`server.py`) instead of Streamlit, with a hand-built
frontend (`static/index.html`, `style.css`, `app.js`) — a dark
"dispatch-log" console styled for the operational context (emergency
correspondence triage), not a generic admin-dashboard look.

The original Streamlit build (`app.py`) is kept for reference but is no
longer the primary interface.

## How to run it

```bash
pip install -r requirements.txt
python server.py
```

Then open http://127.0.0.1:5000 — the sim clock can be dragged with the
slider or auto-advanced with PLAY (speed selectable). Escalation/dropout
flags trigger as the clock advances; ACKNOWLEDGE actually clears escalation
for that item, and RESET ACKS clears all acknowledgements for a fresh demo
run.

(The old Streamlit build still works too: `streamlit run app.py`.)

## Dataset

`data/messages.py` holds 152 synthetic messages simulating one high-volume
wet-season shift (see the module docstring for the full design rationale).
Highlights:

- Distribution deliberately skewed toward low/medium urgency (55/40) with a
  meaningful minority of high/critical (32/23) — most real correspondence
  is mundane, and that skew IS the "needle in a haystack" problem the brief
  is about.
- One consistent weather event (Top End monsoon flooding), not a mix of
  unrelated disaster types — e.g. deliberately no bushfire scenarios, since
  that's a dry-season NT phenomenon.
- Two geographic clusters: Top End communities (where the flood/storm
  messages concentrate) and Central Australia / Barkly towns (unaffected by
  this weather event, mostly routine correspondence plus occasional
  unrelated urgent cases) — geographically honest, and stops the dataset
  being monotonously "everything is a flood emergency."
- Every message has a `true_urgency` ground-truth label, separate from
  `llm_urgency` (the pre-authored LLM stand-in) — needed to actually
  measure classifier accuracy against a real answer key.
- Five formal/informal fairness-audit pairs (one per urgency band), plus
  deliberate repeat senders with realistic gaps to exercise the dropout
  detector both positively (goes silent, should flag) and negatively
  (follows up, should NOT flag).

## Current state — what's real vs. placeholder

- **Baseline model**: trained and evaluated properly — 80/20 split of the
  152-message dataset, accuracy measured on the held-out 20%, then a final
  production fit on the full dataset for live predictions in the app. See
  `train_baseline_from_dataset()` in `src/baseline_model.py`.
- **Access weighting, dropout detection, escalation logic**: fully
  functional, running live. (The dropout detector had a latent bug — it
  expected an `urgency_score` key but was being fed `llm_urgency` — fixed
  in `server.py`, not in `dropout_detector.py` itself, since the module's
  documented contract was correct and the caller just wasn't honouring it.)
- **LLM classification**: pre-authored stand-in values in `data/messages.py`,
  NOT live API calls yet. This was deliberate — it lets the whole pipeline
  be built, tested, and demoed without needing an API key or spending money
  during development.
- To switch to real LLM calls: set `USE_MOCK = False` in
  `src/classifier.py`, set the `ANTHROPIC_API_KEY` environment variable,
  and wire `server.py` to call `classify_urgency()` from `classifier.py`
  instead of reading `llm_urgency` from the sample data.
- **Human acknowledgement**: real now — `server.py` holds acknowledgement
  state in memory and the escalation check reads it live.

## Still to build

- Multi-channel input parsing (currently just labelled, not actually
  ingested from real email/SMS/webform formats)
- Acknowledgement state is in-memory only (resets on server restart) — fine
  for a demo, would need a real store for production
- Housekeeping: `app.py` (old Streamlit build) and the empty `src/explain.py`
  are still in the repo for reference — fine to delete once you're sure you
  don't want them for a "here's our design evolution" slide