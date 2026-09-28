const URGENCY_COLOR = {
  critical: "#C1272D",
  high: "#C97A2B",
  medium: "#A69422",
  low: "#3D6B63",
};
const URGENCY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

// Schematic (not-to-scale) positions within the 500x900 map viewBox,
// arranged to loosely suggest real NT geography: Top End communities
// (monsoon-affected, where the flood/storm messages concentrate) up top,
// Barkly in the middle, Central Australia towns (unaffected by this
// particular weather event) toward the bottom.
const LOCATIONS = {
  "Darwin": { x: 290, y: 35 },
  "Palmerston": { x: 320, y: 75 },
  "Humpty Doo": { x: 350, y: 115 },
  "Batchelor": { x: 240, y: 130 },
  "Jabiru": { x: 415, y: 85 },
  "Daly River area": { x: 165, y: 175 },
  "Peppimenarti": { x: 105, y: 210 },
  "Wadeye": { x: 55, y: 240 },
  "Maningrida": { x: 445, y: 145 },
  "Nhulunbuy": { x: 485, y: 185 },
  "Katherine": { x: 290, y: 260 },
  "Ngukurr": { x: 410, y: 300 },
  "Borroloola": { x: 440, y: 340 },
  "Elliott": { x: 270, y: 430 },
  "Tennant Creek": { x: 280, y: 500 },
  "Yuendumu": { x: 190, y: 690 },
  "Alice Springs": { x: 275, y: 780 },
};

const state = {
  minutes: 30,
  view: "queue",
  playing: false,
  playTimer: null,
  expanded: new Set(),
  activePin: null,
  messages: [],
  fairnessPairs: [],
  baselineEval: null,
};

const el = (id) => document.getElementById(id);

function fmtTime(iso) {
  const d = new Date(iso);
  return d.toISOString().slice(11, 16);
}
function fmtDate(iso) {
  const d = new Date(iso);
  return d.toUTCString().slice(5, 11) + " " + d.getUTCFullYear();
}

async function fetchState(minutes) {
  const res = await fetch(`/api/state?minutes=${minutes}`);
  const data = await res.json();
  applyState(data);
}

async function acknowledge(messageId) {
  const res = await fetch("/api/acknowledge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id: messageId, minutes: state.minutes }),
  });
  const data = await res.json();
  applyState(data);
}

async function resetAcks() {
  const res = await fetch("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ minutes: state.minutes }),
  });
  const data = await res.json();
  applyState(data);
}

function applyState(data) {
  state.messages = data.messages;
  state.fairnessPairs = data.fairness_pairs || [];
  state.baselineEval = data.baseline_eval || null;
  el("clockValue").textContent = fmtTime(data.current_time);
  el("clockDate").textContent = fmtDate(data.current_time);
  render();
}

function render() {
  renderStats();
  if (state.view === "queue") renderQueue();
  if (state.view === "map") renderMap();
  if (state.view === "compare") renderCompare();
  if (state.view === "fairness") renderFairness();
}

// ---------- Stats ----------
function renderStats() {
  const msgs = state.messages;
  const critical = msgs.filter((m) => m.access_adjusted_priority === "critical").length;
  const escalate = msgs.filter((m) => m.should_escalate).length;
  const dropout = msgs.filter((m) => m.dropout_flag).length;
  const disagree = msgs.filter((m) => m.llm_urgency !== m.baseline_urgency).length;

  const tiles = [
    { label: "ITEMS IN QUEUE", value: msgs.length, color: "var(--accent)" },
    { label: "CRITICAL", value: critical, color: "var(--critical)" },
    { label: "ESCALATE NOW", value: escalate, color: "var(--high)" },
    { label: "DROPOUT RISK", value: dropout, color: "var(--medium)" },
    { label: "LLM/BASELINE DISAGREE", value: disagree, color: "var(--low)" },
  ];

  el("statRow").innerHTML = tiles
    .map(
      (t) => `
    <div class="stat-tile" style="--stat-color:${t.color}">
      <div class="num">${t.value}</div>
      <div class="lbl">${t.label}</div>
    </div>`
    )
    .join("");
}

// ---------- Queue ----------
function renderQueue() {
  el("queueMeta").textContent = `${state.messages.length} ITEMS IN QUEUE`;
  const list = el("queueList");

  if (state.messages.length === 0) {
    list.innerHTML = `<p class="view-note">No messages have arrived yet — advance the clock.</p>`;
    return;
  }

  list.innerHTML = state.messages
    .map((m) => {
      const color = URGENCY_COLOR[m.access_adjusted_priority] || "#9C948A";
      let flags = "";
      if (m.dropout_flag) flags += `<span class="flag-tag">&#128266; DROPOUT RISK</span>`;
      if (m.should_escalate) flags += `<span class="flag-tag flag-escalate">&#9200; ESCALATE NOW</span>`;

      const isOpen = state.expanded.has(m.message_id);
      const ackLabel = m.acknowledged ? "ACKNOWLEDGED" : "ACKNOWLEDGE";

      return `
      <div class="dispatch-row ${m.acknowledged ? "acked" : ""}" style="--row-color:${color}">
        <div class="rowid mono">${m.message_id}</div>
        <div class="rowmeta">${fmtTime(m.timestamp)}<br>${m.channel}<br>${m.location}</div>
        <div>
          <div class="rowtext">&ldquo;${escapeHtml(m.raw_text)}&rdquo;</div>
          <button class="expand-btn" data-toggle="${m.message_id}">${isOpen ? "hide" : "why was this prioritised this way?"}</button>
          <div class="row-detail ${isOpen ? "open" : ""}" id="detail-${m.message_id}">
            <dl>
              <dt>Raw LLM urgency</dt><dd>${m.llm_urgency}</dd>
              <dt>LLM reasoning</dt><dd>${escapeHtml(m.llm_reason)}</dd>
              <dt>Baseline model urgency</dt><dd>${m.baseline_urgency}</dd>
              <dt>Access-adjusted priority</dt><dd>${m.access_adjusted_priority}</dd>
              <dt>Access reasoning</dt><dd>${escapeHtml(m.access_reason)}</dd>
              ${m.dropout_flag ? `<dt class="warn">Dropout</dt><dd class="warn">${escapeHtml(m.dropout_reason)}</dd>` : ""}
              ${m.should_escalate ? `<dt class="err">Escalation</dt><dd class="err">${escapeHtml(m.escalation_reason)}</dd>` : ""}
            </dl>
          </div>
        </div>
        <div class="rowtags">
          <span class="priority-tag">${m.access_adjusted_priority.toUpperCase()}</span>
          ${flags}
          <button class="ack-btn" data-ack="${m.message_id}" ${m.acknowledged ? "disabled" : ""}>${ackLabel}</button>
        </div>
      </div>`;
    })
    .join("");

  list.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-toggle");
      if (state.expanded.has(id)) state.expanded.delete(id);
      else state.expanded.add(id);
      renderQueue();
    });
  });
  list.querySelectorAll("[data-ack]").forEach((btn) => {
    btn.addEventListener("click", () => acknowledge(btn.getAttribute("data-ack")));
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- Compare ----------
function renderCompare() {
  let rows = "";
  let disagreeCount = 0;
  state.messages.forEach((m) => {
    const agree = m.llm_urgency === m.baseline_urgency;
    if (!agree) disagreeCount++;
    const preview = m.raw_text.length > 60 ? m.raw_text.slice(0, 60) + "..." : m.raw_text;
    rows += `<tr>
      <td class="mono">${m.message_id}</td>
      <td>${escapeHtml(preview)}</td>
      <td>${m.llm_urgency}</td>
      <td>${m.baseline_urgency}</td>
      <td>${agree ? "&#10003;" : '<span class="disagree">&#10007; DISAGREE</span>'}</td>
    </tr>`;
  });

  el("compareTableWrap").innerHTML = `
    <table class="dispatch-table">
      <tr><th>Message</th><th>Text</th><th>LLM says</th><th>Baseline says</th><th>Agree?</th></tr>
      ${rows}
    </table>`;

  el("compareNote").textContent =
    disagreeCount > 0
      ? `${disagreeCount} disagreement(s) found. Worth writing up in your report — check the message text for the disagreeing rows above.`
      : "No disagreements at this point in the simulation.";

  if (state.baselineEval) {
    const e = state.baselineEval;
    el("baselineEvalNote").textContent =
      `Baseline model trained on ${e.n_train} messages, evaluated on ${e.n_test} held-out messages it never saw during training — ` +
      `${(e.accuracy * 100).toFixed(0)}% accuracy against the true urgency label (${e.n_total} messages total).`;
  }
}

// ---------- Fairness ----------
function renderFairness() {
  const pairs = state.fairnessPairs || [];
  const container = el("fairnessPairs");

  if (pairs.length === 0) {
    container.innerHTML = "";
    el("fairnessSummary").innerHTML = `<p class="view-note">Advance the simulation clock to see the fairness-audit pairs arrive.</p>`;
    return;
  }

  let llmConsistent = 0;
  let baselineConsistent = 0;
  let complete = 0;

  container.innerHTML = pairs
    .map((p) => {
      const informal = p.informal;
      const formal = p.formal;
      if (!informal || !formal) {
        const have = informal || formal;
        return `<div class="fairness-pair">
          <div class="fairness-pair-id mono">${p.pair_id}</div>
          <p class="view-note">Waiting on the ${informal ? "formal" : "informal"} half of this pair to arrive
          (true urgency: ${have.true_urgency}).</p>
        </div>`;
      }
      complete++;
      const llmMatch = informal.llm_urgency === formal.llm_urgency;
      const baselineMatch = informal.baseline_urgency === formal.baseline_urgency;
      if (llmMatch) llmConsistent++;
      if (baselineMatch) baselineConsistent++;

      return `<div class="fairness-pair">
        <div class="fairness-pair-id mono">${p.pair_id} <span class="view-note">— true urgency: ${informal.true_urgency}</span></div>
        <table class="dispatch-table">
          <tr><th>Message</th><th>Style</th><th>Text</th><th>LLM urgency</th><th>Baseline urgency</th></tr>
          <tr>
            <td class="mono">${informal.message_id}</td><td>Informal / SMS</td>
            <td>${escapeHtml(informal.raw_text)}</td><td>${informal.llm_urgency}</td><td>${informal.baseline_urgency}</td>
          </tr>
          <tr>
            <td class="mono">${formal.message_id}</td><td>Formal written</td>
            <td>${escapeHtml(formal.raw_text)}</td><td>${formal.llm_urgency}</td><td>${formal.baseline_urgency}</td>
          </tr>
        </table>
        <p class="pair-verdict">
          <span class="${llmMatch ? "" : "disagree"}">LLM consistent: ${llmMatch ? "Yes" : "No"}</span>
          &nbsp;&middot;&nbsp;
          <span class="${baselineMatch ? "" : "disagree"}">Baseline consistent: ${baselineMatch ? "Yes" : "No"}</span>
        </p>
      </div>`;
    })
    .join("");

  el("fairnessSummary").innerHTML = complete
    ? `<p><strong>Across ${complete} complete pair(s):</strong> LLM stayed consistent on ${llmConsistent}/${complete},
       baseline stayed consistent on ${baselineConsistent}/${complete}.</p>`
    : "";
}

// ---------- Map ----------
function renderMap() {
  const byLocation = {};
  state.messages.forEach((m) => {
    if (!byLocation[m.location]) byLocation[m.location] = [];
    byLocation[m.location].push(m);
  });

  const ntOutline = `M 300 12 L 355 12 L 395 60 L 420 105 L 460 140 L 475 195 L 450 250
    L 420 300 L 400 340 L 415 400 L 395 470 L 400 560 L 385 650 L 400 720 L 370 800
    L 330 870 L 220 880 L 130 830 L 75 740 L 55 640 L 65 520 L 45 400 L 30 280
    L 55 190 L 40 130 L 90 75 L 160 30 L 230 15 Z`;

  let svg = `<path d="${ntOutline}" fill="var(--panel-raised)" stroke="var(--line)" stroke-width="2"/>`;
  svg += `<text x="250" y="895" text-anchor="middle" class="mono" font-size="17" fill="var(--muted)">NORTHERN TERRITORY — SCHEMATIC, NOT TO SCALE</text>`;

  Object.entries(LOCATIONS).forEach(([name, pos]) => {
    const msgsHere = byLocation[name] || [];
    let color = "var(--line)";
    if (msgsHere.length) {
      const best = msgsHere.reduce((a, b) =>
        URGENCY_ORDER[a.access_adjusted_priority] < URGENCY_ORDER[b.access_adjusted_priority] ? a : b
      );
      color = URGENCY_COLOR[best.access_adjusted_priority];
    }
    const active = state.activePin === name ? 1 : 0;
    svg += `
      <g class="pin" data-loc="${name}">
        ${msgsHere.some((m) => m.should_escalate) ? `<circle cx="${pos.x}" cy="${pos.y}" r="14" fill="none" stroke="${color}" stroke-width="2" opacity="0.6"><animate attributeName="r" values="10;18;10" dur="1.4s" repeatCount="indefinite"/><animate attributeName="opacity" values="0.6;0;0.6" dur="1.4s" repeatCount="indefinite"/></circle>` : ""}
        <circle class="core" cx="${pos.x}" cy="${pos.y}" r="${msgsHere.length ? 9 : 5}" fill="${color}" stroke="${active ? "#fff" : "var(--bg)"}" stroke-width="2"/>
        <text x="${pos.x + 14}" y="${pos.y + 4}">${name}${msgsHere.length ? ` (${msgsHere.length})` : ""}</text>
      </g>`;
  });

  el("ntMap").innerHTML = svg;
  el("ntMap").querySelectorAll("[data-loc]").forEach((g) => {
    g.addEventListener("click", () => {
      state.activePin = g.getAttribute("data-loc");
      renderMap();
      renderMapDetail(byLocation[state.activePin] || []);
    });
  });

  if (state.activePin) renderMapDetail(byLocation[state.activePin] || []);
}

function renderMapDetail(msgs) {
  if (!state.activePin) return;
  if (msgs.length === 0) {
    el("mapDetail").innerHTML = `<h4>${state.activePin}</h4><p>No active messages from this location yet.</p>`;
    return;
  }
  el("mapDetail").innerHTML = `<h4>${state.activePin}</h4>` +
    msgs
      .map(
        (m) => `<div class="mini-row">
          <span class="priority-tag" style="background:${URGENCY_COLOR[m.access_adjusted_priority]}">${m.access_adjusted_priority.toUpperCase()}</span>
          <div style="margin-top:6px;">${escapeHtml(m.raw_text)}</div>
        </div>`
      )
      .join("");
}

// ---------- Controls ----------
function setView(view) {
  state.view = view;
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  render();
}

function togglePlay() {
  state.playing = !state.playing;
  const btn = el("playBtn");
  if (state.playing) {
    btn.textContent = "⏸ PAUSE";
    btn.classList.add("playing");
    scheduleTick();
  } else {
    btn.textContent = "▶ PLAY";
    btn.classList.remove("playing");
    clearTimeout(state.playTimer);
  }
}

function scheduleTick() {
  const interval = parseInt(el("speedSelect").value, 10);
  state.playTimer = setTimeout(() => {
    let next = state.minutes + 15;
    if (next > 480) {
      togglePlay();
      return;
    }
    state.minutes = next;
    el("clockSlider").value = next;
    el("minutesReadout").textContent = `+${next} min`;
    fetchState(next);
    if (state.playing) scheduleTick();
  }, interval);
}

el("clockSlider").addEventListener("input", (e) => {
  if (state.playing) togglePlay();
  state.minutes = parseInt(e.target.value, 10);
  el("minutesReadout").textContent = `+${state.minutes} min`;
  fetchState(state.minutes);
});
el("playBtn").addEventListener("click", togglePlay);
el("resetBtn").addEventListener("click", resetAcks);
document.querySelectorAll(".tab-btn").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));

fetchState(state.minutes);
