"""
collect_results.py

Runs the system (no network, no API spend: it only replays saved AI verdicts) and writes every
number the report quotes to report/results_<tag>.json, so the report is never typed from memory.

    python report/collect_results.py          # current system        -> results_after.json
    python report/collect_results.py before   # without the second-opinion floor -> results_before.json
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "data")):
    sys.path.insert(0, p)
os.environ.setdefault("TRIAGE_NO_DOTENV", "1")      # replay only: never touch the API key
TAG = sys.argv[1] if len(sys.argv) > 1 else "after"
if TAG == "before":
    os.environ["TRIAGE_SECOND_OPINION_FLOOR"] = "0"

import server                                        # noqa: E402
import safety_net                                    # noqa: E402
from messages import get_sample_messages             # noqa: E402

out = {}


def evalrows(ev):
    rows = {}
    for r in ev["rows"]:
        key = ("ai" if r["name"].startswith("LLM alone") else
               "baseline" if r["name"].startswith("Baseline") else
               "rules" if r["name"].startswith("Safety") else
               "full_outage" if "OUTAGE" in r["name"] else "full")
        rows[key] = {"urgent_recall": r["urgent_recall"], "critical_recall": r["critical_recall"],
                     "accuracy": r["accuracy"], "false_urgent": r["false_urgent"], "n_routine": r["n_routine"],
                     "missed": r["missed_urgent"]}
    return {"n": ev["n"], "rows": rows, "llm_is_real": ev.get("llm_is_real"), "llm_ok": ev.get("llm_ok"),
            "baseline_per_class_recall": ev.get("baseline_per_class_recall")}


# ---- benchmark (152 hand-written messages, real AI verdicts from scripts/run_llm_batch.py)
server._activate("benchmark")
st = server._build_state(480, True)
out["benchmark"] = evalrows(st["evaluation"])
out["benchmark"]["llm_is_real"] = st["evaluation"].get("llm_is_real")

msgs = get_sample_messages()
out["benchmark"]["composition"] = {
    "urgency": dict(collections.Counter(m["true_urgency"] for m in msgs)),
    "channel": dict(collections.Counter(m["channel"] for m in msgs)),
    "access": dict(collections.Counter(m["access_status"] for m in msgs)),
    "locations": len({m["location"] for m in msgs}),
    "senders": len({m["sender_id"] for m in msgs}),
}
# how often the AI alone matched the answer key, and where it disagreed
ai = [m for m in st["messages"] if m["llm_urgency"]]
out["benchmark"]["ai_exact"] = sum(m["llm_urgency"] == m["true_urgency"] for m in ai) / len(ai)
out["benchmark"]["ai_n"] = len(ai)
order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
out["benchmark"]["ai_over"] = sum(order[m["llm_urgency"]] > order[m["true_urgency"]] for m in ai)
out["benchmark"]["ai_under"] = sum(order[m["llm_urgency"]] < order[m["true_urgency"]] for m in ai)
out["benchmark"]["ai_within1"] = sum(abs(order[m["llm_urgency"]] - order[m["true_urgency"]]) <= 1 for m in ai)
# final-system confusion (true -> final), with the AI online
conf = {t: collections.Counter() for t in order}
for m in st["messages"]:
    conf[m["true_urgency"]][m["access_adjusted_priority"]] += 1
out["benchmark"]["confusion_final"] = {t: dict(c) for t, c in conf.items()}

# fairness pairs
fp = []
for pair in st["fairness_pairs"]:
    pid = pair["pair_id"]
    inf, frm = pair.get("informal"), pair.get("formal")
    if inf and frm:
        fp.append({"id": pid, "truth": inf["true_urgency"],
                   "ai": (inf["llm_urgency"], frm["llm_urgency"]),
                   "baseline": (inf["baseline_urgency"], frm["baseline_urgency"]),
                   "final": (inf["access_adjusted_priority"], frm["access_adjusted_priority"])})
out["benchmark"]["fairness"] = fp

# ---- generated shifts (hidden answer key, real AI verdicts replayed from the cache)
for seed in (2026, 4242):
    server._activate("shift", seed, allow_live=False)
    st = server._build_state(480, True)
    out[f"shift_{seed}"] = evalrows(st["evaluation"])
    fp = []
    for pair in st["fairness_pairs"]:
        pid = pair["pair_id"]
        inf, frm = pair.get("informal"), pair.get("formal")
        if inf and frm:
            fp.append({"id": pid, "ai": (inf["llm_urgency"], frm["llm_urgency"]),
                       "final": (inf["access_adjusted_priority"], frm["access_adjusted_priority"])})
    out[f"shift_{seed}"]["fairness"] = fp
    out[f"shift_{seed}"]["composition"] = dict(collections.Counter(m["true_urgency"] for m in st["messages"]))
    out[f"shift_{seed}"]["channels"] = dict(collections.Counter(m["channel"] for m in st["messages"]))

# ---- code facts
patterns = sum(len(p) for _, _, p in safety_net.TRIPWIRES)
import routing                                      # noqa: E402
teams = {team for _, team, _ in routing.ROUTES} | {routing.DEFAULT_ROUTE[1], "Interpreter & community liaison"}
out["code"] = {"tripwires": len(safety_net.TRIPWIRES), "tripwire_patterns": patterns, "teams": len(teams),
               "tripwire_groups": [[n, f, len(p)] for n, f, p in safety_net.TRIPWIRES]}
src_lines = 0
for base in ("src", "server.py", "static"):
    path = os.path.join(ROOT, base)
    files = [path] if os.path.isfile(path) else [os.path.join(d, f) for d, _, fs in os.walk(path) for f in fs
                                                 if f.endswith((".py", ".js", ".html", ".css")) and "__pycache__" not in d]
    for f in files:
        src_lines += sum(1 for _ in open(f, encoding="utf-8", errors="ignore"))
out["code"]["lines"] = src_lines

with open(os.path.join(HERE, f"results_{TAG}.json"), "w") as f:
    json.dump(out, f, indent=1, default=str)
print(json.dumps({k: (v if k == "code" else {kk: vv for kk, vv in v.items() if kk in ("n", "rows", "ai_exact")})
                  for k, v in out.items()}, indent=1, default=str)[:6000])
