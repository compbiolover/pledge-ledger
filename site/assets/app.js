// Promise Tracker public site. No build step, no dependencies.
// Edit REPO if the GitHub repository has a different name.
const REPO = "compbiolover/promise-tracker";

const OUTCOME = {
  kept: "Kept", partial: "Partially kept", in_progress: "In progress",
  broken: "Broken", not_rated: "Not yet rated",
};
const OUTCOME_ORDER = ["kept", "partial", "in_progress", "broken", "not_rated"];
const OUTCOME_HELP = {
  kept: "The action or outcome happened as worded.",
  partial: "Some of what was promised happened, but less, later or narrower.",
  in_progress: "A formal step is underway, with no final result yet.",
  broken: "Rejected, reversed, made impossible, or a stated deadline passed.",
  not_rated: "No formal step yet, or the rating is still being reviewed.",
};
const EFFORT = {
  "-1": "Undermined", "0": "No action", "1": "Talk only", "2": "Formal start",
  "3": "Spent political capital", "4": "Tried every option",
};
const EFFORT_HELP = {
  "-1": "Backed something contrary, or walked the promise back.",
  "0": "No public action in the period.",
  "1": "Speeches, interviews or posts, with no formal step.",
  "2": "A bill, executive order, budget request, rule or appointment.",
  "3": "Used leverage: a veto, a special session, tying it to the budget, or public pressure on holdouts.",
  "4": "Used every tool available, including executive action, a ballot measure or a lawsuit.",
};
const BLOCKER = {
  none_attempted: "Not attempted", legislature_opposition: "Opposing party in the legislature",
  legislature_own_party: "Governor's own party in the legislature", courts: "Courts",
  federal: "Federal government", voters: "Voters", budget: "Budget shortfall",
  self_reversed: "Governor changed position", too_early: "Too early to tell",
};
const AREA = {
  economy_tax: "Economy and taxes", budget: "Budget", education: "Education", health: "Health",
  housing: "Housing", criminal_justice: "Criminal justice", immigration: "Immigration",
  environment_energy: "Energy and environment", infrastructure_transport: "Infrastructure",
  labor: "Jobs and labor", social_services: "Social services", elections_democracy: "Elections",
  government_ethics: "Government and ethics", agriculture_rural: "Agriculture and rural",
  guns: "Guns", reproductive_rights: "Reproductive rights", civil_rights: "Civil rights",
  technology: "Technology", other: "Other",
};
const SOURCE = {
  campaign_site: "Campaign website or platform", campaign_release: "Campaign release",
  debate: "Debate or forum", news_quote: "Direct quote in news coverage",
};
const INSTRUMENT = {
  bill: "Legislation", executive_order: "Executive order", budget: "Budget",
  appointment: "Appointment", administrative: "Administrative action",
  ballot_measure: "Ballot measure", mixed: "Several instruments", unclear: "Unclear",
};
const FLAG = {
  check_wording: "Quote rebuilt from pieces; wording being checked",
  provisional_race: "Race not yet final",
  possible_duplicate: "May duplicate another promise",
  post_election: "Made after Election Day; under review",
  not_direct_quote: "Reprinted by a news outlet, not a direct quote",
  over_40_words: "Long quote",
  ellipsis_drops_qualifier: "Ellipsis drops a condition; under review",
  needs_context: "Needs surrounding context",
  source_affiliation_unconfirmed: "Source site's link to the campaign is unconfirmed",
};
const COHORT = { D_flip: "Democrat, flipped a Republican-held seat", R_open_seat: "Republican, won an open seat" };

// ---------- helpers ----------
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x) => (x == null ? "—" : `${Math.round(x * 100)}%`);
const params = new URLSearchParams(location.search);
const cache = {};
async function load(name) {
  if (!cache[name]) cache[name] = fetch(`data/${name}.json`).then((r) => {
    if (!r.ok) throw new Error(`Could not load ${name}.json (${r.status})`);
    return r.json();
  });
  return cache[name];
}
const safeStatus = (o) => (OUTCOME[o] ? o : "not_rated");
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
const mark = (o) => `<span class="mark s-${safeStatus(o)}" aria-hidden="true"></span>`;
const chip = (o) => `<span class="chip">${mark(o)}${OUTCOME[o]}</span>`;
const fmtDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
  return isNaN(d) ? iso : d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
};
const waybackDate = (ts) => (ts && ts.length >= 8 ? fmtDate(`${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)}`) : "");
const byStatus = (a, b) => OUTCOME_ORDER.indexOf(a.current.outcome) - OUTCOME_ORDER.indexOf(b.current.outcome)
  || a.policy_area.localeCompare(b.policy_area) || a.pledge_id.localeCompare(b.pledge_id, undefined, { numeric: true });
const issueUrl = (title, body) => `https://github.com/${REPO}/issues/new?${new URLSearchParams({ title, body, labels: "appeal" })}`;
const legend = () => `<ul class="legend" aria-label="Status key">${OUTCOME_ORDER.map((o) => `<li>${mark(o)}${OUTCOME[o]}</li>`).join("")}</ul>`;

function strip(pledges) {
  return `<div class="strip" aria-hidden="true">${[...pledges].sort(byStatus).map((p) =>
    `<a class="s-${safeStatus(p.current.outcome)}" href="promise.html?id=${encodeURIComponent(p.pledge_id)}" tabindex="-1"
      title="${esc(`${OUTCOME[p.current.outcome]}. ${AREA[p.policy_area] || p.policy_area}: ${p.pledge_text.slice(0, 110)}${p.pledge_text.length > 110 ? "…" : ""}`)}"></a>`).join("")}</div>`;
}

const pendingWhy = (st) => (st === "disputed" ? "The two reviewers disagreed. A third reviewer is deciding." : "Waiting for the second reviewer.");

function statusSentence(s) {
  if (!s.rated) return `${s.n} promises. None rated yet.`;
  return `${s.n} promises. ${s.outcomes.kept} kept, ${s.outcomes.partial} partially kept, ${s.outcomes.in_progress} in progress, ${s.outcomes.broken} broken, ${s.outcomes.not_rated} not yet rated.`;
}

// ---------- pages ----------
async function home() {
  const [officials, pledges, meta] = await Promise.all([load("officials"), load("pledges"), load("meta")]);
  const active = pledges.filter((p) => p.active);
  const rated = active.filter((p) => p.current.outcome !== "not_rated").length;
  $("#facts").innerHTML = `
    <div><dt>Promises tracked</dt><dd class="num">${active.length}</dd></div>
    <div><dt>Governors</dt><dd class="num">${officials.length}</dd></div>
    <div><dt>Rated so far</dt><dd class="num">${rated}<small>${rated ? `as of ${fmtDate(meta.latest_period)}` : "First ratings after inauguration"}</small></dd></div>`;
  $("#legend").innerHTML = legend();
  const groups = [["D_flip", "Democrats who flipped a seat"], ["R_open_seat", "Republicans who won an open seat"]];
  $("#roster").innerHTML = groups.map(([cohort, title]) => {
    const offs = officials.filter((o) => o.cohort === cohort);
    const n = offs.reduce((a, o) => a + o.summary.n, 0);
    return `<div class="group-head"><h2>${title}</h2><span class="muted small num">${offs.length} governors, ${n} promises</span></div>
      <ul class="roster">${offs.map((o) => {
        const mine = active.filter((p) => p.official_id === o.official_id);
        return `<li>
          <div class="who"><a href="governor.html?id=${o.official_id}">${esc(o.name)}</a>
            <span class="meta">${esc(o.state_name)} (${o.party})${o.provisional === "Y" ? ". Race not final" : ""}</span></div>
          ${strip(mine)}
          <p class="strip-note">${statusSentence(o.summary)} <a href="governor.html?id=${o.official_id}">See ${esc(o.name.split(" ").slice(-1)[0])}'s promises</a></p>
        </li>`;
      }).join("")}</ul>`;
  }).join("");
}

function filterBar(pledges, officials, opts = {}) {
  const areas = [...new Set(pledges.map((p) => p.policy_area))].sort((a, b) => (AREA[a] || a).localeCompare(AREA[b] || b));
  const sel = (id, label, items, val) => `<label>${label}<select id="${id}"><option value="">All</option>${items.map(([v, t]) => `<option value="${esc(v)}"${val === v ? " selected" : ""}>${esc(t)}</option>`).join("")}</select></label>`;
  return `<form class="filters" role="search" onsubmit="return false">
    <label>Search the promises<input type="search" id="q" value="${esc(params.get("q") || "")}" placeholder="e.g. grocery tax, teacher pay"></label>
    ${opts.noGovernor ? "" : sel("gov", "Governor", officials.map((o) => [o.official_id, `${o.name} (${o.state})`]), params.get("gov") || "")}
    ${sel("area", "Topic", areas.map((a) => [a, AREA[a] || a]), params.get("area") || "")}
    ${sel("status", "Status", OUTCOME_ORDER.map((o) => [o, OUTCOME[o]]), params.get("status") || "")}
    ${sel("src", "Source", Object.entries(SOURCE), params.get("src") || "")}
  </form>
  <p class="count" id="count" aria-live="polite"></p>
  <ol class="plist" id="plist"></ol>
  <p><button type="button" id="more" hidden>Show more</button></p>`;
}

function wireList(all, officials, scopeGov) {
  const offName = Object.fromEntries(officials.map((o) => [o.official_id, o]));
  let shown = 60;
  const read = () => ({ q: $("#q").value.trim().toLowerCase(), gov: scopeGov || ($("#gov")?.value ?? ""),
    area: $("#area").value, status: $("#status").value, src: $("#src").value });
  function render(resetShown) {
    if (resetShown) shown = 60;
    const f = read();
    const words = f.q.split(/\s+/).filter(Boolean);
    const list = all.filter((p) => (!f.gov || p.official_id === f.gov) && (!f.area || p.policy_area === f.area)
      && (!f.status || p.current.outcome === f.status) && (!f.src || p.source_type === f.src)
      && words.every((w) => `${p.pledge_text} ${p.pledge_id} ${AREA[p.policy_area]}`.toLowerCase().includes(w)));
    $("#count").textContent = `${list.length} of ${all.length} promises`;
    $("#plist").innerHTML = list.slice(0, shown).map((p) => {
      const o = offName[p.official_id];
      return `<li>
        <p class="quote">${esc(p.pledge_text)}</p>
        <div class="row">${chip(p.current.outcome)}
          ${scopeGov ? "" : `<span>${esc(o.name)} (${o.state})</span>`}
          <span>${esc(AREA[p.policy_area] || p.policy_area)}</span>
          <a href="promise.html?id=${encodeURIComponent(p.pledge_id)}">Details for ${esc(p.pledge_id)}</a></div>
      </li>`;
    }).join("") || `<li><p>No promises match. Try fewer words, or set a filter back to All.</p></li>`;
    $("#more").hidden = list.length <= shown;
    if (!scopeGov) {
      const u = new URLSearchParams(Object.entries(f).filter(([, v]) => v));
      history.replaceState(null, "", `${location.pathname}${u.toString() ? "?" + u : ""}`);
    }
  }
  ["q", "gov", "area", "status", "src"].forEach((id) => {
    const n = $("#" + id);
    if (n) n.addEventListener(id === "q" ? "input" : "change", () => render(true));
  });
  $("#more").addEventListener("click", () => { shown += 60; render(false); });
  render(true);
}

async function promises() {
  const [officials, pledges] = await Promise.all([load("officials"), load("pledges")]);
  const all = pledges.filter((p) => p.active).sort((a, b) => a.pledge_id.localeCompare(b.pledge_id, undefined, { numeric: true }));
  $("#browse").innerHTML = filterBar(all, officials);
  wireList(all, officials, null);
}

async function governor() {
  const [officials, pledges] = await Promise.all([load("officials"), load("pledges")]);
  const o = officials.find((x) => x.official_id === params.get("id"));
  if (!o) { $("#gov-main").innerHTML = `<h1>Governor not found</h1><p><a href="index.html">Go back to all governors</a>.</p>`; return; }
  document.title = `${o.name}'s promises | Governor Promise Tracker`;
  const mine = pledges.filter((p) => p.official_id === o.official_id && p.active)
    .sort((a, b) => a.pledge_id.localeCompare(b.pledge_id, undefined, { numeric: true }));
  const s = o.summary;
  const g = s.effort_outcome_grid;
  const cell = (ob, band) => g[`${ob}|${band}`] || 0;
  const areaRows = Object.entries(o.policy_areas).map(([a, n]) => {
    const inA = mine.filter((p) => p.policy_area === a);
    const k = inA.filter((p) => ["kept", "partial"].includes(p.current.outcome)).length;
    return `<tr><td>${esc(AREA[a] || a)}</td><td class="n">${n}</td><td class="n">${s.rated ? k : "—"}</td></tr>`;
  }).join("");
  $("#gov-main").innerHTML = `
    <p class="crumbs"><a href="index.html">All governors</a></p>
    <h1>${esc(o.name)}</h1>
    <p class="lead">Governor-elect of ${esc(o.state_name)}. ${esc(COHORT[o.cohort] || "")}.${o.provisional === "Y" ? ` <strong>The race is not final:</strong> ${esc(o.notes)}.` : ""}</p>
    <dl class="facts">
      <div><dt>Promises tracked</dt><dd class="num">${s.n}</dd></div>
      <div><dt>Rated</dt><dd class="num">${s.rated}</dd></div>
      <div><dt>Kept or partially kept</dt><dd class="num">${s.rated ? pct(s.kept_or_partial_share) : "—"}${s.rated && s.kept_or_partial_ci95 ? `<small>95% range ${pct(s.kept_or_partial_ci95[0])} to ${pct(s.kept_or_partial_ci95[1])}</small>` : "<small>After the first review</small>"}</dd></div>
    </dl>
    ${legend()}
    ${strip(mine)}
    <h2>Effort and results</h2>
    <p>Each promise gets two separate ratings: what happened, and how hard the governor pushed. Reading them together separates a promise that was fought for and blocked from one that was never tried.</p>
    <div class="eo" role="table" aria-label="Promises by effort and outcome">
      <div class="h" role="columnheader"></div><div class="h" role="columnheader">Low effort</div><div class="h" role="columnheader">High effort</div><div class="h" role="columnheader">Effort under review</div>
      <div class="h" role="rowheader">Kept or partly</div>
        <div class="cell" role="cell">${cell("kept", "low")}<span>easy win</span></div><div class="cell" role="cell">${cell("kept", "high")}<span>delivered</span></div><div class="cell" role="cell">${cell("kept", "unrated")}</div>
      <div class="h" role="rowheader">Broken</div>
        <div class="cell flag" role="cell">${cell("not_kept", "low")}<span>never really tried</span></div><div class="cell" role="cell">${cell("not_kept", "high")}<span>fought and blocked</span></div><div class="cell" role="cell">${cell("not_kept", "unrated")}</div>
      <div class="h" role="rowheader">Still open</div>
        <div class="cell" role="cell">${cell("open", "low")}</div><div class="cell" role="cell">${cell("open", "high")}</div><div class="cell" role="cell">${cell("open", "unrated")}</div>
    </div>
    <p class="small muted">Low effort means no action or talk only. High effort means a formal step or more. ${cell("kept", "undermined") + cell("not_kept", "undermined") + cell("open", "undermined")} promises were undermined by the governor's own actions.</p>
    <h2>Power in the statehouse</h2>
    ${o.power_context.length ? `<div class="table-wrap"><table><thead><tr><th>Session</th><th>Trifecta</th><th>House majority</th><th>Senate majority</th><th>Veto override</th></tr></thead><tbody>${o.power_context.map((pc) => `<tr><td>${esc(pc.session)}</td><td>${esc(pc.trifecta)}</td><td>${esc(pc.house_majority)}</td><td>${esc(pc.senate_majority)}</td><td>${esc(pc.veto_override_threshold)}</td></tr>`).join("")}</tbody></table></div>`
      : `<div class="notice"><p>Legislative control for the 2027 session will be added once results are certified. Whether a governor's party controls the legislature changes what they can deliver, so every comparison on this site shows it.</p></div>`}
    <h2>Promises by topic</h2>
    <div class="table-wrap"><table><thead><tr><th>Topic</th><th class="n">Promises</th><th class="n">Kept or partly</th></tr></thead><tbody>${areaRows}</tbody></table></div>
    <h2>Every promise</h2>
    <div id="browse"></div>`;
  $("#browse").innerHTML = filterBar(mine, officials, { noGovernor: true });
  wireList(mine, officials, o.official_id);
}

async function promise() {
  const [officials, pledges] = await Promise.all([load("officials"), load("pledges")]);
  const p = pledges.find((x) => x.pledge_id === params.get("id"));
  const main = $("#p-main");
  if (!p) { main.innerHTML = `<h1>Promise not found</h1><p>Check the link, or <a href="promises.html">search all promises</a>.</p>`; return; }
  const o = officials.find((x) => x.official_id === p.official_id);
  document.title = `${p.pledge_id}: ${o.name} | Governor Promise Tracker`;
  const c = p.current;
  const rated = c.outcome !== "not_rated" && c.as_of;
  const latest = p.history[p.history.length - 1];
  const verdict = rated ? `
    <div class="verdict">
      <div><p class="k">What happened</p><p class="v">${mark(c.outcome)}${OUTCOME[c.outcome]}</p><p class="d">${OUTCOME_HELP[c.outcome]}</p></div>
      <div><p class="k">Governor's effort</p><p class="v">${c.effort != null ? esc(EFFORT[c.effort]) : "Under review"}</p><p class="d">${c.effort != null ? EFFORT_HELP[c.effort] : pendingWhy(latest.effort_state)}</p></div>
      ${c.outcome !== "kept" ? `<div><p class="k">What stood in the way</p><p class="v">${c.blocker ? esc(BLOCKER[c.blocker]) : "Under review"}</p>${c.blocker ? "" : `<p class="d">${pendingWhy(latest.blocker_state)}</p>`}</div>` : ""}
    </div>
    <p class="small muted">Rated as of ${fmtDate(c.as_of)} by two independent reviewers${latest.adjudication_notes.length ? ", with a third settling a disagreement" : ""}.${c.in_review ? " A newer review is in progress." : ""}</p>
    ${latest.adjudication_notes.length ? `<p class="small"><strong>Why the tie-breaker decided this way:</strong> ${latest.adjudication_notes.map(esc).join(" ")}</p>` : ""}
    <h2>Evidence</h2>
    ${latest.evidence.length ? `<ol>${latest.evidence.map((e) => `<li><a href="${esc(safeUrl(e.url))}" rel="noopener">${esc(e.url.replace(/^https?:\/\//, "").slice(0, 90))}</a>${e.cited_by < 2 ? ` <span class="small muted">(cited by one reviewer)</span>` : ""}</li>`).join("")}</ol>` : "<p>No evidence links recorded.</p>"}`
    : `<div class="notice"><p><strong>Not yet rated.</strong> ${c.in_review ? "Two reviewers are working on the first rating." : "Ratings start after the governor takes office in January 2027. The first review covers the first 100 days."}</p></div>`;
  main.innerHTML = `
    <p class="crumbs"><a href="index.html">All governors</a> / <a href="governor.html?id=${o.official_id}">${esc(o.name)}</a> / ${esc(p.pledge_id)}</p>
    <p class="quote quote-lg">${esc(p.pledge_text)}</p>
    <p class="muted">${esc(o.name)}, ${esc(SOURCE[p.source_type] || p.source_type).toLowerCase()}. ${esc(AREA[p.policy_area] || p.policy_area)}.</p>
    ${p.review_flags.length ? `<ul class="flags" aria-label="Review notes">${p.review_flags.map((f) => `<li>${esc(FLAG[f] || f)}</li>`).join("")}</ul>` : ""}
    ${!p.active ? `<div class="notice"><p>This promise was ${p.merged_into ? `merged into <a href="promise.html?id=${esc(p.merged_into)}">${esc(p.merged_into)}</a> as a duplicate` : "removed from the tracker after review"}.</p></div>` : ""}
    ${verdict}
    ${p.history.length > 1 ? `<h2>How the rating changed</h2><ol class="timeline">${p.history.map((h) => `<li><strong>${fmtDate(h.period_end)}</strong>: ${OUTCOME[h.outcome]}${h.effort != null ? `, ${EFFORT[h.effort]?.toLowerCase()}` : ""}</li>`).join("")}</ol>` : ""}
    <h2>Where this promise comes from</h2>
    <dl class="kv">
      <dt>Source</dt><dd><a href="${esc(safeUrl(p.source_url))}" rel="noopener">${esc(p.source_title || p.source_url)}</a></dd>
      <dt>Saved copy</dt><dd>${p.archive_url ? `<a href="${esc(safeUrl(p.archive_url))}" rel="noopener">Wayback Machine, ${waybackDate(p.archive_timestamp)}</a>` : "Not archived yet"}</dd>
      <dt>Page fingerprint</dt><dd class="small"><code>${esc(p.sha256 || "—")}</code></dd>
      <dt>How it gets done</dt><dd>${esc(INSTRUMENT[p.instrument] || p.instrument)}</dd>
      <dt>Needs others to act</dt><dd>${p.requires_other_actor === "Y" ? "Yes. The governor can't do this alone" : "No. Within the governor's own power"}</dd>
      <dt>Keeps things as they are</dt><dd>${p.status_quo === "Y" ? "Yes" : "No, it changes something"}</dd>
      ${p.extractor_notes ? `<dt>Notes</dt><dd>${esc(p.extractor_notes)}</dd>` : ""}
    </dl>
    <h2>Think we got this wrong?</h2>
    <p>Anyone can ask us to review a rating or a quote, including the governor's office. Every request and our answer is public.</p>
    <p><a class="btn" href="${issueUrl(`Review request: ${p.pledge_id}`, `Promise: ${p.pledge_id}\nCurrent rating: ${OUTCOME[c.outcome]}\n\nWhat should change, and the evidence for it:\n`)}" rel="noopener">Ask for a review</a></p>`;
}

async function compare() {
  const [officials, summary, pledges] = await Promise.all([load("officials"), load("summary"), load("pledges")]);
  const active = pledges.filter((p) => p.active);
  const rated = active.some((p) => p.current.outcome !== "not_rated");
  const cohorts = [["D", "Democrats who flipped a seat"], ["R", "Republicans who won an open seat"]];
  // composition: what each side promised
  const areas = Object.keys(AREA).filter((a) => active.some((p) => p.policy_area === a));
  const share = (party, pred) => {
    const ids = new Set(officials.filter((o) => o.party === party).map((o) => o.official_id));
    const mine = active.filter((p) => ids.has(p.official_id));
    return mine.length ? mine.filter(pred).length / mine.length : 0;
  };
  const rows = areas.map((a) => [a, share("D", (p) => p.policy_area === a), share("R", (p) => p.policy_area === a)])
    .sort((x, y) => (y[1] + y[2]) - (x[1] + x[2]));
  $("#cmp").innerHTML = `
    ${rated ? `<h2>How much each side delivered</h2>${dotChart(officials)}
      <div class="table-wrap"><table><thead><tr><th>Group</th><th class="n">Promises</th><th class="n">Kept or partly, all promises pooled</th><th class="n">Average of each governor's rate</th></tr></thead><tbody>
      ${cohorts.map(([k, t]) => { const c = summary.cohorts[k]; return `<tr><td>${t}</td><td class="n">${c.pooled.n}</td><td class="n">${pct(c.pooled.kept_or_partial_share)} (${pct(c.pooled.kept_or_partial_ci95?.[0])} to ${pct(c.pooled.kept_or_partial_ci95?.[1])})</td><td class="n">${pct(c.mean_of_officials_kept_or_partial)}</td></tr>`; }).join("")}
      </tbody></table></div>
      <p class="small muted">Pooled rates weight governors with longer platforms more. The average of each governor's rate weights every governor equally. Ranges are 95% Wilson intervals.</p>`
    : `<div class="notice"><p><strong>Nothing to compare yet.</strong> Delivery comparisons appear after the first review, about 100 days after inauguration. Until then, here is what each side promised.</p></div>`}
    <h2>What each side promised</h2>
    <p>Share of each group's promises in each topic.</p>
    <div class="table-wrap"><table><thead><tr><th>Topic</th><th class="n">Democrats</th><th class="n">Republicans</th></tr></thead><tbody>
      ${rows.map(([a, d, r]) => `<tr><td>${esc(AREA[a])}</td><td class="n">${pct(d)}</td><td class="n">${pct(r)}</td></tr>`).join("")}
      <tr><td><strong>Needs the legislature or others to act</strong></td><td class="n">${pct(share("D", (p) => p.requires_other_actor === "Y"))}</td><td class="n">${pct(share("R", (p) => p.requires_other_actor === "Y"))}</td></tr>
      <tr><td><strong>Keeps things as they are</strong></td><td class="n">${pct(share("D", (p) => p.status_quo === "Y"))}</td><td class="n">${pct(share("R", (p) => p.status_quo === "Y"))}</td></tr>
    </tbody></table></div>
    <p class="small muted">Democrats made ${summary.cohorts.D.pooled.n} trackable promises and Republicans ${summary.cohorts.R.pooled.n}. A count only includes statements specific enough to check, so it partly measures how specific a platform was.</p>`;
}

function dotChart(officials) {
  const rows = officials.filter((o) => o.summary.rated).sort((a, b) => a.party.localeCompare(b.party) || (b.summary.kept_or_partial_share - a.summary.kept_or_partial_share));
  const W = 640, L = 190, R = 20, rowH = 30, H = rows.length * rowH + 30;
  const x = (v) => L + v * (W - L - R);
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  return `<figure class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Share of each governor's promises kept or partially kept, with 95% ranges">
    ${ticks.map((t) => `<line x1="${x(t)}" x2="${x(t)}" y1="0" y2="${H - 24}" stroke="#d5dae0"/><text x="${x(t)}" y="${H - 6}" text-anchor="middle">${t * 100}%</text>`).join("")}
    ${rows.map((o, i) => { const y = i * rowH + 16, s = o.summary, ci = s.kept_or_partial_ci95 || [s.kept_or_partial_share, s.kept_or_partial_share];
      return `<text class="lbl" x="0" y="${y + 4}">${esc(o.name)} (${o.party})</text>
        <line x1="${x(ci[0])}" x2="${x(ci[1])}" y1="${y}" y2="${y}" stroke="#1d2733" stroke-width="2"/>
        <circle cx="${x(s.kept_or_partial_share)}" cy="${y}" r="5" fill="${o.party === "D" ? "#1d2733" : "#ffffff"}" stroke="#1d2733" stroke-width="2"><title>${esc(o.name)}: ${pct(s.kept_or_partial_share)} of ${s.n}</title></circle>`; }).join("")}
  </svg><figcaption class="small muted">Dot: share kept or partially kept. Line: 95% range. Filled dots are Democrats, open dots Republicans.</figcaption></figure>`;
}

async function methods() {
  const [rel, meta] = await Promise.all([load("reliability"), load("meta")]);
  $("#rel").innerHTML = rel.fields.length
    ? `<div class="table-wrap"><table><thead><tr><th>Task</th><th>Field</th><th class="n">Promises rated by both</th><th class="n">Agreement</th><th class="n">Kappa</th></tr></thead><tbody>
      ${rel.fields.map((f) => `<tr><td>${f.task === "status" ? "Status" : "Extraction review"}</td><td>${esc(f.field.replace("_", " "))}</td><td class="n">${f.n}</td><td class="n">${pct(f.percent_agreement)}</td><td class="n">${f.kappa ?? "—"}</td></tr>`).join("")}
      </tbody></table></div><p class="small muted">Target kappa is ${rel.target_kappa} or higher. Effort uses quadratic-weighted kappa because it is an ordered scale.</p>`
    : `<div class="notice"><p>No double-coded ratings yet. Agreement scores appear here as soon as two reviewers have rated the same promises.</p></div>`;
  $("#codebook-link").href = `https://github.com/${REPO}/blob/main/codebook/CODEBOOK.md`;
  $("#data-link").href = `https://github.com/${REPO}/tree/main/data`;
  $("#built").textContent = `Codebook version ${meta.codebook_version}. Data built ${fmtDate(meta.built)}.`;
}

const pages = { home, promises, governor, promise, compare, methods };
const page = document.body.dataset.page;
(pages[page] || (async () => {}))().catch((e) => {
  const m = document.querySelector("main");
  m.insertAdjacentHTML("afterbegin", `<div class="notice" role="alert"><p>The data didn't load: ${esc(e.message)}. Reload the page, and if it keeps happening, run <code>python3 scripts/build.py</code>.</p></div>`);
});
