# Judge Q&A prep

Likely hard questions from an industry panel, with answers grounded in what the build actually does.

**"Your LLM scores 100%. Isn't that suspicious?"**
Yes, and we say so on screen. Until `scripts/run_llm_batch.py` is run, the LLM column holds
hand-authored stand-ins that match the answer key. That's why we don't rely on it: the
headline claim is the **LLM-outage row**. With the LLM switched off, baseline + tripwires +
access weighting still puts 100% of critical and 98% of urgent messages in the fast lane.
*(If you've run the batch script, quote the real numbers instead.)*

**"Why not just use the LLM for everything?"**
Three failure modes a single LLM has and our design doesn't: it can be down (wet-season
outages), it can be prompt-injected by the message itself, and it can be quietly wrong. Each
layer can only raise a priority, so any one of three independent signals catching a message
is enough.

**"Won't the tripwires cause alert fatigue?"**
We measured the cost: in outage mode, 12 of 97 routine items get a faster look than they
needed. That's the deliberate trade. A few extra minutes of officer time buys zero missed
critical messages. The tripwires alone produced 0 false escalations on this dataset.

**"Your tripwires were written against your own dataset. Isn't that overfitting?"**
Partly, yes, and the README says so. The baseline numbers are clean (5-fold out-of-fold). In
production the phrase lists would be reviewed by duty officers and a family-violence
practitioner, and re-measured on real, consented correspondence.

**"How does it handle someone who can't write formal English?"**
Three ways:
- The LLM prompt says spelling and informality must not lower urgency.
- The Fairness tab tests five like-for-like formal/informal pairs. The baseline alone is
  inconsistent on 2 of 5, but the final priority is consistent on all 5.
- The honest gap: Aboriginal languages and Kriol. That needs co-designed phrase lists and
  interpreter pathways, not a patch.

**"What stops the AI replying to someone in danger?"**
There is no send path in the code (a test checks that no module imports an email/SMS
library). Every draft is marked NOT SENT and needs an officer's click. For personal-safety
cases, the draft doesn't repeat what was disclosed, in case the person causing harm reads the
phone. The officer is prompted to call instead.

**"What if nobody acknowledges?"**
Dead-man's switch. A critical item escalates to the shift supervisor at 15 minutes and the
duty manager at 30. It stays pinned in "Needs a human now" until someone acts. If a sender who
reported something critical then goes silent for 2 hours, that silence is flagged as its own
risk and prompts a welfare check.

**"Why does being cut off raise priority if the content is the same?"**
The same problem is more dangerous when the person can't reach any other help. A burst pipe
in Darwin and one in a flood-isolated community aren't equally urgent. Both values are shown,
so the officer sees the content urgency and the access adjustment separately.

**"Privacy? You're sending public correspondence to an external AI."**
It would need a privacy impact assessment and a data-residency review before production. The
offline mode (baseline + tripwires) is also the privacy-preserving fallback: it works with no
data leaving the building.

**"What would you build next?"**
In order:
1. Real evaluation data.
2. A persistent audit log with officer identity.
3. Live access status from road-closure and outage feeds.
4. Real channel ingestion.
5. Language co-design.
