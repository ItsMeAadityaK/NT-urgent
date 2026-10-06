"""
language_parity.py

Language fairness test: does a message in another language get ranked LOWER than the same
message in English? That would mean the system buries people who don't write in English.

Each pair is (English meaning, other-language text). The pipeline runs with the LLM switched
off, so this costs nothing and shows what protects someone even if the AI is down.

  - Stand-ins (data/language_standins.py) are an invented letter-swap, NOT a real language.
    They test the mechanism: what happens to text the system cannot read.
  - Real phrases (data/community_phrases.json, written or reviewed by a speaker or interpreter,
    each with an "english_meaning") are added automatically when that file exists:
        [{"text": "...", "english_meaning": "...", "true_urgency": "critical",
          "language": "Kriol", "source": "reviewed by ..."}]

Run:   python scripts/language_parity.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "data"), ROOT):
    sys.path.insert(0, p)
os.environ["TRIAGE_NO_DOTENV"] = "1"  # this script never needs (or spends) an API key

import language_check  # noqa: E402
import server  # noqa: E402
from language_standins import PAIRS, standin  # noqa: E402

RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
OUTAGE = {"ok": False, "error": "LLM switched off for this test"}


def priority(text, label="T"):
    msg = {"message_id": label, "raw_text": text, "access_status": "normal", "channel": "sms"}
    return server._finish_triage(msg, OUTAGE)["decision"]["access_adjusted_priority"]


def load_cases():
    cases = [("stand-in", eng, standin(eng), urg) for eng, urg in PAIRS]
    path = os.path.join(ROOT, "data", "community_phrases.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for e in json.load(f):
                if e.get("text") and e.get("english_meaning"):
                    cases.append((e.get("language", "real"), e["english_meaning"], e["text"], e.get("true_urgency", "?")))
    return cases


def main():
    cases = load_cases()
    checker = language_check._checker
    rows = []
    for kind, english, other, truth in cases:
        en = priority(english)
        language_check.disable()
        before = priority(other)
        language_check._checker = checker
        after = priority(other)
        rows.append((kind, truth, en, before, after, other))

    print(f"{'kind':9} {'true':8} {'English':8} {'other BEFORE fix':17} {'other AFTER fix':15}  text")
    for kind, truth, en, before, after, other in rows:
        flag = "  <- BURIED" if RANK[before] < RANK.get(truth, 0) and RANK[before] < 2 <= RANK.get(truth, 0) else ""
        print(f"{kind:9} {truth:8} {en:8} {before:17} {after:15}  {other[:46]}{flag}")

    urgent = [r for r in rows if r[1] in ("high", "critical")]
    buried_before = sum(RANK[r[3]] < 2 for r in urgent)
    buried_after = sum(RANK[r[4]] < 2 for r in urgent)
    routine = [r for r in rows if r[1] in ("low", "medium")]
    pushed_after = sum(RANK[r[4]] >= 2 for r in routine)
    print(f"\nUrgent messages ranked below 'high' (buried): BEFORE the fix {buried_before}/{len(urgent)}, "
          f"AFTER {buried_after}/{len(urgent)}")
    print(f"Routine messages pushed up to 'high' by the same rule: {pushed_after}/{len(routine)} "
          f"(the price: the system can't tell routine from urgent in a language it can't read, so a person looks)")


if __name__ == "__main__":
    main()
