// The "How It Works" tab: follows one real message from its channel through the checks to a named team.
// Loaded after app.js and uses its globals (state, el, URGENCY_COLOR...). Nothing here changes how messages are triaged.

/* ===================================================================
   Journey: follow one real message from arrival to a human
   =================================================================== */
const J = { mid: null, shown: null, timers: [] };
const CHANNEL_LABEL = { sms: "SMS", webform: "Web form", email: "Email", phone: "Phone" };
const ACCESS_NOTE = {
  normal: "Normal access: no change.",
  limited: "Limited access: raised one level.",
  "cut-off": "Cut off (flood, no road): raised two levels.",
};

function urgPill(level) {
  if (!level) return `<span class="jr-pill none">none</span>`;
  return `<span class="jr-pill" style="--c:${URGENCY_COLOR[level] || "#8B8F98"}">${level.toUpperCase()}</span>`;
}

function renderJourney() {
  const msgs = state.data.messages;
  const pick = el("journeyPick");
  const sig = `${state.data.shift ? state.data.shift.seed : ""}:${msgs.length}`;
  if (pick.dataset.sig !== sig) {
    pick.innerHTML = msgs.slice(0, 40).map((m) =>
      `<option value="${m.message_id}">${m.message_id} · ${m.access_adjusted_priority.toUpperCase()} · ${escapeHtml(clip(m.raw_text, 60))}</option>`).join("");
    pick.dataset.sig = sig;
  }
  if (!msgs.length) {
    el("journeyStage").innerHTML = `<p class="view-note">No messages yet. Move the clock forward or press PLAY.</p>`;
    return;
  }
  if (!msgs.find((m) => m.message_id === J.mid)) {
    const best = msgs.find((m) => m.access_adjusted_priority === "critical" && m.access_status !== "normal")
      || msgs.find((m) => m.access_adjusted_priority === "critical") || msgs[0];
    J.mid = best.message_id;
    J.shown = null;
  }
  pick.value = J.mid;
  if (J.shown !== J.mid) {
    buildJourney(msgs.find((m) => m.message_id === J.mid));
    J.shown = J.mid;
    playJourney();
  }
}

// The six stage cards for one message (also used by the Try a Message tab).
function stageCards(m) {
  const unreadable = m.category === "Language not recognised";
  const sigs = m.safety_signals || [];
  const llmKnown = m.llm_urgency != null;
  const bumped = m.content_urgency !== m.access_adjusted_priority;

  const stage = (n, name, plain, val, detail, cls = "") => `
    <div class="jr-card jr-step ${cls}" data-s="${n}">
      <div class="jr-n">${n}</div><h5>${name}</h5>
      <p class="jr-plain">${plain}</p>
      <div class="jr-val">${val}</div>
      <p class="jr-detail">${detail}</p>
    </div>`;

  return [
    stage(1, "Can we read it?", "Language check",
      unreadable ? `<span class="jr-pill" style="--c:#E8590C">NOT RECOGNISED</span>` : `<span class="jr-pill ok">READABLE</span>`,
      unreadable ? "Never ignored: raised to at least HIGH and sent to an interpreter." : "Typos, slang and short text are fine.",
      unreadable ? "warn" : ""),
    stage(2, "AI", "Reads the meaning",
      llmKnown ? urgPill(m.llm_urgency) : `<span class="jr-pill none">OFFLINE</span>`,
      llmKnown ? escapeHtml(clip(m.llm_reason, 130)) : "AI unavailable. The backup model and rules carry on."),
    stage(3, "Backup ML model", "Second opinion",
      urgPill(m.baseline_urgency),
      !llmKnown ? "Used because AI is offline."
        : m.baseline_urgency === m.llm_urgency ? "Agrees with AI." : "Differs from AI, so a person is told to look closer."),
    stage(4, "Safety rules", "Fixed checklist",
      sigs.length ? sigs.map((s) => `<span class="jr-pill sig">${escapeHtml(s.signal)}</span>`).join(" ") : `<span class="jr-pill none">NO TRIPWIRE</span>`,
      sigs.length ? `Raises to at least ${(m.safety_floor || "").toUpperCase()}. The AI cannot override this.` : "Rules can only raise priority, never lower it.",
      sigs.length ? "hit" : ""),
    stage(5, "Can they get help?", "Access check",
      `<span class="jr-pill sig">${escapeHtml((m.access_status || "normal").toUpperCase())}</span>`,
      ACCESS_NOTE[m.access_status] || ACCESS_NOTE.normal),
    stage(6, "Final priority", "What the human sees",
      urgPill(m.access_adjusted_priority),
      bumped ? `Content said ${m.content_urgency}. After rules and access: ${m.access_adjusted_priority}.` : "Priority only ever goes up through the steps.", "final"),
  ].join("");
}

function buildJourney(m) {
  const ch = (m.channel || "").toLowerCase();
  const finalColor = URGENCY_COLOR[m.access_adjusted_priority];
  const stages = stageCards(m);

  const sla = m.sla_minutes;
  const ladder = sla
    ? `<div class="jr-ladder">
         <div class="jr-rung"><b>Officer</b><span>acknowledge within ${sla} min</span></div>
         <div class="jr-rung up"><b>Shift supervisor</b><span>alerted at ${sla} min</span></div>
         <div class="jr-rung up2"><b>Duty manager</b><span>alerted at ${sla * 2} min</span></div>
       </div>`
    : `<div class="jr-ladder"><div class="jr-rung"><b>Officer</b><span>routine: no auto-escalation</span></div></div>`;
  const status = m.acknowledged ? `Acknowledged${m.acknowledged_by ? " by " + escapeHtml(m.acknowledged_by) : ""}.`
    : m.should_escalate ? `Overdue: escalated to ${escapeHtml(m.escalate_to || "")}.` : `Waiting ${m.waited_minutes} min so far.`;

  el("journeyStage").innerHTML = `
    <div class="jr-band">
      <div class="jr-band-h"><span>1</span> Where it comes from</div>
      <div class="jr-source jr-step" data-s="0">
        <div class="jr-chans">${Object.entries(CHANNEL_LABEL).map(([k, v]) => `<span class="jr-chan ${k === ch ? "on" : ""}">${v}</span>`).join("")}
          <span class="jr-inbox">one inbox &middot; <span class="mono">POST /api/ingest</span></span></div>
        <div class="jr-bubble">
          <div class="jr-meta mono">${m.message_id} &middot; ${fmtTime(m.timestamp)} &middot; ${escapeHtml(m.location)} &middot; access: ${escapeHtml(m.access_status)}</div>
          <div class="jr-text">&ldquo;${escapeHtml(m.raw_text)}&rdquo;</div>
        </div>
      </div>
    </div>
    <div class="jr-band">
      <div class="jr-band-h"><span>2</span> What the system checks</div>
      <div class="jr-stages">${stages}</div>
    </div>
    <div class="jr-band">
      <div class="jr-band-h"><span>3</span> Who gets it</div>
      <div class="jr-out">
        <div class="jr-card jr-step jr-team" data-s="7" style="--row-color:${finalColor}">
          <h5>Routed to</h5>
          <div class="jr-team-name">${escapeHtml(m.team)}${m.cc_duty_officer ? " <small>+ Duty Officer</small>" : ""}</div>
          <p class="jr-detail">${escapeHtml(m.category)}. ${escapeHtml(m.route_reason || "")}</p>
        </div>
        <div class="jr-card jr-step" data-s="8">
          <h5>If nobody acts</h5>${ladder}
          <p class="jr-detail"><strong>${status}</strong></p>
        </div>
        <div class="jr-card jr-step jr-draft" data-s="9">
          <h5>Reply</h5>
          <div class="jr-val"><span class="jr-pill none">DRAFTED, NOT SENT</span></div>
          <p class="jr-detail">A person reads it, edits it and approves it. The system never replies to the public.</p>
        </div>
      </div>
    </div>`;
}

// Light the cards under `root` up one after another (the little "message travelling" animation).
function playLit(root, timers, step = 520, start = 350) {
  timers.forEach(clearTimeout);
  timers.length = 0;
  const steps = [...root.querySelectorAll(".jr-step")];
  steps.forEach((s) => s.classList.remove("lit"));
  steps.sort((a, b) => a.dataset.s - b.dataset.s).forEach((s, i) => {
    timers.push(setTimeout(() => s.classList.add("lit"), start + i * step));
  });
}
function playJourney() { playLit(el("journeyStage"), J.timers); }

// /?msg=L003#journey opens the journey on that message.
const _jm = new URLSearchParams(location.search).get("msg");
if (_jm) J.mid = _jm;

el("journeyPick").addEventListener("change", (e) => { J.mid = e.target.value; J.shown = null; renderJourney(); });
el("journeyReplay").addEventListener("click", playJourney);
