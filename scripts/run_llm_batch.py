"""
run_llm_batch.py

Runs the real Claude classifier over all 152 dataset messages ONCE and
caches the results to data/llm_results.json. The server then uses those
genuine model outputs (instead of the hand-authored stand-in values in
messages.py), so the demo runs offline and reproducibly while the
LLM-vs-baseline and fairness comparisons reflect a real model.

Usage:
    export ANTHROPIC_API_KEY=...
    python scripts/run_llm_batch.py

Cost: 152 short classification calls — a few cents in total.
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "data"))

from classifier import MODEL, classify_urgency, llm_configured  # noqa: E402
from messages import get_sample_messages  # noqa: E402

OUT_PATH = os.path.join(ROOT, "data", "llm_results.json")


def main():
    if not llm_configured():
        sys.exit("ANTHROPIC_API_KEY is not set — nothing to do.")

    messages = get_sample_messages()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda m: classify_urgency(m["raw_text"]), messages))

    out, failures = {}, []
    for m, r in zip(messages, results):
        if r["ok"]:
            out[m["message_id"]] = {"urgency_score": r["urgency_score"], "flag_reason": r["flag_reason"]}
        else:
            failures.append((m["message_id"], r["error"]))

    agree = sum(out[m["message_id"]]["urgency_score"] == m["true_urgency"]
                for m in messages if m["message_id"] in out)
    payload = {
        "model": MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results": out,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=1)

    print(f"Classified {len(out)}/{len(messages)} messages -> {OUT_PATH}")
    print(f"Exact agreement with true_urgency: {agree}/{len(out)}")
    for mid, err in failures:
        print(f"  FAILED {mid}: {err}  (server will treat these as degraded / baseline + safety net)")


if __name__ == "__main__":
    main()
