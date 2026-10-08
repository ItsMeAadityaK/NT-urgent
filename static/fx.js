// Motion and interaction layer: count-up numbers, the sliding tab pill, the shift timeline (scrub the clock by
// dragging), arrival toasts, the sticky mini bar and keyboard shortcuts.
// Loaded after app.js and journey.js. Purely presentational: nothing here changes how messages are triaged.

const FX_REDUCE = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- count-up numbers ---------- */
function tween(node, to, suffix = "", dur = 650) {
  const from = parseFloat(node.dataset.v);
  node.dataset.v = to;
  cancelAnimationFrame(node._raf);
  if (FX_REDUCE || isNaN(from) || from === to) { node.textContent = to + suffix; return; }
  const t0 = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - t0) / dur);
    node.textContent = Math.round(from + (to - from) * (1 - Math.pow(1 - k, 3))) + suffix;
    if (k < 1) node._raf = requestAnimationFrame(step);
  };
  node._raf = requestAnimationFrame(step);
}

/* ---------- sliding tab pill ---------- */
function moveTabIndicator() {
  const act = document.querySelector(".view-tabs .tab-btn.active");
  const ind = el("tabIndicator");
  if (!act || !ind) return;
  ind.style.width = act.offsetWidth + "px";
  ind.style.transform = `translateX(${act.offsetLeft}px)`;
  ind.style.opacity = 1;
  act.closest(".view-tabs").classList.add("ready");
}
window.addEventListener("resize", moveTabIndicator);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(moveTabIndicator);

/* ---------- shift timeline ---------- */
const TL = { built: false, buckets: 32, max: 480, down: false, last: 0 };
const PRIOS = ["low", "medium", "high", "critical"];   // stacked bottom to top

function buildTimeline() {
  const tl = el("timeline");
  tl.innerHTML = `
    <div class="tl-bars">${Array.from({ length: TL.buckets }, (_, i) =>
      `<div class="tl-col" data-b="${i}">${PRIOS.map((p) => `<i class="s-${p}"></i>`).join("")}</div>`).join("")}</div>
    <div class="tl-hours">${Array.from({ length: 9 }, (_, h) =>
      `<span style="left:${(h / 8) * 100}%">${String(6 + h).padStart(2, "0")}</span>`).join("")}</div>
    <div class="tl-head" id="tlHead"><span class="tl-flag" id="tlFlag"></span></div>
    <div class="tl-tip" id="tlTip"></div>`;
  TL.built = true;

  const minuteAt = (e) => {
    const r = tl.getBoundingClientRect();
    const frac = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    return Math.round((frac * TL.max) / 15) * 15;
  };
  const scrub = (e, force) => {
    const m = minuteAt(e);
    if (m === state.minutes && !force) return;
    if (state.playing) togglePlay();
    setMinutes(m);
    const now = performance.now();
    if (force || now - TL.last > 130) { TL.last = now; fetchState(); }
  };
  tl.addEventListener("pointerdown", (e) => { TL.down = true; tl.setPointerCapture(e.pointerId); tl.classList.add("dragging"); scrub(e, true); });
  tl.addEventListener("pointermove", (e) => {
    if (TL.down) scrub(e, false);
    showTip(e, minuteAt(e));
  });
  tl.addEventListener("pointerup", (e) => { TL.down = false; tl.classList.remove("dragging"); scrub(e, true); });
  tl.addEventListener("pointerleave", () => { el("tlTip").classList.remove("show"); });
  tl.addEventListener("keydown", (e) => {
    const d = e.key === "ArrowRight" ? 15 : e.key === "ArrowLeft" ? -15 : 0;
    if (!d) return;
    e.preventDefault();
    if (state.playing) togglePlay();
    setMinutes(Math.min(TL.max, Math.max(0, state.minutes + d)));
    fetchState();
  });
}

function bucketOf(m) { return Math.min(TL.buckets - 1, Math.floor(m.arrival_minute / 15)); }

function showTip(e, minute) {
  if (!state.data) return;
  const tip = el("tlTip"), tl = el("timeline");
  const b = Math.min(TL.buckets - 1, Math.floor(minute / 15));
  const here = state.data.messages.filter((m) => bucketOf(m) === b);
  const crit = here.filter((m) => m.access_adjusted_priority === "critical").length;
  const t = 6 * 60 + b * 15;
  const clock = `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
  tip.innerHTML = b * 15 > state.minutes
    ? `<b>${clock}</b> not arrived yet`
    : `<b>${clock}</b> ${here.length} new${crit ? ` <span class="crit">${crit} critical</span>` : ""}`;
  const r = tl.getBoundingClientRect();
  tip.style.left = Math.min(r.width - 70, Math.max(70, e.clientX - r.left)) + "px";
  tip.classList.add("show");
}

function renderTimeline() {
  if (!TL.built) buildTimeline();
  const msgs = state.data.messages;
  const counts = Array.from({ length: TL.buckets }, () => ({ low: 0, medium: 0, high: 0, critical: 0, n: 0 }));
  msgs.forEach((m) => { const c = counts[bucketOf(m)]; c[m.access_adjusted_priority]++; c.n++; });
  const max = Math.max(3, ...counts.map((c) => c.n));
  document.querySelectorAll("#timeline .tl-col").forEach((col, i) => {
    PRIOS.forEach((p) => { col.querySelector(".s-" + p).style.height = (counts[i][p] / max) * 100 + "%"; });
    col.classList.toggle("future", i * 15 > state.minutes);
  });
  const head = el("tlHead");
  head.style.setProperty("--f", state.minutes / TL.max);
  const t = 6 * 60 + state.minutes;
  el("tlFlag").textContent = `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
  const tl = el("timeline");
  tl.setAttribute("aria-valuenow", state.minutes);
  tl.setAttribute("aria-valuetext", el("tlFlag").textContent);
}

/* ---------- sticky mini bar ---------- */
let miniBuilt = false;
function renderMiniBar() {
  const bar = el("miniBar");
  if (!miniBuilt) {
    bar.innerHTML = `
      <span class="mb-brand"><span class="brand-mark"></span>NT TRIAGE</span>
      <span class="mb-shift mono" id="mbShift"></span>
      <span class="mb-clock mono" id="mbClock"></span>
      <button class="mb-alert" id="mbAlert"></button>
      <button class="mb-play" id="mbPlay" aria-label="Play or pause">&#9654;</button>`;
    el("mbAlert").addEventListener("click", () => window.scrollTo({ top: 0, behavior: FX_REDUCE ? "auto" : "smooth" }));
    el("mbPlay").addEventListener("click", togglePlay);
    miniBuilt = true;
  }
  const d = state.data, s = d.shift || {};
  const need = d.messages.filter((m) => ROLE_DESKS[state.role].includes(m)).length;
  el("mbShift").textContent = s.mode === "shift" ? `seed ${s.seed}` : "benchmark";
  el("mbClock").textContent = fmtTime(d.current_time);
  const a = el("mbAlert");
  a.textContent = need ? `${need} need a human now` : "all clear";
  a.classList.toggle("clear", !need);
  el("mbPlay").innerHTML = state.playing ? "&#10074;&#10074;" : "&#9654;";
}
function syncMiniBar() {
  const show = window.scrollY > 430;
  el("miniBar").classList.toggle("show", show);
  if (miniBuilt) el("mbPlay").innerHTML = state.playing ? "&#10074;&#10074;" : "&#9654;";
}
window.addEventListener("scroll", syncMiniBar, { passive: true });
setInterval(syncMiniBar, 400);

/* ---------- toasts ---------- */
function toast(html, cls, onClick) {
  const box = el("toasts");
  const t = document.createElement("div");
  t.className = `toast ${cls || ""}`;
  t.innerHTML = html;
  if (onClick) { t.classList.add("clickable"); t.addEventListener("click", () => { onClick(); t.remove(); }); }
  box.appendChild(t);
  requestAnimationFrame(() => t.classList.add("in"));
  while (box.children.length > 4) box.firstChild.remove();
  setTimeout(() => { t.classList.remove("in"); setTimeout(() => t.remove(), 300); }, cls && cls.includes("critical") ? 8000 : 5500);
}

function openMessage(id) {
  state.expanded.add(id);
  state.priorityFilter = "";
  state.teamFilter = "";
  setView("queue");
  setTimeout(() => {
    const btn = document.querySelector(`[data-toggle="${id}"]`);
    if (btn) btn.closest(".dispatch-row").scrollIntoView({ behavior: FX_REDUCE ? "auto" : "smooth", block: "center" });
  }, 80);
}

function notifyArrivals(prev, cur) {
  if (!prev || !cur || !prev.shift || !cur.shift) return;
  if (prev.shift.seed !== cur.shift.seed || prev.shift.mode !== cur.shift.mode) return;
  if (cur.minutes_elapsed < prev.minutes_elapsed) return;
  const had = new Map(prev.messages.map((m) => [m.message_id, m]));
  const fresh = cur.messages.filter((m) => !had.has(m.message_id));
  const newlyEscalated = cur.messages.filter((m) => {
    const old = had.get(m.message_id);
    return old && m.should_escalate && !m.acknowledged && (m.escalation_level > (old.should_escalate ? old.escalation_level : 0));
  });
  if (!fresh.length && !newlyEscalated.length) return;

  if (fresh.length > 6) {
    const crit = fresh.filter((m) => m.access_adjusted_priority === "critical").length;
    toast(`<span class="t-tag" style="--c:var(--accent)">${fresh.length} NEW</span><div><b>${fresh.length} messages arrived</b><span>${crit} critical</span></div>`, crit ? "critical" : "", () => setView("queue"));
    return;
  }
  const order = (m) => URGENCY_ORDER[m.access_adjusted_priority];
  // Only critical and high arrivals interrupt; routine ones just appear in the queue.
  fresh.filter((m) => order(m) <= 1).sort((a, b) => order(a) - order(b)).slice(0, 3).forEach((m) => {
    toast(`<span class="t-tag" style="--c:${URGENCY_COLOR[m.access_adjusted_priority]}">${m.access_adjusted_priority.toUpperCase()}</span>
      <div><b>${m.message_id} · ${escapeHtml(m.team)}</b><span>${escapeHtml(clip(m.raw_text, 80))}</span></div>`,
      m.access_adjusted_priority === "critical" ? "critical" : "", () => openMessage(m.message_id));
  });
  newlyEscalated.slice(0, 2).forEach((m) => {
    toast(`<span class="t-tag" style="--c:var(--critical)">ESCALATED</span>
      <div><b>${m.message_id} → ${escapeHtml(m.escalate_to)}</b><span>${escapeHtml(clip(m.raw_text, 70))}</span></div>`, "critical", () => openMessage(m.message_id));
  });
}

/* ---------- keyboard ---------- */
document.addEventListener("keydown", (e) => {
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.code === "Space" && e.target.tagName !== "BUTTON" && !e.target.closest("#timeline")) { e.preventDefault(); togglePlay(); return; }
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= VIEW_NAMES.length) setView(VIEW_NAMES[n - 1]);
});

moveTabIndicator();
