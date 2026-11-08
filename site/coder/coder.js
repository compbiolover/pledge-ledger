// Rating tool. Loads only the blinded queue (coder/pledges.json): no names, parties, or anyone's ratings.
const COLUMNS = ["pledge_id", "coder", "rated_at", "codebook_version", "task", "period_end",
  "decision", "merge_into", "testable", "verbatim_ok", "outcome", "effort", "blocker", "evidence_urls", "note"];
const OUTCOMES = [["kept", "Kept"], ["partial", "Partially kept"], ["in_progress", "In progress"], ["not_rated", "Not yet rated"], ["broken", "Broken"]];
const EFFORTS = [["0", "No action"], ["1", "Talk only"], ["2", "Formal start"], ["3", "Spent capital"], ["4", "Every option"], ["-1", "Undermined"]];
const BLOCKERS = [["too_early", "Too early to tell"], ["none_attempted", "Not attempted"], ["legislature_opposition", "Opposing party in legislature"],
  ["legislature_own_party", "Own party in legislature"], ["courts", "Courts"], ["federal", "Federal government"], ["voters", "Voters"],
  ["budget", "Budget shortfall"], ["self_reversed", "Changed position"],
  ["other_chamber", "The House (Congress)"], ["president", "The president (Congress)"], ["filibuster", "Filibuster (Congress)"]];
const AREA = { economy_tax: "Economy and taxes", budget: "Budget", education: "Education", health: "Health", housing: "Housing",
  criminal_justice: "Criminal justice", immigration: "Immigration", environment_energy: "Energy and environment",
  infrastructure_transport: "Infrastructure", labor: "Jobs and labor", social_services: "Social services", elections_democracy: "Elections",
  government_ethics: "Government and ethics", agriculture_rural: "Agriculture and rural", guns: "Guns",
  reproductive_rights: "Reproductive rights", civil_rights: "Civil rights", technology: "Technology", other: "Other" };

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const KEY = "pt-ratings-v1";
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
let memory = {}; // fallback when browser storage is unavailable
let storageOk = true;
function store() {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { storageOk = false; return memory; }
}
function persist(obj) {
  memory = obj;
  try { localStorage.setItem(KEY, JSON.stringify(obj)); } catch { storageOk = false; }
}
const recKey = (r) => `${r.coder}|${r.task}|${r.period_end}|${r.pledge_id}`;

let Q = [], codebookVersion = "1.0", S = { coder: "", task: "extraction", period: "", order: [], i: 0 };

// deterministic per-coder shuffle so the two reviewers see promises in different orders
function seededOrder(n, seed) {
  let h = 2166136261;
  for (const ch of seed) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  const rnd = () => ((h = Math.imul(h ^ (h >>> 15), 2246822507) ^ Math.imul(h ^ (h >>> 13), 3266489909)) >>> 0) / 4294967296;
  const a = [...Array(n).keys()];
  for (let i = n - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

function mine() {
  const all = store();
  return Object.values(all).filter((r) => r.coder === S.coder && r.task === S.task && r.period_end === (S.task === "status" ? S.period : ""));
}
const done = () => new Set(mine().map((r) => r.pledge_id));

function visibleOrder() {
  if (!$("#todo-only").checked) return S.order;
  const d = done();
  return S.order.filter((ix) => !d.has(Q[ix].pledge_id));
}

function progress() {
  const d = done();
  const n = S.order.filter((ix) => d.has(Q[ix].pledge_id)).length;
  $("#bar").style.width = `${S.order.length ? (100 * n) / S.order.length : 0}%`;
  $("#progress-text").textContent = `${n} of ${S.order.length} done`;
}

const radios = (name, items, val) => `<div class="opts">${items.map(([v, t], i) =>
  `<label><input type="radio" name="${name}" value="${esc(v)}"${val === v ? " checked" : ""}> ${esc(t)}${i < 9 && name !== "blocker" ? ` <kbd>${i + 1}</kbd>` : ""}</label>`).join("")}</div>`;

function render() {
  const order = visibleOrder();
  if (!S.order.length) {
    $("#card").innerHTML = `<div class="card"><h2 style="margin-top:0">No promises are assigned to you</h2>
      <p>Every promise is assigned to other reviewers in <code>data/assignments.csv</code>. Check your reviewer ID, or ask the project lead to assign you some.</p></div>`;
    progress();
    return;
  }
  if (!order.length) {
    $("#card").innerHTML = `<div class="card"><h2 style="margin-top:0">All done for this task</h2>
      <p>Download your ratings and add the file to the repository as <code>data/ratings/${esc(S.coder)}.csv</code>.</p>
      <p><button class="primary" type="button" id="export2">Download my ratings</button></p></div>`;
    $("#export2").onclick = exportCsv;
    progress();
    return;
  }
  S.i = Math.max(0, Math.min(S.i, order.length - 1));
  const p = Q[order[S.i]];
  const prev = store()[recKey({ coder: S.coder, task: S.task, period_end: S.task === "status" ? S.period : "", pledge_id: p.pledge_id })] || {};
  const formBody = S.task === "extraction" ? `
      <fieldset><legend>Keep this promise in the tracker?</legend>${radios("decision", [["keep", "Keep"], ["drop", "Drop"], ["merge", "Merge into another"]], prev.decision)}</fieldset>
      <label id="merge-wrap" ${prev.decision === "merge" ? "" : "hidden"}><strong>Merge into which promise?</strong>
        <input type="text" id="merge_into" list="ids" value="${esc(prev.merge_into || "")}" placeholder="e.g. ${esc(p.state)}-001"></label>
      <fieldset><legend>Could someone later show it was kept or broken?</legend>${radios("testable", [["Y", "Yes, testable"], ["N", "No, too vague"]], prev.testable)}</fieldset>
      <fieldset><legend>Does the quote match the saved source word for word?</legend>${radios("verbatim_ok", [["Y", "Yes, it matches"], ["N", "No, or a condition is missing"]], prev.verbatim_ok)}</fieldset>`
    : `
      ${p.office === "Senator"
        ? `<fieldset><legend>What did the senator do by ${esc(S.period)}? (Part 2b)</legend>${radios("effort", EFFORTS, prev.effort)}</fieldset>
           <fieldset><legend>What happened to the policy?</legend>${radios("outcome", OUTCOMES, prev.outcome)}</fieldset>`
        : `<fieldset><legend>What happened by ${esc(S.period)}?</legend>${radios("outcome", OUTCOMES, prev.outcome)}</fieldset>
           <fieldset><legend>How hard did the governor push?</legend>${radios("effort", EFFORTS, prev.effort)}</fieldset>`}
      <fieldset id="blocker-wrap" ${prev.outcome === "kept" ? "hidden" : ""}><legend>Main obstacle</legend>${radios("blocker", BLOCKERS, prev.blocker)}</fieldset>
      <label><strong>Evidence links</strong><textarea id="evidence" placeholder="One link per line, most authoritative first">${esc((prev.evidence_urls || "").split("|").join("\n"))}</textarea>
        <span class="hint">Enacted text first, then official records, then government releases. News only for effort and obstacles.</span></label>`;
  $("#card").innerHTML = `<article class="card">
    <p class="small muted num">${esc(p.pledge_id)}. ${esc(p.office || "Governor")}, ${esc(p.state)}. ${esc(AREA[p.policy_area] || p.policy_area)}. ${p.requires_other_actor === "Y" ? "Needs others to act." : "Governor can act alone."}${p.compound_group ? ` Part of group ${esc(p.compound_group)}.` : ""}</p>
    <p class="quote quote-lg">${esc(p.pledge_text)}</p>
    <p class="small"><a href="${esc(safeUrl(p.archive_url))}" target="_blank" rel="noopener">Open the saved copy</a> &nbsp; <a href="${esc(safeUrl(p.source_url))}" target="_blank" rel="noopener">Open the live page</a></p>
    ${p.review_flags.length ? `<ul class="flags">${p.review_flags.map((f) => `<li>${esc(f.replace(/_/g, " "))}</li>`).join("")}</ul>` : ""}
    <form class="form" id="rate">
      ${formBody}
      <label><strong>Note</strong><textarea id="note" placeholder="${S.task === "extraction" ? "Why, especially for Drop or No" : "Name who blocked it, with a link; anything the other reviewer should know"}">${esc(prev.note || "")}</textarea></label>
      <p style="display:flex;gap:.75rem;flex-wrap:wrap">
        <button class="primary" type="submit">Save and next</button>
        <button type="button" id="back">Previous</button>
        <button type="button" id="skip">Skip for now</button>
      </p>
      <p class="hint">Keyboard: number keys pick the first unanswered question's option. Ctrl + Enter saves.</p>
    </form>
  </article>`;
  const f = $("#rate");
  f.addEventListener("change", (e) => {
    if (e.target.name === "decision") $("#merge-wrap").hidden = e.target.value !== "merge";
    if (e.target.name === "outcome") $("#blocker-wrap").hidden = e.target.value === "kept";
  });
  f.addEventListener("submit", (e) => { e.preventDefault(); save(p); });
  $("#back").onclick = () => { S.i = Math.max(0, S.i - 1); render(); };
  $("#skip").onclick = () => { S.i += 1; render(); };
  progress();
}

function val(name) { const n = document.querySelector(`input[name="${name}"]:checked`); return n ? n.value : ""; }

function save(p) {
  const r = Object.fromEntries(COLUMNS.map((c) => [c, ""]));
  Object.assign(r, { pledge_id: p.pledge_id, coder: S.coder, rated_at: new Date().toISOString(), codebook_version: codebookVersion,
    task: S.task, period_end: S.task === "status" ? S.period : "", note: $("#note").value.trim() });
  const missing = [];
  if (S.task === "extraction") {
    r.decision = val("decision"); r.testable = val("testable"); r.verbatim_ok = val("verbatim_ok");
    if (r.decision === "merge") {
      r.merge_into = $("#merge_into").value.trim().toUpperCase();
      if (!Q.some((x) => x.pledge_id === r.merge_into) || r.merge_into === p.pledge_id) missing.push("a valid promise ID to merge into");
    }
    if (!r.decision) missing.push("whether to keep it");
    if (!r.testable) missing.push("whether it's testable");
    if (!r.verbatim_ok) missing.push("whether the quote matches");
    if (r.decision === "drop" && !r.note) missing.push("a note saying why it should be dropped");
  } else {
    r.outcome = val("outcome"); r.effort = val("effort"); r.blocker = r.outcome === "kept" ? "" : val("blocker");
    r.evidence_urls = $("#evidence").value.split(/\s+/).map((u) => u.trim()).filter(Boolean).join("|");
    if (!r.outcome) missing.push("what happened");
    if (!r.effort) missing.push("the effort level");
    if (r.outcome && r.outcome !== "kept" && !r.blocker) missing.push("the main obstacle");
    if (r.outcome && r.outcome !== "not_rated" && !r.evidence_urls) missing.push("at least one evidence link");
  }
  if (missing.length) { $("#save-status").textContent = `Not saved. Add ${missing.join(", ")}.`; return; }
  const all = store();
  all[recKey(r)] = r;
  persist(all);
  $("#save-status").textContent = `Saved ${p.pledge_id}.${storageOk ? "" : " This browser can't keep data, so download your ratings before closing the tab."}`;
  if (!$("#todo-only").checked) S.i += 1;
  render();
  window.scrollTo({ top: 0, behavior: "instant" });
}

// A download replaces data/ratings/<id>.csv, so this browser must hold everything already in that file.
function hasBase(coder) { try { return localStorage.getItem(`pt-base-${coder}`) === "1"; } catch { return baseMem.has(coder); } }
function setBase(coder) { baseMem.add(coder); try { localStorage.setItem(`pt-base-${coder}`, "1"); } catch { /* memory only */ } }
const baseMem = new Set();
function askBase() {
  $("#base-q")?.remove();
  $("#setup-form").insertAdjacentHTML("afterend", `<div class="notice" id="base-q" role="alert">
    <p><strong>Do you already have a ratings file in the repository?</strong> Your download replaces that file, so load it first or earlier ratings will be lost.</p>
    <p style="display:flex;gap:.75rem;flex-wrap:wrap;margin-top:.75rem"><label class="btn" for="import">Load my ratings file</label>
    <button type="button" id="first-time">This is my first time</button></p></div>`);
  $("#first-time").onclick = () => { setBase(S.coder); $("#base-q").remove(); $("#setup-form").requestSubmit(); };
}

function csvCell(v) { const s = String(v ?? ""); return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }
function exportCsv() {
  const rows = Object.values(store()).filter((r) => r.coder === S.coder)
    .sort((a, b) => a.rated_at.localeCompare(b.rated_at));
  const text = [COLUMNS.join(","), ...rows.map((r) => COLUMNS.map((c) => csvCell(r[c])).join(","))].join("\n") + "\n";
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  a.download = `${S.coder}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  $("#save-status").textContent = `Downloaded ${rows.length} ratings as ${S.coder}.csv. Replace data/ratings/${S.coder}.csv in the repository with it.`;
}

function parseCsv(text) {
  const rows = []; let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) { if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; }
    else if (ch === '"') q = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i + 1] === "\n") i++; row.push(cell); rows.push(row); row = []; cell = ""; }
    else cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.some((c) => c !== ""));
}

$("#import").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const rows = parseCsv(await file.text());
  const head = rows.shift() || [];
  if (head.join(",") !== COLUMNS.join(",")) { $("#import-status").textContent = "That file's columns don't match a ratings file. Nothing was loaded."; return; }
  const all = store(); let n = 0;
  for (const cells of rows) {
    const r = Object.fromEntries(COLUMNS.map((c, i) => [c, cells[i] ?? ""]));
    const k = recKey(r);
    if (!all[k] || all[k].rated_at < r.rated_at) { all[k] = r; n++; }
  }
  persist(all);
  const ids = new Set(rows.map((c) => c[1]));
  ids.forEach(setBase);
  $("#base-q")?.remove();
  $("#import-status").textContent = `Loaded ${n} ratings. Pick a task and select Start to continue.`;
  if (rows[0]) $("#coder").value = rows[0][1];
});

document.querySelectorAll('input[name="task"]').forEach((n) => n.addEventListener("change", () => {
  $("#period-wrap").hidden = val("task") !== "status";
}));

$("#setup-form").addEventListener("submit", (e) => {
  e.preventDefault();
  S.coder = $("#coder").value.trim().toLowerCase();
  S.task = val("task");
  S.period = $("#period").value;
  if (S.task === "status" && !S.period) { $("#period").focus(); return; }
  if (!hasBase(S.coder)) { askBase(); return; }
  // a promise with no assignment is open to everyone; otherwise only its two assigned reviewers see it
  const mineIx = [...Q.keys()].filter((ix) => !Q[ix].assigned_to?.length || Q[ix].assigned_to.includes(S.coder));
  S.order = seededOrder(mineIx.length, S.coder).map((j) => mineIx[j]);
  S.i = 0;
  try { localStorage.setItem("pt-last-coder", S.coder); } catch { /* storage unavailable */ }
  $("#who").textContent = `${S.coder}: ${S.task === "extraction" ? "checking the promise list" : `rating as of ${S.period}`}`;
  $("#setup").hidden = true; $("#work").hidden = false;
  $("#ref").innerHTML = S.task === "extraction"
    ? `<ul><li><strong>Drop</strong> if the statement isn't the candidate's own words, was made after Election Day, or is too vague to test.</li>
       <li><strong>Merge</strong> if another promise says the same thing; keep the one from the more authoritative source.</li>
       <li><strong>Quote doesn't match</strong> if any word differs, or an ellipsis removes an amount, date, condition or limit.</li></ul>`
    : `<ul><li>Judge against the candidate's own wording: amounts, dates, scope.</li>
       <li>A missed deadline in the promise makes it Broken, even if work continues.</li>
       <li>Effort: rate the highest level reached. Undermined overrides everything.</li>
       <li>If you can't tell In progress from Not yet rated, choose Not yet rated.</li></ul>`;
  render();
});

$("#todo-only").addEventListener("change", () => { S.i = 0; render(); });
$("#export").onclick = exportCsv;
$("#change").onclick = () => { $("#work").hidden = true; $("#setup").hidden = false; };

document.addEventListener("keydown", (e) => {
  if ($("#work").hidden || ["TEXTAREA", "INPUT"].includes(document.activeElement.tagName) && document.activeElement.type !== "radio") {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !$("#work").hidden) $("#rate")?.requestSubmit();
    return;
  }
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { $("#rate")?.requestSubmit(); return; }
  const n = Number(e.key);
  if (!n) return;
  const sets = [...document.querySelectorAll("#rate fieldset:not([hidden])")].filter((fs) => fs.id !== "blocker-wrap");
  const open = sets.find((fs) => !fs.querySelector("input:checked")) || null;
  const opt = open && open.querySelectorAll("input[type=radio]")[n - 1];
  if (opt) { opt.checked = true; opt.dispatchEvent(new Event("change", { bubbles: true })); }
});

fetch("pledges.json").then((r) => r.json()).then((d) => {
  Q = d.pledges; codebookVersion = d.codebook_version;
  const dl = document.createElement("datalist"); dl.id = "ids";
  dl.innerHTML = Q.map((p) => `<option value="${esc(p.pledge_id)}">`).join("");
  document.body.append(dl);
  try { $("#coder").value = localStorage.getItem("pt-last-coder") || ""; } catch { /* storage unavailable */ }
}).catch(() => {
  $("#setup").insertAdjacentHTML("afterbegin", `<div class="notice" role="alert"><p>The promise list didn't load. Run <code>python3 scripts/build.py</code>, then reload.</p></div>`);
});
