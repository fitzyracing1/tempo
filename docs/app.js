const HIGH = 0.7, LOW = 0.4, MAX = 10;
const SEED = [1.0, 1.0, 0.2, 1.0];
const BRIEF = "Build TEMPO itself: an iterative spec rewriter whose next temperature is chosen from change-ratio, high/low run length, and spec completeness.";
const PREV0 = "seed brief only — no spec yet";
const CUR0 = `# TEMPO spec (pass 4 after H,H,L,H)

Role: temperature controller for iterative AI spec rewriting.

Missing pieces:
- full system prompt not locked
- tools list is a sketch
- eval harness not written
`;

const state = {
  brief: BRIEF,
  temps: SEED.slice(),
  prev: PREV0,
  cur: CUR0,
};

function mode(t) {
  return t >= HIGH ? "H" : t <= LOW ? "L" : "M";
}

function ratio(a, b) {
  if (!a || !b) return 1;
  const ta = new Set(a.toLowerCase().split(/\s+/).filter(Boolean));
  const tb = new Set(b.toLowerCase().split(/\s+/).filter(Boolean));
  let inter = 0;
  for (const w of ta) if (tb.has(w)) inter++;
  const union = new Set([...ta, ...tb]).size || 1;
  return 1 - inter / union;
}

function complete(spec) {
  const s = spec.toLowerCase();
  return ["system prompt", "tools", "eval"].every((k) => s.includes(k)) && (s.split("->").length - 1) >= 5;
}

function runLen(temps, pred) {
  let n = 0;
  for (let i = temps.length - 1; i >= 0; i--) {
    if (!pred(temps[i])) break;
    n++;
  }
  return n;
}

function decide() {
  const d = ratio(state.prev, state.cur);
  const last = state.temps.length ? state.temps[state.temps.length - 1] : 1;
  const hi = runLen(state.temps, (t) => t >= HIGH);
  const lo = runLen(state.temps, (t) => t <= LOW);
  const ok = complete(state.cur);
  const s = state.cur.toLowerCase();
  const gaps = [];
  if (!s.includes("system prompt")) gaps.push("system prompt");
  if (!s.includes("tools")) gaps.push("tools");
  if (!s.includes("eval")) gaps.push("eval");
  const arrows = s.split("->").length - 1;
  if (arrows < 5) gaps.push(`eval-arrows ${arrows}/5`);

  let nxt = "PASS", t = 0.6, why = "explore";
  if (state.temps.length >= MAX) {
    nxt = "FINISH"; t = 0.3; why = `hit ${MAX}-pass cap`;
  } else if (last <= LOW && d < 0.15 && ok) {
    nxt = "FINISH"; t = 0.3; why = `converged (change ${(d * 100).toFixed(0)}%) and spec complete`;
  } else if (hi >= 2) {
    t = 0.25; why = "two high already — grok consolidates";
  } else if (lo >= 2 && !ok) {
    t = 0.85; why = "two low already — grok breaks plateau";
  } else if (d > 0.5) {
    t = 0.22; why = `big rewrite (${(d * 100).toFixed(0)}%) — grok converges`;
  } else if (d < 0.15 && gaps.length) {
    t = 0.88; why = `plateau + gaps (${gaps.join(", ")}) — grok diverges`;
  } else if (gaps.length) {
    t = 0.55; why = `moderate change (${(d * 100).toFixed(0)}%); still missing ${gaps.join(", ")}`;
  } else {
    t = 0.45; why = `moderate change (${(d * 100).toFixed(0)}%) — tighten`;
  }
  if (nxt === "FINISH" && !ok) {
    nxt = "PASS"; t = 0.2; why = "grok wanted FINISH but spec incomplete — converge";
  }
  const sched = state.temps.map(mode).join("") + (nxt === "FINISH" ? "." : mode(t));
  return { next: nxt, t, mode: nxt === "PASS" ? mode(t) : "—", why, change: +d.toFixed(3), complete: ok, schedule: sched };
}

function answer(q) {
  const ql = (q || "").trim().toLowerCase();
  if (!ql) return "Ask something. Try: what is the next t?";
  if (ql.includes("who are you") || ql.includes("what are you")) {
    return "TEMPO desk in the browser. I pick the next rewrite temperature. Seed HHLH. No API key.";
  }
  if (ql.includes("finish")) {
    const out = decide();
    if (out.next === "FINISH") return `Yes — FINISH. ${out.why}`;
    return `No FINISH yet. Need last pass low, small change, system prompt + tools + eval and ≥5 '->' tests.\nNow: complete=${out.complete} change=${out.change} last=${mode(state.temps.at(-1))}\nGrok would ${out.next} at t=${out.t} (${out.why})`;
  }
  if (ql.includes("missing") || ql.includes("gap") || ql.includes("complete")) {
    const s = state.cur.toLowerCase();
    const bits = [
      s.includes("system prompt") ? "system prompt mentioned" : "MISSING system prompt",
      s.includes("tools") ? "tools mentioned" : "MISSING tools",
      s.includes("eval") ? "eval mentioned" : "MISSING eval",
      `${(s.split("->").length - 1)}/5 eval arrows`,
    ];
    return "Completeness: " + bits.join(", ") + `\ncomplete()=${complete(state.cur)}`;
  }
  if (ql.includes("schedule") || ql.includes("seed") || ql.includes("temps") || ql.includes("history")) {
    return `temps=${JSON.stringify(state.temps)}\nmodes=${state.temps.map(mode).join("")}  seed HHLH\nHIGH>=${HIGH}  LOW<=${LOW}  cap=${MAX}`;
  }
  if (ql.includes("rule") || ql.includes("how do you") || ql.includes("system")) {
    return "High t (0.8–1.0) diverge. Mid explore. Low (0.1–0.3) converge.\n1 big change → low\n2 small change + gaps → high\n3 never 3 H or 3 L unless finish\n4 FINISH after low + small change + complete spec";
  }
  const out = decide();
  return `${out.next}  t=${out.t}  mode=${out.mode}\nschedule ${out.schedule}   change=${out.change}  complete=${out.complete}\nwhy: ${out.why}\nbrain: grok-js`;
}

function renderTape(nextMode) {
  const el = document.getElementById("tape");
  el.innerHTML = "";
  state.temps.forEach((t) => {
    const s = document.createElement("span");
    s.className = "pill " + mode(t);
    s.textContent = mode(t);
    el.appendChild(s);
  });
  if (nextMode) {
    const s = document.createElement("span");
    s.className = "pill " + nextMode + " next";
    s.textContent = "→" + nextMode;
    el.appendChild(s);
  }
}

function add(q, a) {
  const log = document.getElementById("log");
  const row = document.createElement("div");
  row.className = "row";
  row.innerHTML = '<div class="q"></div><div class="a"></div>';
  row.querySelector(".q").textContent = q;
  row.querySelector(".a").textContent = a;
  log.appendChild(row);
  row.scrollIntoView({ behavior: "smooth", block: "end" });
}

document.getElementById("f").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("q");
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  add(q, answer(q));
});

document.querySelectorAll(".chips button").forEach((b) => {
  b.addEventListener("click", () => {
    const q = b.getAttribute("data-q");
    add(q, answer(q));
  });
});

renderTape(decide().mode);
add("desk", "Ask anything about the schedule, next t, finish rules, or gaps.");
