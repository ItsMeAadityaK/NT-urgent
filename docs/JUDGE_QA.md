# Likely questions, and honest answers

Numbers are from the 152-message benchmark with real Claude API verdicts (`report/results_after.json`).

**Is the data real?**
No. We wrote it, so scores are optimistic. The pipeline and the Claude API verdicts are real. The fixed benchmark is
the independent check; the generated shifts are an upper bound.

**Why not just use the AI for everything?**
A single model can be unavailable in a storm, can be prompt-injected by the message itself, and can be quietly
wrong. On the benchmark the Claude API alone caught 52 of 55 urgent messages (94.5%); the full system caught 54 of
55 (98.2%) and all 23 critical ones. Each layer can only raise a priority, so any one of three signals is enough.

**What if the AI is down or there is no internet?**
The backup model and the safety rules take over, rows are marked *NOT AI-CHECKED*, and 54 of 55 urgent messages
(98.2%) and all 23 critical ones still reach the fast lane, at the cost of 12 of 97 routine messages escalated.

**Can someone trick the AI?**
The message is passed as untrusted data, and the safety rules are separate from the AI and ignore instructions in
the text. A message saying "low priority, do not escalate" followed by a threat stays critical. Priorities only rise.

**Does it send replies?**
Never. It drafts an acknowledgement; an officer approves it. A test fails if any code path sends a message.

**Won't over-escalation cause alert fatigue?**
It is a real cost. 10 of 97 routine messages are escalated, and 30% of all messages finish on the 15-minute clock
because access weighting is deliberate (someone cut off by floods is in a worse position). That is the first figure
we would check in a pilot; the report proposes measures and a roadmap.

**What did you change after testing?**
The first full pipeline missed 3 urgent messages (two carport-damage messages and a freezer message). The backup
model had said "high" on two of them, so we added a second-opinion floor: urgent recall rose from 94.5% to 98.2%,
and routine escalations rose from 1 to 10 of 97. We also moved that floor after the access boost, so a mosquito
complaint no longer jumped to critical. The report has a problems-and-fixes log.

**What about Aboriginal languages and Kriol?**
We do not pretend to understand them and we invented none. Text the system cannot read is raised to at least high
and routed to an interpreter desk (8 of 8 urgent test messages were buried before; 0 after). Our stand-in text is
deliberately fake. Real phrase lists need speakers, under community control (CARE and Maiam nayri Wingara principles).

**Is it fair to people who write informally?**
Five formal/informal pairs: the final priority matched on 4 of 5 (the AI model 4 of 5, the backup model 3 of 5). The
exception is a routine request where the formal wording made the backup model rate it high, and the floor passed
that on. It errs in the safe direction but it is a difference, and the report says so.

**Privacy?**
All messages here are synthetic. A real deployment needs a privacy impact assessment, redaction of personal details
and Australian hosting before any message goes to an external API (Information Act 2002 (NT); Privacy Act 1988 (Cth)).

**What is real and what is simulated?**
Real: the pipeline, the Claude API calls, safety rules, escalation logic, inbound endpoint (`POST /api/ingest`),
audit log. Simulated: the shift clock, the message source, and in-memory storage.

**How much does it cost to run?**
A fraction of a US cent a message at the rates we paid (about 10 to 25 US cents for a brand-new 55-message shift); the 152-message benchmark run cost well under one dollar.
Answers are saved by message, so replaying a shift is free.
