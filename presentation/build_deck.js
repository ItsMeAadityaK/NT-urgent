// Builds NT-Triage-Deck.pptx (pptxgenjs). Animations, transitions and navigation links are added afterwards by
// polish_deck.ps1 (PowerPoint itself), using the plan this script writes to animations.json.
//
//   set NODE_PATH to a folder containing pptxgenjs, react, react-dom, react-icons, sharp, then:
//   node presentation/build_deck.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const HERE = __dirname;
const R = JSON.parse(fs.readFileSync(path.join(HERE, "..", "report", "results_after.json"), "utf8"));
const B = R.benchmark.rows;

// ---------------------------------------------------------------- palette and type
const INK = "0E1116", PANEL = "161B23", RAISED = "1C222C", BORDER = "2A323E";
const TEXT = "F3EFE6", MUTED = "9AA1AD", DIM = "6C7480";
const ACCENT = "E0561A", TEAL = "17A5A3", AMBER = "F2B84B";
const CRIT = "E03A52", HIGH = "F0702C", MED = "D1A21E", LOW = "36B26B";
const HEAD = "Calibri", MONO = "Consolas";

const ANIM = {}; // slide number -> list of effects, written to animations.json
function anim(n, name, effect, trigger = "after", delay = 0, dur = 0.5) {
  (ANIM[n] = ANIM[n] || []).push({ name, effect, trigger, delay, dur });
}

async function icon(Comp, color = "#FFFFFF") {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color, size: 256 }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
  pres.title = "NT Correspondence Triage";
  pres.author = "Team AIC023";

  const TOTAL = 7;
  let n = 0;

  // ---------------------------------------------------------------- helpers
  const text = (s, t, o) => s.addText(t, { fontFace: HEAD, color: TEXT, margin: 0, isTextBox: true, valign: "top", ...o });
  const mono = (s, t, o) => text(s, t, { fontFace: MONO, ...o });
  const card = (s, x, y, w, h, o = {}) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: o.fill || PANEL }, line: { color: o.line || BORDER, width: o.lw || 1 }, objectName: o.name });
  const dot = (s, x, y, d, color, name) => s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color }, objectName: name });
  const badge = async (s, x, y, d, fill, Icon, name) => {
    dot(s, x, y, d, fill, name + " badge");
    const pad = d * 0.26;
    s.addImage({ data: await icon(Icon), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, altText: name, objectName: name + " icon" });
  };

  function frame(s, idx, hidden = false) {
    s.background = { color: INK };
    mono(s, "NT CORRESPONDENCE TRIAGE", { x: 0.6, y: 5.18, w: 3.4, h: 0.22, fontSize: 10, color: DIM, charSpacing: 2, objectName: "Footer label" });
    if (hidden) {
      mono(s, "BACKUP", { x: 8.4, y: 5.18, w: 1.0, h: 0.22, fontSize: 10, color: AMBER, align: "right", charSpacing: 2, objectName: "Backup tag" });
      return;
    }
    for (let i = 1; i <= TOTAL; i++) {
      const d = 0.12;
      s.addShape(pres.shapes.OVAL, {
        x: 9.4 - (TOTAL - i + 1) * 0.22 + 0.1, y: 5.23, w: d, h: d,
        fill: { color: i === idx ? ACCENT : BORDER }, line: { color: i === idx ? ACCENT : BORDER },
        objectName: `Nav ${i}`,
      });
    }
  }

  // ================================================================ 1. HOOK
  {
    const s = pres.addSlide(); n = 1; frame(s, n);
    mono(s, "CODE FAIR 2026  ·  AI CHALLENGE 5", { x: 0.6, y: 0.55, w: 4.4, h: 0.25, fontSize: 10, color: ACCENT, bold: true, charSpacing: 2, objectName: "Kicker" });
    text(s, "Every urgent message reaches a person.", { x: 0.6, y: 1.0, w: 4.2, h: 2.2, fontSize: 40, bold: true, objectName: "Title" });
    text(s, "NT Correspondence Triage. It sorts, routes and explains every message, and it never replies by itself.", { x: 0.6, y: 3.3, w: 3.9, h: 1.0, fontSize: 16, color: MUTED, objectName: "Subtitle" });
    mono(s, "TEAM AIC023", { x: 0.6, y: 4.7, w: 2.5, h: 0.22, fontSize: 10, color: DIM, charSpacing: 2, objectName: "Team" });

    card(s, 5.05, 0.5, 4.4, 4.45, { name: "Inbox panel" });
    mono(s, "INBOX  ·  06:41  ·  43 UNREAD", { x: 5.25, y: 0.66, w: 3.8, h: 0.22, fontSize: 10, color: MUTED, charSpacing: 1, objectName: "Inbox header" });
    const rows = [
      ["06:12", "can i get a receipt for my application"], ["06:15", "bin day changed after the storm?"],
      ["06:19", "update the address on my account"], ["06:24", "thanks for the quick reply last week"],
      ["06:26", "opening hours over Easter?"], ["06:28", "my mum collapsed and is not responding"],
      ["06:31", "street light out near the bus stop"], ["06:36", "renewal form: which box do I tick"],
      ["06:38", "how do i sign up for the training course"],
    ];
    rows.forEach(([t, m], i) => {
      const y = 1.02 + i * 0.4, hot = i === 5;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 5.2, y, w: 4.1, h: 0.34, rectRadius: 0.06, fill: { color: hot ? "3A1822" : RAISED }, line: { color: hot ? CRIT : BORDER, width: hot ? 1.5 : 0.75 },
        objectName: `Inbox row ${i + 1}`,
      });
      mono(s, t, { x: 5.3, y: y + 0.07, w: 0.55, h: 0.2, fontSize: 10, color: hot ? "FF8A99" : DIM, objectName: `Inbox time ${i + 1}` });
      text(s, m, { x: 5.9, y: y + 0.05, w: 3.35, h: 0.25, fontSize: 12, color: hot ? "FFFFFF" : MUTED, bold: hot, fit: "shrink", objectName: `Inbox text ${i + 1}` });
      anim(1, `Inbox row ${i + 1}`, "fade", "after", 0, 0.25);
      anim(1, `Inbox time ${i + 1}`, "fade", "with", 0, 0.25);
      anim(1, `Inbox text ${i + 1}`, "fade", "with", 0, 0.25);
    });
    text(s, "One of these is an emergency.", { x: 5.25, y: 4.6, w: 3.9, h: 0.28, fontSize: 14, bold: true, color: AMBER, objectName: "Inbox callout" });
    anim(1, "Inbox row 6", "pulse", "after", 0.3, 0.8);
    anim(1, "Inbox callout", "fade", "after", 0.1, 0.5);
    s.addNotes("HOOK, about 35 seconds.\nLet the inbox build by itself. Say: this is a normal morning in a government correspondence inbox. Bin days, receipts, thank-yous. And one of these is a woman telling us her mum has collapsed and the road is flooded.\nThen the line: our system exists so that message is never the 43rd thing someone reads.\nOne rule to plant now: it never replies by itself. It makes sure a named person sees the urgent ones, and chases them if they do nothing.");
  }

  // ================================================================ 2. NT PROBLEM
  {
    const s = pres.addSlide(); n = 2; frame(s, n);
    mono(s, "THE NORTHERN TERRITORY, WET SEASON", { x: 0.6, y: 0.55, w: 4.0, h: 0.25, fontSize: 10, color: ACCENT, bold: true, charSpacing: 2, objectName: "Kicker" });
    text(s, "A short message, from a phone with one bar of signal.", { x: 0.6, y: 0.95, w: 3.9, h: 1.7, fontSize: 30, bold: true, objectName: "Title" });
    text(s, "From October to April the monsoon can cut roads and take out phone towers. In March 2024 it did both at Borroloola, and mobile coverage across the area went down.", { x: 0.6, y: 2.85, w: 3.8, h: 1.5, fontSize: 14, color: MUTED, objectName: "Context" });
    mono(s, "Sources: ABS, RMIT / ADM+S, AAP", { x: 0.6, y: 4.7, w: 4.0, h: 0.2, fontSize: 10, color: DIM, objectName: "Sources" });
    const stats = [
      ["58.5%", "of First Nations people speak an Indigenous language at home", "ABS, 2021 Census", ACCENT],
      ["43%", "of First Nations communities and homelands have no mobile service", "RMIT / ADM+S, 2023", TEAL],
      ["3 in 4", "First Nations people in remote communities are digitally excluded", "RMIT / ADM+S, 2025", AMBER],
      ["4.4×", "the national rate of assault victims (4,057 vs 917 per 100,000)", "ABS, 2025", CRIT],
    ];
    stats.forEach(([big, label, src, col], i) => {
      const x = 4.75 + (i % 2) * 2.4, y = 0.5 + Math.floor(i / 2) * 2.25;
      card(s, x, y, 2.25, 2.1, { name: `Stat card ${i + 1}` });
      text(s, big, { x: x + 0.18, y: y + 0.14, w: 1.95, h: 0.7, fontSize: 38, bold: true, color: col, objectName: `Stat number ${i + 1}` });
      text(s, label, { x: x + 0.18, y: y + 0.88, w: 1.95, h: 0.85, fontSize: 12.5, color: TEXT, objectName: `Stat label ${i + 1}` });
      mono(s, src, { x: x + 0.18, y: y + 1.78, w: 1.95, h: 0.2, fontSize: 10, color: DIM, objectName: `Stat source ${i + 1}` });
      ["card", "number", "label", "source"].forEach((k, j) => {
        const nm = k === "card" ? `Stat card ${i + 1}` : `Stat ${k} ${i + 1}`;
        anim(2, nm, "fade", j === 0 ? "after" : "with", j === 0 ? 0.25 : 0, 0.5);
      });
    });
    s.addNotes("THE PROBLEM, about 50 seconds.\nThree facts, not a lecture. 58.5% of First Nations people in the NT speak an Indigenous language at home, the highest share in Australia. 43% of First Nations communities and homelands have no mobile service. In 2025 the NT recorded 4,057 assault victims per 100,000 people against 917 nationally, two thirds family and domestic violence.\nSo the person we built for writes briefly, on a phone, maybe not in English, maybe with the road under water, and may not write twice.\nSources are on the slide and in the report.");
  }

  // ================================================================ 3. THE ANSWER
  {
    const s = pres.addSlide(); n = 3; frame(s, n);
    text(s, [{ text: "Triage. Escalate. ", options: { color: TEXT } }, { text: "Never reply.", options: { color: ACCENT } }],
      { x: 0.6, y: 0.5, w: 8.8, h: 0.8, fontSize: 38, bold: true, objectName: "Title" });
    const nodes = [
      [fa.FaEnvelope, "Message arrives", "SMS, web form, email or phone notes", MUTED],
      [fa.FaProjectDiagram, "Three readers", "AI model, backup ML model, safety rules", ACCENT],
      [fa.FaLevelUpAlt, "Priority only rises", "Floors and access can raise it, never lower it", TEAL],
      [fa.FaUserCheck, "A named person", "Right team, Duty Officer copied on critical", LOW],
      [fa.FaClock, "A clock runs", "15, 60 or 240 minutes, then it escalates", CRIT],
    ];
    for (let i = 0; i < nodes.length; i++) {
      const [Ic, h, c, col] = nodes[i];
      const cx = 1.15 + i * 1.9;
      await badge(s, cx - 0.4, 1.75, 0.8, col, Ic, `Node ${i + 1}`);
      text(s, h, { x: cx - 0.85, y: 2.72, w: 1.7, h: 0.3, fontSize: 15, bold: true, align: "center", objectName: `Node ${i + 1} title` });
      text(s, c, { x: cx - 0.85, y: 3.05, w: 1.7, h: 0.8, fontSize: 12, color: MUTED, align: "center", objectName: `Node ${i + 1} text` });
      if (i < nodes.length - 1) {
        s.addShape(pres.shapes.LINE, { x: cx + 0.5, y: 2.15, w: 0.9, h: 0, line: { color: BORDER, width: 2, endArrowType: "triangle" }, objectName: `Arrow ${i + 1}` });
      }
      ["badge", "icon"].forEach((k, j) => anim(3, `Node ${i + 1} ${k}`, j === 0 ? "zoom" : "fade", j === 0 ? "after" : "with", j === 0 ? 0.15 : 0, 0.45));
      anim(3, `Node ${i + 1} title`, "fade", "with", 0.1, 0.4);
      anim(3, `Node ${i + 1} text`, "fade", "with", 0.15, 0.4);
      if (i < nodes.length - 1) anim(3, `Arrow ${i + 1}`, "wipe", "with", 0.25, 0.4);
    }
    card(s, 0.6, 4.05, 8.8, 0.78, { fill: "1F1710", line: ACCENT, name: "Rule banner" });
    text(s, [
      { text: "The system drafts. A person approves. It ", options: { color: TEXT } },
      { text: "never", options: { color: AMBER, bold: true } },
      { text: " sends anything to the public.", options: { color: TEXT } },
    ], { x: 0.85, y: 4.05, w: 8.3, h: 0.78, fontSize: 17, bold: true, valign: "middle", objectName: "Rule text" });
    anim(3, "Rule banner", "fade", "after", 0.2, 0.5);
    anim(3, "Rule text", "fade", "with", 0, 0.5);
    s.addNotes("THE ANSWER, about 45 seconds.\nThe brief's trust twist is the whole design: the system escalates, it never replies. Walk the flow left to right as it builds itself: a message arrives; three readers judge it; the priority can only go up; it lands with a named person; a clock starts, 15 minutes for critical. If nobody acknowledges it, it climbs to the shift supervisor, then the duty manager.\nLand the banner: it drafts, a person approves, it never sends.");
  }

  // ================================================================ 4. THREE READERS
  {
    const s = pres.addSlide(); n = 4; frame(s, n);
    text(s, "Three readers. None can lower a priority.", { x: 0.6, y: 0.5, w: 8.8, h: 0.7, fontSize: 32, bold: true, objectName: "Title" });
    const layers = [
      [fa.FaCommentDots, ACCENT, "The AI model", "Reads the meaning. Typos and slang don't lower urgency. Treats every message as data, not orders."],
      [fa.FaChartBar, TEAL, "The backup ML model", "Trained on our data. Runs with no network, and its disagreement is a warning."],
      [fa.FaShieldAlt, "5B6472", "The safety rules", "61 fixed patterns, from \"hurt me\" to \"not breathing\". They ignore instructions in the text."],
    ];
    for (let i = 0; i < 3; i++) {
      const [Ic, col, h, c] = layers[i];
      const y = 1.45 + i * 1.12;
      card(s, 0.6, y, 5.25, 0.98, { name: `Layer ${i + 1}` });
      await badge(s, 0.78, y + 0.19, 0.6, col, Ic, `Layer ${i + 1}`);
      text(s, h, { x: 1.58, y: y + 0.12, w: 4.1, h: 0.3, fontSize: 16, bold: true, objectName: `Layer ${i + 1} title` });
      text(s, c, { x: 1.58, y: y + 0.45, w: 4.1, h: 0.5, fontSize: 12, color: MUTED, objectName: `Layer ${i + 1} text` });
      ["", " badge", " icon", " title", " text"].forEach((k, j) => anim(4, `Layer ${i + 1}${k}`, "fade", j === 0 ? "after" : "with", j === 0 ? 0.2 : 0.05, 0.45));
    }
    // priority ladder
    const lad = [["CRITICAL", CRIT], ["HIGH", HIGH], ["MEDIUM", MED], ["LOW", LOW]];
    mono(s, "PRIORITY", { x: 6.35, y: 1.2, w: 1.7, h: 0.22, fontSize: 10, color: MUTED, charSpacing: 2, objectName: "Ladder label" });
    lad.forEach(([lab, col], i) => {
      const y = 1.5 + i * 0.7;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.35, y, w: 1.7, h: 0.58, rectRadius: 0.08, fill: { color: col }, line: { color: col }, objectName: `Ladder ${lab}` });
      mono(s, lab, { x: 6.35, y, w: 1.7, h: 0.58, fontSize: 13, bold: true, align: "center", valign: "middle", color: "FFFFFF", charSpacing: 2, objectName: `Ladder ${lab} text` });
    });
    [3, 2, 1, 0].forEach((idx, j) => {
      anim(4, `Ladder ${lad[idx][0]}`, "wipe", j === 0 ? "after" : "with", j * 0.25 + (j === 0 ? 0.3 : 0), 0.4);
      anim(4, `Ladder ${lad[idx][0]} text`, "fade", "with", j * 0.25 + (j === 0 ? 0.3 : 0), 0.4);
    });
    s.addShape(pres.shapes.LINE, { x: 6.18, y: 1.6, w: 0, h: 2.55, flipV: true, line: { color: AMBER, width: 2.25, endArrowType: "triangle" }, objectName: "Raise arrow" });
    anim(4, "Raise arrow", "wipe", "after", 0.1, 0.8);
    text(s, "+2 levels for senders cut off by floods", { x: 8.2, y: 1.55, w: 1.3, h: 1.0, fontSize: 12, color: AMBER, bold: true, objectName: "Chip cut-off" });
    text(s, "Text we can't read: at least HIGH, to an interpreter", { x: 8.2, y: 2.95, w: 1.3, h: 1.3, fontSize: 12, color: AMBER, bold: true, objectName: "Chip language" });
    anim(4, "Chip cut-off", "fade", "after", 0.1, 0.5);
    anim(4, "Chip language", "fade", "after", 0.1, 0.5);
    s.addNotes("THE READERS, about 50 seconds.\nThree independent readers so no single failure hides an emergency. The AI model understands meaning (this runs on the Claude API). A small ML model we trained is the second opinion and works with no network. Fixed safety rules are a checklist that can't be talked out of a threat, and they ignore instructions inside a message.\nNone of them can lower a priority. Two more things: senders cut off by floods are raised two levels, and text we can't read is never ignored: it goes to an interpreter at HIGH.");
  }

  // ================================================================ 5. RESULTS
  {
    const s = pres.addSlide(); n = 5; frame(s, n);
    text(s, "Does it work?", { x: 0.6, y: 0.5, w: 5, h: 0.7, fontSize: 34, bold: true, objectName: "Title" });
    mono(s, "152 HAND-WRITTEN MESSAGES  ·  REAL AI VERDICTS  ·  55 TRULY URGENT", { x: 0.6, y: 1.15, w: 6, h: 0.22, fontSize: 10, color: MUTED, charSpacing: 1, objectName: "Subtitle" });
    const vals = [B.baseline.urgent_recall, B.rules.urgent_recall, B.ai.urgent_recall, B.full.urgent_recall, B.full_outage.urgent_recall].map((v) => Math.round(v * 1000) / 10);
    s.addChart(pres.charts.BAR, [{ name: "Urgent messages caught", labels: ["Backup model alone", "Safety rules alone", "AI model alone", "Full system", "Full system, AI off"], values: vals }], {
      x: 0.5, y: 1.5, w: 5.5, h: 3.2, barDir: "bar", chartColors: ["C0495A", "C0495A", MED, LOW, LOW], showValue: true, dataLabelColor: TEXT, dataLabelFontSize: 12, dataLabelFontBold: true,
      dataLabelFormatCode: '0.0"%"', dataLabelPosition: "outEnd", valAxisMinVal: 0, valAxisMaxVal: 110, valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
      catAxisLabelColor: TEXT, catAxisLabelFontSize: 12, catAxisLabelFontFace: HEAD, catAxisOrientation: "maxMin", showLegend: false, showTitle: true, title: "Urgent messages caught",
      titleColor: MUTED, titleFontSize: 11, titleFontFace: HEAD, barGapWidthPct: 45, plotArea: { fill: { color: INK } }, objectName: "Results chart",
    });
    anim(5, "Results chart", "wipe", "after", 0.3, 0.9);
    const big = [
      [`${Math.round(B.full.urgent_recall * 55)} / 55`, "urgent messages caught", LOW],
      [`${Math.round(B.full.critical_recall * 23)} / 23`, "critical messages on the 15-minute clock", LOW],
      [`${B.full.false_urgent} / 97`, "routine messages escalated: the price of safety", AMBER],
    ];
    big.forEach(([num, lab, col], i) => {
      const y = 1.45 + i * 1.13;
      card(s, 6.3, y, 3.2, 0.98, { name: `Big card ${i + 1}` });
      text(s, num, { x: 6.5, y: y + 0.1, w: 1.55, h: 0.75, fontSize: 28, bold: true, color: col, valign: "middle", objectName: `Big number ${i + 1}` });
      text(s, lab, { x: 8.05, y: y + 0.1, w: 1.35, h: 0.78, fontSize: 11.5, color: MUTED, valign: "middle", objectName: `Big label ${i + 1}` });
      ["Big card", "Big number", "Big label"].forEach((k, j) => anim(5, `${k} ${i + 1}`, "fade", j === 0 ? "after" : "with", j === 0 ? 0.3 : 0, 0.5));
    });
    text(s, "Synthetic data that we wrote. Real-world scores will be lower.", { x: 0.6, y: 4.78, w: 6.5, h: 0.25, fontSize: 12, color: DIM, italic: true, objectName: "Honest note" });
    anim(5, "Honest note", "fade", "after", 0.3, 0.5);
    s.addNotes("RESULTS, about 55 seconds.\nThe chart is urgent messages caught, out of the 55 that are truly high or critical. The backup model alone catches 85% and only half the critical ones. The safety rules alone, 65%. The AI model alone is the best single reader at 94.5%. Together: 54 of 55, and all 23 critical messages on the 15-minute clock. Switch the AI off and it is still 98%.\nBe honest about the price: 10 of 97 routine messages get escalated, and we wrote this data ourselves, so real scores will be lower. That is why the report recommends a shadow pilot.\nNumbers come straight from the running system: report/collect_results.py.");
  }

  // ================================================================ 6. DEMO
  {
    const s = pres.addSlide(); n = 6; frame(s, n);
    text(s, "Live demo", { x: 0.6, y: 0.45, w: 4.5, h: 0.9, fontSize: 46, bold: true, objectName: "Title" });
    mono(s, "ABOUT 4½ MINUTES  ·  CLICK A STEP TO OPEN IT", { x: 0.6, y: 1.3, w: 4.6, h: 0.22, fontSize: 10, color: AMBER, charSpacing: 1, objectName: "Subtitle" });
    const steps = [
      ["The live queue, and who needs a human now", "queue"],
      ["Follow one message through the checks", "journey"],
      ["Try to break it: injection, unreadable text", "try"],
      ["Nobody acts, so it escalates", "queue"],
      ["The scores, even with the AI off", "compare"],
    ];
    steps.forEach(([t, view], i) => {
      const y = 1.85 + i * 0.58;
      card(s, 0.6, y, 4.55, 0.48, { name: `Step ${i + 1}` });
      dot(s, 0.72, y + 0.09, 0.3, i === 0 ? ACCENT : RAISED, `Step ${i + 1} dot`);
      mono(s, String(i + 1), { x: 0.72, y: y + 0.09, w: 0.3, h: 0.3, fontSize: 12, bold: true, align: "center", valign: "middle", objectName: `Step ${i + 1} number` });
      text(s, t, { x: 1.18, y: y + 0.02, w: 3.9, h: 0.44, fontSize: 13, valign: "middle", objectName: `Step ${i + 1} text` });
      ["", " dot", " number", " text"].forEach((k, j) => anim(6, `Step ${i + 1}${k}`, "fade", j === 0 ? "after" : "with", j === 0 ? 0.15 : 0, 0.4));
    });
    s.addImage({ path: path.join(HERE, "assets", "console_preview.gif"), x: 5.45, y: 0.55, w: 4.05, h: 4.05 * 764 / 1100, altText: "Animated preview of the console", objectName: "Console preview" });
    card(s, 5.45, 3.75, 4.05, 0.62, { fill: ACCENT, line: ACCENT, name: "Open button" });
    text(s, "OPEN THE CONSOLE  ▶", { x: 5.45, y: 3.75, w: 4.05, h: 0.62, fontSize: 18, bold: true, align: "center", valign: "middle", objectName: "Open button text" });
    mono(s, "127.0.0.1:5050  ·  seed 2026  ·  no AI credit used", { x: 5.45, y: 4.5, w: 4.05, h: 0.22, fontSize: 10, color: DIM, align: "center", objectName: "Console address" });
    anim(6, "Console preview", "fade", "after", 0.2, 0.6);
    anim(6, "Open button", "fade", "after", 0.1, 0.4);
    anim(6, "Open button text", "fade", "with", 0, 0.4);
    s.addNotes("DEMO, about 4 minutes 30 seconds. Click OPEN THE CONSOLE (or Alt+Tab to the browser, already open on http://127.0.0.1:5050).\n\n1. LIVE QUEUE (60s): press PLAY, let messages arrive, then pause. Point at the dark panel: it only shows what is overdue or silent. Open one row: full reasoning and draft reply.\n2. HOW IT WORKS tab (60s): pick a critical message, press REPLAY. Channel, then six checks, then the named team and the escalation ladder.\n3. TRY A MESSAGE (75s): click 'Prompt injection', TRIAGE IT: still critical. Then 'Unreadable language (stand-in)': goes to the interpreter desk at HIGH. Say the stand-in text is invented, not a real language.\n4. ESCALATION (45s): drag the timeline to about +240 min, set ACTING AS to Shift supervisor, ACKNOWLEDGE an overdue row.\n5. EVALUATION (60s): point at the bars, then the AI-off row.\n\nDo NOT press NEW SHIFT on stage (it spends credit). If the site fails, the preview on this slide and the backup slide show the same thing.");
  }

  // ================================================================ 7. CLOSE
  {
    const s = pres.addSlide(); n = 7; frame(s, n);
    text(s, "What is real. What is next. What we won't do.", { x: 0.6, y: 0.5, w: 8.8, h: 0.7, fontSize: 30, bold: true, objectName: "Title" });
    const cols = [
      [fa.FaCheckCircle, LOW, "Real today", "The full pipeline, escalation clocks, silent-sender checks, an inbound endpoint, an audit trail and 97 tests. AI verdicts are real."],
      [fa.FaArrowRight, TEAL, "Next", "A shadow pilot for one wet season. Real SMS and email feeds. Language phrases reviewed by speakers, under community control."],
      [fa.FaBan, CRIT, "Never", "No auto-replies. No lowering a priority. No pretending to understand a language we can't read."],
    ];
    for (let i = 0; i < 3; i++) {
      const [Ic, col, h, c] = cols[i];
      const x = 0.6 + i * 3.0;
      card(s, x, 1.35, 2.8, 2.3, { name: `Column ${i + 1}` });
      await badge(s, x + 0.2, 1.55, 0.55, col, Ic, `Column ${i + 1}`);
      text(s, h, { x: x + 0.2, y: 2.22, w: 2.4, h: 0.35, fontSize: 18, bold: true, objectName: `Column ${i + 1} title` });
      text(s, c, { x: x + 0.2, y: 2.62, w: 2.45, h: 1.0, fontSize: 12, color: MUTED, objectName: `Column ${i + 1} text` });
      ["", " badge", " icon", " title", " text"].forEach((k, j) => anim(7, `Column ${i + 1}${k}`, "fade", j === 0 ? "after" : "with", j === 0 ? 0.2 : 0, 0.45));
    }
    mono(s, "OUR WARNINGS:  SYNTHETIC DATA  ·  30% ON THE CRITICAL CLOCK  ·  ONE MODEL, ENGLISH ONLY", { x: 0.6, y: 3.85, w: 8.8, h: 0.22, fontSize: 10, color: AMBER, charSpacing: 1, objectName: "Warnings" });
    card(s, 0.6, 4.2, 8.8, 0.7, { fill: PANEL, line: BORDER, name: "Closing banner" });
    text(s, "Questions?", { x: 0.9, y: 4.2, w: 3.0, h: 0.7, fontSize: 28, bold: true, valign: "middle", objectName: "Questions" });
    text(s, "Help people. Never replace them.", { x: 4.2, y: 4.2, w: 5.0, h: 0.7, fontSize: 20, bold: true, color: AMBER, align: "right", valign: "middle", objectName: "Principle" });
    anim(7, "Warnings", "fade", "after", 0.2, 0.5);
    anim(7, "Closing banner", "fade", "after", 0.2, 0.5);
    anim(7, "Questions", "fade", "with", 0, 0.5);
    anim(7, "Principle", "fade", "with", 0.2, 0.5);
    s.addNotes("CLOSE, about 50 seconds.\nBe straight about what is real: the pipeline, the clocks, the silent-sender check, the audit trail and the real AI verdicts. Next: a shadow pilot for one wet season, real SMS and email feeds, and language phrases reviewed by speakers and held under community control. Never: auto-replies, lowering a priority, pretending to understand a language we can't read.\nOur own warnings are on the slide: synthetic data, 30% of messages reach the critical clock because of the access boost, one model, English only.\nEnd on: help people, never replace them. Then Questions. Backup slides follow if asked (they are hidden).");
  }

  // ================================================================ BACKUP A: demo fallback
  {
    const s = pres.addSlide(); frame(s, 0, true); n = 8;
    text(s, "If the live demo fails", { x: 0.6, y: 0.45, w: 8, h: 0.6, fontSize: 30, bold: true, objectName: "Title" });
    mono(s, "THE SAME CONSOLE, PLAYING A SHIFT FROM 06:45 TO 10:30 (SEED 2026)", { x: 0.6, y: 1.05, w: 8, h: 0.22, fontSize: 10, color: MUTED, charSpacing: 1, objectName: "Subtitle" });
    const w = 5.2;
    s.addImage({ path: path.join(HERE, "assets", "console_preview.gif"), x: (10 - w) / 2, y: 1.5, w, h: w * 764 / 1100, altText: "Animated preview of the console", objectName: "Console preview" });
    s.addNotes("BACKUP: only if the website will not start. Talk over the loop: the timeline moves, messages arrive, the dark panel fills with what is overdue, escalation climbs to the duty manager.");
  }

  // ================================================================ BACKUP B: fairness, language, floor
  {
    const s = pres.addSlide(); frame(s, 0, true); n = 9;
    text(s, "Fairness, language, and the second-opinion floor", { x: 0.6, y: 0.45, w: 8.8, h: 0.6, fontSize: 28, bold: true, objectName: "Title" });
    const tiles = [
      ["4 of 5", "fairness pairs got the same final priority (AI model 4, backup model 3). The exception: formal wording made the backup model nervous.", TEAL],
      ["8 → 0", "urgent messages buried in unreadable text, after the readability check. The price: all 8 routine ones were raised to high too.", LOW],
      ["94.5% → 98.2%", "urgent recall after the second-opinion floor. The price: routine messages escalated went from 1 to 10 of 97.", AMBER],
    ];
    tiles.forEach(([big, txt, col], i) => {
      const x = 0.6 + i * 3.0;
      card(s, x, 1.4, 2.8, 3.0, { name: `Tile ${i + 1}` });
      text(s, big, { x: x + 0.2, y: 1.6, w: 2.4, h: 0.7, fontSize: i === 2 ? 24 : 34, bold: true, color: col, objectName: `Tile ${i + 1} number` });
      text(s, txt, { x: x + 0.2, y: 2.45, w: 2.4, h: 1.8, fontSize: 13, color: MUTED, objectName: `Tile ${i + 1} text` });
    });
    s.addNotes("BACKUP: use if asked about fairness, language, or why the system escalates some routine messages. Full tables are in the report (sections 3.2, 3.4, 3.5).");
  }

  // ================================================================ BACKUP C: likely questions
  {
    const s = pres.addSlide(); frame(s, 0, true); n = 10;
    text(s, "Questions we expect", { x: 0.6, y: 0.45, w: 8, h: 0.6, fontSize: 30, bold: true, objectName: "Title" });
    const qa = [
      ["Is the data real?", "No. We wrote it, so scores are optimistic. The pipeline and the AI verdicts are real."],
      ["What if the AI is down?", "Backup model and rules take over: still 98% of urgent messages."],
      ["Can someone trick it?", "The rules ignore instructions in the text, and priorities only go up."],
      ["Does it reply?", "Never. It drafts; a person approves. A test checks nothing can send."],
      ["Aboriginal languages?", "We invent none. Unreadable text goes to an interpreter at HIGH."],
      ["Privacy?", "Needs a privacy impact assessment and Australian hosting before any real message."],
    ];
    qa.forEach(([q, a], i) => {
      const x = 0.6 + (i % 2) * 4.5, y = 1.3 + Math.floor(i / 2) * 1.2;
      card(s, x, y, 4.3, 1.05, { name: `QA ${i + 1}` });
      text(s, q, { x: x + 0.2, y: y + 0.1, w: 3.9, h: 0.3, fontSize: 14, bold: true, color: AMBER, objectName: `QA ${i + 1} question` });
      text(s, a, { x: x + 0.2, y: y + 0.42, w: 3.9, h: 0.6, fontSize: 12.5, color: MUTED, objectName: `QA ${i + 1} answer` });
    });
    s.addNotes("BACKUP: six likely questions with one-line answers. The report's Appendix and /script.html have more.");
  }

  await pres.writeFile({ fileName: path.join(HERE, "NT-Triage-Deck.raw.pptx") });
  fs.writeFileSync(path.join(HERE, "animations.json"), JSON.stringify(ANIM, null, 1));
  console.log("built");
})();
