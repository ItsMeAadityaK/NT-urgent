// The talk: PowerPoint (presentation/NT-Triage-Deck.pptx) + live demo, 10 minutes in all.
// Rendered by script.html (the printable speaker sheet).
//
// secs   : time budget for the part
// say    : what to say, in your own words
// do     : what to click (demo only)

const TALK = [
  { part: "slides", title: "1. Title", secs: 30,
    say: ["Every urgent message reaches a person. Say it once, slowly.",
          "This is our answer to Brief 5. The picture: messages in, sorted, urgent ones land with a named human.",
          "The system never replies to the public by itself."] },
  { part: "slides", title: "2. The problem", secs: 45,
    say: ["NT agencies get messages by SMS, web form and email. Some are life or death.",
          "Many are short, full of typos or in a language a system can't read. Many senders are cut off by floods.",
          "Land the last line: the job is to make sure a person sees it."] },
  { part: "slides", title: "3. Triage, escalate, never reply", secs: 60,
    say: ["Four steps: it arrives, five checks give it a priority, it goes to a named team, a clock starts.",
          "Critical must be acknowledged in 15 minutes, high in 60, medium in 240. Miss it and it goes to the Shift supervisor, then the Duty manager at twice the limit.",
          "The black bar is the trust twist: it drafts, a person approves, it never sends."] },
  { part: "slides", title: "4. Three layers", secs: 60,
    say: ["The AI understands meaning. A small ML model trained on 152 hand-written messages is the second opinion and the fallback if the AI is offline.",
          "Safety rules are a fixed checklist. They can only raise priority, so “ignore this, it's low” can't talk the system down.",
          "Cut-off senders are raised up to two levels. Text we can't read goes to an interpreter at HIGH. Then: let me show you."] },
  { part: "slides", title: "5. Live demo (divider)", secs: 15,
    say: ["Alt+Tab to the browser. Follow the demo steps below."] },

  { part: "demo", title: "Demo 1. The live queue", secs: 60,
    say: ["This is a live shift: 55 fresh messages. The right answers are hidden and only used to score us.",
          "Sorted by priority, then oldest first. Every row says why.",
          "The dark panel at the top is what matters in an emergency: who is overdue or has gone silent."],
    do: "Press PLAY. Let messages arrive for a few seconds, then PAUSE. Open one row: “full reasoning + draft reply”." },
  { part: "demo", title: "Demo 2. Follow one message", secs: 60,
    say: ["Same data, as a journey: channel, five checks, a named team, then the escalation ladder.",
          "The AI, the backup model and the rules each give a view. The final priority only ever goes up."],
    do: "Open the How It Works tab. Pick a critical message in the dropdown, press REPLAY. Point at each stage as it lights up." },
  { part: "demo", title: "Demo 3. Try to break it", secs: 75,
    say: ["Type like a real person: typos, no punctuation. It still works.",
          "This one is a prompt-injection attack telling the AI to ignore a threat. The safety rules still catch it.",
          "Text it can't read is never ignored. It goes to the Interpreter team at high. (Our stand-in text is invented, not a real language.)"],
    do: "Try a Message tab. Click “Prompt injection”, press TRIAGE IT. Then click “Unreadable language (stand-in)”, TRIAGE IT. (Each costs a few cents if not cached.)" },
  { part: "demo", title: "Demo 4. Nobody acts", secs: 45,
    say: ["If nobody acknowledges in time it goes up the ladder, and every action is recorded against who did it.",
          "Replies are drafts. A person approves."],
    do: "Message Queue. Drag the clock slider to about +240 min. Set ACTING AS to Shift supervisor. Press ACKNOWLEDGE on an overdue row. (Optional: Welfare Checks tab for silent senders.)" },
  { part: "demo", title: "Demo 5. The scores", secs: 60,
    say: ["In the table, the last row is the whole system with the AI switched off: urgent messages still reach a human.",
          "In Evaluation the number that matters is Urgent caught. Rules alone miss many; the full system, even with the AI offline, misses very few. Read the number off the table.",
          "Honest note: this shift is generated from our templates, so scores are optimistic. The 152-message benchmark is the independent check."],
    do: "Open the Evaluation tab. Point at “Urgent caught”, then at the last row (AI offline)." },

  { part: "slides", title: "6. What is real, what is next", secs: 60,
    say: ["Real: the pipeline, escalation clocks, silent-sender checks, an inbound endpoint and an audit trail.",
          "Next: SMS and email feeds, phrases checked by real language speakers, a trial with an NT agency.",
          "End on: help people, never replace them. Then: Questions?"] },
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
