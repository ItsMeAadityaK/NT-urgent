// The talk: PowerPoint (presentation/NT-Triage-Deck.pptx) + live demo, 10 minutes in all.
// Rendered by script.html (the printable speaker sheet).
//
// secs   : time budget for the part
// say    : what to say, in your own words
// do     : what to click (demo only)

const TALK = [
  { part: "slides", title: "1. The inbox", secs: 35,
    say: ["Let the inbox build by itself. A normal morning: bin days, receipts, thank-yous. And one of these is someone saying her mum has collapsed.",
          "Our system exists so that message is never the 43rd thing someone reads.",
          "One rule to plant now: it never replies by itself. It makes sure a named person sees the urgent ones, and chases them if they do nothing."] },
  { part: "slides", title: "2. The NT problem", secs: 50,
    say: ["Three facts, not a lecture: 58.5% of First Nations people in the NT speak an Indigenous language at home; 43% of First Nations communities and homelands have no mobile service; the NT's assault rate is 4.4 times the national rate.",
          "In March 2024 the phone towers at Borroloola went down in the flood.",
          "So the person we built for writes briefly, on a phone, maybe not in English, and may not write twice."] },
  { part: "slides", title: "3. Triage, escalate, never reply", secs: 45,
    say: ["Walk the flow as it builds: a message arrives, three readers judge it, the priority can only rise, it lands with a named person, a clock starts.",
          "15 minutes for critical. If nobody acknowledges it, it climbs to the shift supervisor, then the duty manager.",
          "Land the banner: it drafts, a person approves, it never sends."] },
  { part: "slides", title: "4. Three readers", secs: 50,
    say: ["The AI model understands meaning (it runs on the Claude API). A small ML model we trained is the second opinion and works with no network. Fixed safety rules can't be talked out of a threat.",
          "None can lower a priority. Senders cut off by floods go up two levels; text we can't read goes to an interpreter at HIGH."] },
  { part: "slides", title: "5. Does it work?", secs: 55,
    say: ["The chart is urgent messages caught, out of the 55 that are truly urgent. Backup model alone 85%, rules alone 65%, the AI model alone 94.5%. Together 54 of 55, and all 23 critical on the 15-minute clock. With the AI switched off it is still 98%.",
          "Be honest about the price: 10 of 97 routine messages are escalated, and we wrote the data ourselves, so real scores will be lower."] },

  { part: "demo", title: "Demo 1. The live queue", secs: 60,
    say: ["This is a live shift: 55 fresh messages. The right answers are hidden and only used to score us.",
          "The dark panel at the top shows only what is overdue or has gone silent."],
    do: "Slide 6: click OPEN THE CONSOLE (or Alt+Tab to the browser). Press PLAY, let messages arrive, then pause. Open one row: full reasoning + draft reply." },
  { part: "demo", title: "Demo 2. Follow one message", secs: 60,
    say: ["Same data as a journey: channel, six checks, a named team, then the escalation ladder.",
          "The final priority only ever goes up."],
    do: "How It Works tab. Pick a critical message, press REPLAY. Point at each stage as it lights up." },
  { part: "demo", title: "Demo 3. Try to break it", secs: 75,
    say: ["Type like a real person: typos, no punctuation. It still works.",
          "This one is a prompt-injection attack telling the AI to ignore a threat. The safety rules still catch it.",
          "Text it can't read goes to the interpreter team at high. Our stand-in text is invented, not a real language."],
    do: "Try a Message tab. Click \u201cPrompt injection\u201d, TRIAGE IT. Then \u201cUnreadable language (stand-in)\u201d, TRIAGE IT. (A few cents if not cached.)" },
  { part: "demo", title: "Demo 4. Nobody acts", secs: 45,
    say: ["If nobody acknowledges in time it goes up the ladder, and every action is recorded against who did it.",
          "Replies are drafts. A person approves."],
    do: "Message Queue. Drag the timeline to about +240 min. Set ACTING AS to Shift supervisor. ACKNOWLEDGE an overdue row." },
  { part: "demo", title: "Demo 5. The scores", secs: 45,
    say: ["Same bars as the slide, computed live from the hidden answer key. The last row is the whole system with the AI switched off: urgent messages still reach a human."],
    do: "Evaluation tab. Point at the bars, then the AI-off row. Do NOT press NEW SHIFT on stage." },

  { part: "slides", title: "7. What is real, what is next", secs: 50,
    say: ["Real: the pipeline, the clocks, the silent-sender check, the audit trail and real AI verdicts. Next: a shadow pilot for one wet season, real SMS and email feeds, phrases reviewed by speakers.",
          "Our own warnings are on the slide: synthetic data, 30% of messages reach the critical clock, one model, English only.",
          "End on: help people, never replace them. Then Questions. Backup slides are hidden; click the small amber links."] },
];

const TALK_EXTRA = [
  "If asked or time allows (30s each): NT Map (where trouble is), Fairness Audit (same emergency written casually and formally gets the same priority), Activity Log (who did what, when).",
];

const QA = [
  ["Is the data real?",
   "No. It is synthetic, generated from our own templates with a hidden answer key, so scores are optimistic. The fixed 152-message benchmark is the independent check. The pipeline is real; real messages would use the same endpoint."],
  ["Why not just use keywords?",
   "We tested it: the safety rules alone miss many urgent messages (see the Evaluation table). Rules are the floor that cannot be argued with; the AI understands meaning and typos; the ML model is the backup."],
  ["What if the AI is down or has no internet?",
   "The backup model and safety rules take over, rows are marked NOT CLAUDE-CHECKED, and urgent messages still reach a human. The last row of the Evaluation table shows exactly that case."],
  ["Can someone trick the AI?",
   "That is what the prompt-injection example shows. The safety rules are separate from the AI and only ever raise priority, so a message saying “mark this low” cannot lower it."],
  ["Does it send replies?",
   "Never. It drafts an acknowledgement; an officer approves it. A test checks that no code path sends a message."],
  ["What about Aboriginal languages?",
   "We do not pretend to understand them. If text is not readable, it is raised to at least high and sent to the Interpreter & community liaison team. Our demo text is an invented stand-in. Real phrases need speaker review; there is a file ready for them."],
  ["Where does the message data go? Privacy?",
   "Message text is sent to the AI model API. For production, an NT agency would need approved hosting, redaction of personal details and a data agreement. We name this as a next step, not a solved problem."],
  ["How much does it cost to run?",
   "About 25 cents of credit for a brand-new 55-message shift on Sonnet, roughly half a cent a message. Answers are cached, so replaying a shift is free."],
  ["Why both the AI and a small ML model?",
   "A second opinion and a fallback. When they disagree the row says “2nd opinion differs”, so a human looks closer."],
  ["Why so many false alarms?",
   "A deliberate choice. Missing an urgent message is far worse than a person reading one extra. The score we optimise is Urgent caught."],
  ["What is real and what is simulated?",
   "Real: the pipeline, AI calls, safety rules, escalation logic, inbound endpoint (POST /api/ingest). Simulated: the shift clock, the message source, and in-memory storage."],
  ["How does it scale?",
   "One AI call per message, so hundreds a day is fine. Production needs a database instead of memory, and a real inbox or SMS feed."],
];
