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
const EFFORT_HELP_SENATE = {
  "-1": "Voted against it, backed something contrary, or walked the promise back.",
  "0": "No public action in the period.",
  "1": "Speeches, interviews or posts, with no formal step.",
  "2": "Introduced or cosponsored a bill, offered an amendment, or voted as promised.",
  "3": "Led the effort: got a hearing, whipped votes, used Senate procedure, or pressured named holdouts.",
  "4": "Tried every route: a standalone bill, an amendment to must-pass legislation, funding riders and procedural pressure.",
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
  legislature_own_party: "Their own party in the legislature", courts: "Courts",
  federal: "Federal government", voters: "Voters", budget: "Budget shortfall",
  self_reversed: "Changed position", too_early: "Too early to tell",
  other_chamber: "The House", president: "The president", filibuster: "Filibuster",
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
  sponsor_bill: "Introducing or backing a bill", vote: "A vote", appropriations: "Federal funding",
  oversight: "Oversight of agencies", nomination: "Confirming or blocking nominees", constituent_service: "Work for constituents",
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
  pre_election_unverified: "No copy saved before Election Day; wording could have changed since",
  pre_election_mismatch: "Differs from the copy saved before Election Day; under review",
  not_own_commitment: "Says what should happen, not what they will do; under review",
  possibly_already_done: "May already have happened before they took office",
  source_unavailable: "Original page is gone and was never archived; quote corroborated elsewhere",
};
const COHORT = { D_flip: "Democrat, flipped a Republican-held seat", D_open_seat: "Democrat, won an open seat", R_open_seat: "Republican, won an open seat" };
const OFFICE = {
  Governor: { plural: "Governors", elect: "Governor-elect of", from: "of", title: "governor",
    groups: [["D_flip", "Democrats who flipped a seat"], ["R_open_seat", "Republicans who won an open seat"]] },
  Senator: { plural: "Senators", elect: "Senator-elect from", from: "from", title: "senator",
    groups: [["D_flip", "Democrats who flipped a seat"], ["D_open_seat", "Democrats who won an open seat"], ["R_open_seat", "Republicans who won an open seat"]] },
};
const effortHelp = (e, office) => (office === "Senator" ? EFFORT_HELP_SENATE : EFFORT_HELP)[e];

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
const issueUrl = (pid = "") => `https://github.com/${REPO}/issues/new?${new URLSearchParams({ template: "review.yml", title: `Review request: ${pid}`, pledge_id: pid })}`;
const PREREG_URL = `https://github.com/${REPO}/blob/main/PREREGISTRATION.md`;
const CORRECTION_KIND = { quote: "Quote", source: "Source", rating: "Rating", metadata: "Details", other: "Other" };
const legend = () => `<ul class="legend" aria-label="Status key">${OUTCOME_ORDER.map((o) => `<li>${mark(o)}${OUTCOME[o]}</li>`).join("")}</ul>`;

function strip(pledges) {
  return `<div class="strip" aria-hidden="true">${[...pledges].sort(byStatus).map((p) =>
    `<a class="s-${safeStatus(p.current.outcome)}" href="promise.html?id=${encodeURIComponent(p.pledge_id)}" tabindex="-1"
      title="${esc(`${OUTCOME[p.current.outcome]}. ${AREA[p.policy_area] || p.policy_area}: ${p.pledge_text.slice(0, 110)}${p.pledge_text.length > 110 ? "…" : ""}`)}"></a>`).join("")}</div>`;
}

const pendingWhy = (st) => (st === "disputed" ? "The two reviewers disagreed. A third reviewer is deciding." : "Waiting for the second reviewer.");

function statusSentence(s, office) {
  if (!s.rated) return `${s.n} promises. None rated yet.`;
  if (office === "Senator") return `${s.n} promises. Took formal action on ${pct(s.acted_share)} of those rated. ${s.outcomes.kept} kept, ${s.outcomes.partial} partially kept, ${s.outcomes.broken} broken.`;
  return `${s.n} promises. ${s.outcomes.kept} kept, ${s.outcomes.partial} partially kept, ${s.outcomes.in_progress} in progress, ${s.outcomes.broken} broken, ${s.outcomes.not_rated} not yet rated.`;
}

// ---------- pages ----------
async function home() {
  const [officials, pledges, meta] = await Promise.all([load("officials"), load("pledges"), load("meta")]);
  const active = pledges.filter((p) => p.active);
  const rated = active.filter((p) => p.current.outcome !== "not_rated").length;
  const count = (office) => officials.filter((o) => o.office === office).length;
  $("#facts").innerHTML = `
    <div><dt>Promises tracked</dt><dd class="num">${active.length}</dd></div>
    <div><dt>Governors</dt><dd class="num">${count("Governor")}</dd></div>
    <div><dt>Senators</dt><dd class="num">${count("Senator")}</dd></div>
    <div><dt>Rated so far</dt><dd class="num">${rated}<small>${rated ? `as of ${fmtDate(meta.latest_period)}` : "First ratings after January 2027"}</small></dd></div>`;
  $("#legend").innerHTML = legend();
  $("#roster").innerHTML = Object.entries(OFFICE).map(([office, cfg]) => {
    const inOffice = officials.filter((o) => o.office === office);
    if (!inOffice.length) return "";
    const n = inOffice.reduce((a, o) => a + o.summary.n, 0);
    return `<section aria-labelledby="h-${office}"><h2 class="office-head" id="h-${office}">${cfg.plural} <span class="muted small num">${inOffice.length} people, ${n} promises</span></h2>
    ${office === "Senator" ? `<p class="small muted">A senator can rarely pass a law alone, so senators are rated first on what they did, then on what happened.</p>` : ""}
    ${cfg.groups.map(([cohort, title]) => {
      const offs = inOffice.filter((o) => o.cohort === cohort);
      if (!offs.length) return "";
      return `<div class="group-head"><h3>${title}</h3><span class="muted small num">${offs.length} ${offs.length === 1 ? cfg.title : cfg.title + "s"}, ${offs.reduce((a, o) => a + o.summary.n, 0)} promises</span></div>
      <ul class="roster">${offs.map((o) => {
        const mine = active.filter((p) => p.official_id === o.official_id);
        return `<li>
          <div class="who"><a href="official.html?id=${encodeURIComponent(o.official_id)}">${esc(o.name)}</a>
            <span class="meta">${esc(o.state_name)} (${o.party})${o.provisional === "Y" ? ". Race not final" : ""}</span></div>
          ${strip(mine)}
          <p class="strip-note">${statusSentence(o.summary, o.office)} <a href="official.html?id=${encodeURIComponent(o.official_id)}">See ${esc(o.name.split(" ").slice(-1)[0])}'s promises</a></p>
        </li>`;
      }).join("")}</ul>`;
    }).join("")}</section>`;
  }).join("");
}

function filterBar(pledges, officials, opts = {}) {
  const areas = [...new Set(pledges.map((p) => p.policy_area))].sort((a, b) => (AREA[a] || a).localeCompare(AREA[b] || b));
  const sel = (id, label, items, val) => `<label>${label}<select id="${id}"><option value="">All</option>${items.map(([v, t]) => `<option value="${esc(v)}"${val === v ? " selected" : ""}>${esc(t)}</option>`).join("")}</select></label>`;
  return `<form class="filters" role="search" onsubmit="return false">
    <label>Search the promises<input type="search" id="q" value="${esc(params.get("q") || "")}" placeholder="e.g. grocery tax, teacher pay"></label>
    ${opts.noGovernor ? "" : sel("office", "Office", Object.entries(OFFICE).map(([k, c]) => [k, c.plural]), params.get("office") || "")}
    ${opts.noGovernor ? "" : sel("gov", "Person", officials.map((o) => [o.official_id, `${o.name} (${o.office === "Senator" ? "Sen." : "Gov."}, ${o.state})`]), params.get("gov") || "")}
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
  const read = () => ({ q: $("#q").value.trim().toLowerCase(), office: $("#office")?.value ?? "", gov: scopeGov || ($("#gov")?.value ?? ""),
    area: $("#area").value, status: $("#status").value, src: $("#src").value });
  function render(resetShown) {
    if (resetShown) shown = 60;
    const f = read();
    const words = f.q.split(/\s+/).filter(Boolean);
    const list = all.filter((p) => (!f.office || offName[p.official_id].office === f.office) && (!f.gov || p.official_id === f.gov) && (!f.area || p.policy_area === f.area)
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
  ["q", "office", "gov", "area", "status", "src"].forEach((id) => {
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

async function official() {
  const [officials, pledges] = await Promise.all([load("officials"), load("pledges")]);
  const o = officials.find((x) => x.official_id === params.get("id"));
  if (!o) { $("#gov-main").innerHTML = `<h1>Not found</h1><p><a href="index.html">Go back to everyone we track</a>.</p>`; return; }
  document.title = `${o.name}'s promises | Promise Tracker`;
  const cfg = OFFICE[o.office] || OFFICE.Governor;
  const senate = o.office === "Senator";
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
    <p class="crumbs"><a href="index.html">Everyone we track</a></p>
    <h1>${esc(o.name)}</h1>
    <p class="lead">${cfg.elect} ${esc(o.state_name)}. ${esc(COHORT[o.cohort] || "")}.${o.provisional === "Y" ? ` <strong>The race is not final:</strong> ${esc(o.notes)}.` : ""}</p>
    <dl class="facts">
      <div><dt>Promises tracked</dt><dd class="num">${s.n}</dd></div>
      <div><dt>Rated</dt><dd class="num">${s.rated}</dd></div>
      ${senate ? `<div><dt>Took formal action</dt><dd class="num">${s.effort_rated ? pct(s.acted_share) : "—"}${s.effort_rated && s.acted_ci95 ? `<small>95% range ${pct(s.acted_ci95[0])} to ${pct(s.acted_ci95[1])}</small>` : "<small>After the first review</small>"}</dd></div>` : ""}
      <div><dt>Kept or partially kept</dt><dd class="num">${s.rated ? pct(s.kept_or_partial_share) : "—"}${s.rated && s.kept_or_partial_ci95 ? `<small>95% range ${pct(s.kept_or_partial_ci95[0])} to ${pct(s.kept_or_partial_ci95[1])}</small>` : "<small>After the first review</small>"}</dd></div>
    </dl>
    ${legend()}
    ${strip(mine)}
    <h2>Effort and results</h2>
    <p>${senate ? "A senator can rarely make a law happen alone, so effort comes first: did they introduce, vote, and push for what they promised? What actually happened is shown alongside." : "Each promise gets two separate ratings: what happened, and how hard the governor pushed."} Reading them together separates a promise that was fought for and blocked from one that was never tried.</p>
    <div class="eo" role="table" aria-label="Promises by effort and outcome">
      <div class="h" role="columnheader"></div><div class="h" role="columnheader">Low effort</div><div class="h" role="columnheader">High effort</div><div class="h" role="columnheader">Effort under review</div>
      <div class="h" role="rowheader">Kept or partly</div>
        <div class="cell" role="cell">${cell("kept", "low")}<span>easy win</span></div><div class="cell" role="cell">${cell("kept", "high")}<span>delivered</span></div><div class="cell" role="cell">${cell("kept", "unrated")}</div>
      <div class="h" role="rowheader">Broken</div>
        <div class="cell flag" role="cell">${cell("not_kept", "low")}<span>never really tried</span></div><div class="cell" role="cell">${cell("not_kept", "high")}<span>fought and blocked</span></div><div class="cell" role="cell">${cell("not_kept", "unrated")}</div>
      <div class="h" role="rowheader">Still open</div>
        <div class="cell" role="cell">${cell("open", "low")}</div><div class="cell" role="cell">${cell("open", "high")}</div><div class="cell" role="cell">${cell("open", "unrated")}</div>
    </div>
    <p class="small muted">Low effort means no action or talk only. High effort means a formal step or more. ${cell("kept", "undermined") + cell("not_kept", "undermined") + cell("open", "undermined")} promises were undermined by the ${cfg.title}'s own actions.</p>
    <h2>${senate ? "Power in Congress" : "Power in the statehouse"}</h2>
    ${o.power_context.length ? `<div class="table-wrap"><table><thead><tr><th>Session</th><th>Trifecta</th><th>House majority</th><th>Senate majority</th><th>Veto override</th></tr></thead><tbody>${o.power_context.map((pc) => `<tr><td>${esc(pc.session)}</td><td>${esc(pc.trifecta)}</td><td>${esc(pc.house_majority)}</td><td>${esc(pc.senate_majority)}</td><td>${esc(pc.veto_override_threshold)}</td></tr>`).join("")}</tbody></table></div>`
      : `<div class="notice"><p>${senate ? "Control of the Senate, the House and the White House for the 2027 session will be added once results are certified. A senator in the majority can get votes scheduled; one in the minority mostly can't." : "Legislative control for the 2027 session will be added once results are certified. Whether a governor's party controls the legislature changes what they can deliver."}</p></div>`}
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
  document.title = `${p.pledge_id}: ${o.name} | Promise Tracker`;
  const senate = o.office === "Senator";
  const cfg = OFFICE[o.office] || OFFICE.Governor;
  const c = p.current;
  const rated = c.outcome !== "not_rated" && c.as_of;
  const latest = p.history[p.history.length - 1];
  const outcomeCard = `<div><p class="k">What happened</p><p class="v">${mark(c.outcome)}${OUTCOME[c.outcome]}</p><p class="d">${OUTCOME_HELP[c.outcome]}</p></div>`;
  const effortCard = `<div><p class="k">${senate ? "What the senator did" : "Governor's effort"}</p><p class="v">${c.effort != null ? esc(EFFORT[c.effort]) : "Under review"}</p><p class="d">${c.effort != null ? effortHelp(c.effort, o.office) : pendingWhy(latest?.effort_state)}</p></div>`;
  const verdict = rated ? `
    <div class="verdict">
      ${senate ? effortCard + outcomeCard : outcomeCard + effortCard}
      ${c.outcome !== "kept" ? `<div><p class="k">What stood in the way</p><p class="v">${c.blocker ? esc(BLOCKER[c.blocker]) : "Under review"}</p>${c.blocker ? "" : `<p class="d">${pendingWhy(latest.blocker_state)}</p>`}</div>` : ""}
    </div>
    <p class="small muted">Rated as of ${fmtDate(c.as_of)} by two independent reviewers${latest.adjudication_notes.length ? ", with a third settling a disagreement" : ""}.${c.in_review ? " A newer review is in progress." : ""}</p>
    ${latest.adjudication_notes.length ? `<p class="small"><strong>Why the tie-breaker decided this way:</strong> ${latest.adjudication_notes.map(esc).join(" ")}</p>` : ""}
    <h2>Evidence</h2>
    ${latest.evidence.length ? `<ol>${latest.evidence.map((e) => `<li><a href="${esc(safeUrl(e.url))}" rel="noopener">${esc(e.url.replace(/^https?:\/\//, "").slice(0, 90))}</a>${e.cited_by < 2 ? ` <span class="small muted">(cited by one reviewer)</span>` : ""}</li>`).join("")}</ol>` : "<p>No evidence links recorded.</p>"}`
    : `<div class="notice"><p><strong>Not yet rated.</strong> ${c.in_review ? "Two reviewers are working on the first rating." : `Ratings start after the ${cfg.title} takes office in January 2027. The first review covers the first 100 days.`}</p></div>`;
  main.innerHTML = `
    <p class="crumbs"><a href="index.html">Everyone we track</a> / <a href="official.html?id=${encodeURIComponent(o.official_id)}">${esc(o.name)}</a> / ${esc(p.pledge_id)}</p>
    <p class="quote quote-lg">${esc(p.pledge_text)}</p>
    <p class="muted">${esc(o.name)}, ${senate ? "Senate" : "governor"} campaign, ${esc(SOURCE[p.source_type] || p.source_type).toLowerCase()}. ${esc(AREA[p.policy_area] || p.policy_area)}.</p>
    ${p.review_flags.length ? `<ul class="flags" aria-label="Review notes">${p.review_flags.map((f) => `<li>${esc(FLAG[f] || f)}</li>`).join("")}</ul>` : ""}
    ${!p.active ? `<div class="notice"><p>This promise was ${p.merged_into ? `merged into <a href="promise.html?id=${esc(p.merged_into)}">${esc(p.merged_into)}</a> as a duplicate` : "removed from the tracker after review"}.</p></div>` : ""}
    ${verdict}
    ${p.history.length > 1 ? `<h2>How the rating changed</h2><ol class="timeline">${p.history.map((h) => `<li><strong>${fmtDate(h.period_end)}</strong>: ${OUTCOME[h.outcome]}${h.effort != null ? `, ${EFFORT[h.effort]?.toLowerCase()}` : ""}</li>`).join("")}</ol>` : ""}
    <h2>Where this promise comes from</h2>
    <dl class="kv">
      <dt>Source</dt><dd><a href="${esc(safeUrl(p.source_url))}" rel="noopener">${esc(p.source_title || p.source_url)}</a></dd>
      <dt>Saved copy</dt><dd>${p.archive_url ? `<a href="${esc(safeUrl(p.archive_url))}" rel="noopener">Wayback Machine, ${waybackDate(p.archive_timestamp)}</a>${/\.pdf($|\?)/i.test(p.archive_url) ? ` <span class="muted">(PDF; it can take a few seconds to appear)</span>` : ""}` : "Not archived yet"}</dd>
      <dt>Page fingerprint</dt><dd class="small"><code>${esc(p.sha256 || "—")}</code></dd>
      <dt>How it gets done</dt><dd>${esc(INSTRUMENT[p.instrument] || p.instrument)}</dd>
      <dt>Needs others to act</dt><dd>${p.requires_other_actor === "Y" ? `Yes. The ${cfg.title} can't do this alone` : `No. Within the ${cfg.title}'s own power`}</dd>
      <dt>Keeps things as they are</dt><dd>${p.status_quo === "Y" ? "Yes" : "No, it changes something"}</dd>
      ${p.prereg ? `<dt>Pre-registered</dt><dd>${{ frozen: `Yes. Locked in before ratings began (<a href="${PREREG_URL}" rel="noopener">what that means</a>)`, added: `No. Added after the <a href="${PREREG_URL}" rel="noopener">pre-registration</a>, under the same rules`, changed: `Yes, then corrected afterward (see below)` }[p.prereg]}</dd>` : ""}
      ${p.extractor_notes ? `<dt>Notes</dt><dd>${esc(p.extractor_notes)}</dd>` : ""}
    </dl>
    ${p.corrections.length ? `<h2>Corrections</h2><ul>${p.corrections.map((x) => `<li><strong>${fmtDate(x.date)}</strong> (${esc(CORRECTION_KIND[x.kind] || x.kind)}): ${esc(x.what_changed)}${x.issue_url ? ` <a href="${esc(safeUrl(x.issue_url))}" rel="noopener">Request</a>` : ""}</li>`).join("")}</ul>` : ""}
    <h2>Think we got this wrong?</h2>
    <p>Anyone can ask us to review a rating or a quote, including the ${cfg.title}'s office. Every request and our answer is public.</p>
    <p><a class="btn" href="${issueUrl(p.pledge_id)}" rel="noopener">Ask for a review or report an error</a></p>
    <p class="small muted">You'll need a free GitHub account. Every fix we make is listed on the <a href="corrections.html">corrections page</a>.</p>`;
}

async function compare() {
  const [officials, summary, pledges] = await Promise.all([load("officials"), load("summary"), load("pledges")]);
  const active = pledges.filter((p) => p.active);
  const officeOf = Object.fromEntries(officials.map((o) => [o.official_id, o]));
  $("#cmp").innerHTML = Object.entries(OFFICE).map(([office, cfg]) => {
    const offs = officials.filter((o) => o.office === office);
    if (!offs.length) return "";
    const senate = office === "Senator";
    const mine = active.filter((p) => officeOf[p.official_id].office === office);
    const rated = mine.some((p) => p.current.outcome !== "not_rated");
    const parties = [["D", "Democrats"], ["R", "Republicans"]].filter(([k]) => summary.cohorts[office]?.[k]);
    const share = (party, pred) => {
      const set = mine.filter((p) => officeOf[p.official_id].party === party);
      return set.length ? set.filter(pred).length / set.length : 0;
    };
    const areas = Object.keys(AREA).filter((a) => mine.some((p) => p.policy_area === a))
      .map((a) => [a, ...parties.map(([k]) => share(k, (p) => p.policy_area === a))])
      .sort((x, y) => y.slice(1).reduce((a, b) => a + b, 0) - x.slice(1).reduce((a, b) => a + b, 0));
    const metric = senate ? "acted" : "kept";
    return `<section aria-labelledby="c-${office}"><h2 id="c-${office}">${cfg.plural}</h2>
    ${rated ? `<h3>${senate ? "How often each senator took formal action" : "How much each governor delivered"}</h3>${dotChart(offs, metric)}
      <div class="table-wrap"><table><thead><tr><th>Party</th><th class="n">Promises</th><th class="n">${senate ? "Took formal action, pooled" : "Kept or partly, pooled"}</th><th class="n">Average of each person's rate</th></tr></thead><tbody>
      ${parties.map(([k, t]) => { const c = summary.cohorts[office][k]; const pool = c.pooled;
        const v = senate ? [pool.acted_share, pool.acted_ci95] : [pool.kept_or_partial_share, pool.kept_or_partial_ci95];
        return `<tr><td>${t}</td><td class="n">${pool.n}</td><td class="n">${pct(v[0])}${v[1] ? ` (${pct(v[1][0])} to ${pct(v[1][1])})` : ""}</td><td class="n">${pct(senate ? c.mean_of_officials_acted : c.mean_of_officials_kept_or_partial)}</td></tr>`; }).join("")}
      </tbody></table></div>
      <p class="small muted">Pooled rates weight people with longer platforms more. The average of each person's rate weights everyone equally. Ranges are 95% Wilson intervals.</p>`
    : `<div class="notice"><p><strong>Nothing to compare yet.</strong> Comparisons appear after the first review, about 100 days after the ${cfg.title}s take office. Until then, here is what each side promised.</p></div>`}
    <h3>What each side promised</h3>
    <div class="table-wrap"><table><thead><tr><th>Topic</th>${parties.map(([, t]) => `<th class="n">${t}</th>`).join("")}</tr></thead><tbody>
      ${areas.map(([a, ...v]) => `<tr><td>${esc(AREA[a])}</td>${v.map((x) => `<td class="n">${pct(x)}</td>`).join("")}</tr>`).join("")}
      <tr><td><strong>${senate ? "Can keep it alone (no other votes needed)" : "Needs the legislature or others to act"}</strong></td>${parties.map(([k]) => `<td class="n">${pct(share(k, (p) => senate ? p.requires_other_actor === "N" : p.requires_other_actor === "Y"))}</td>`).join("")}</tr>
    </tbody></table></div>
    <p class="small muted">${parties.map(([k, t]) => `${t}: ${summary.cohorts[office][k].pooled.n} promises`).join(". ")}. A count only includes statements specific enough to check, so it partly measures how specific a platform was.</p>
    </section>`;
  }).join("");
}

function dotChart(offs, metric) {
  const val = (s) => (metric === "acted" ? [s.acted_share, s.acted_ci95] : [s.kept_or_partial_share, s.kept_or_partial_ci95]);
  const rows = offs.filter((o) => val(o.summary)[0] != null && o.summary.rated)
    .sort((a, b) => a.party.localeCompare(b.party) || (val(b.summary)[0] - val(a.summary)[0]));
  const W = 640, L = 190, R = 20, rowH = 30, H = rows.length * rowH + 30;
  const x = (v) => L + v * (W - L - R);
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const label = metric === "acted" ? "took formal action on" : "kept or partially kept";
  return `<figure class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Share of each person's promises they ${label}, with 95% ranges">
    ${ticks.map((t) => `<line x1="${x(t)}" x2="${x(t)}" y1="0" y2="${H - 24}" class="grid"/><text x="${x(t)}" y="${H - 6}" text-anchor="middle">${t * 100}%</text>`).join("")}
    ${rows.map((o, i) => { const y = i * rowH + 16; const [v, ci0] = val(o.summary); const ci = ci0 || [v, v];
      return `<text class="lbl" x="0" y="${y + 4}">${esc(o.name)} (${o.party})</text>
        <line x1="${x(ci[0])}" x2="${x(ci[1])}" y1="${y}" y2="${y}" class="ci" stroke-width="2"/>
        <circle cx="${x(v)}" cy="${y}" r="5" class="dot${o.party === "D" ? " filled" : ""}" stroke-width="2"><title>${esc(o.name)}: ${pct(v)}</title></circle>`; }).join("")}
  </svg><figcaption class="small muted">Dot: ${metric === "acted" ? "share of promises they took formal action on" : "share of promises kept or partially kept"}. Line: 95% range. Filled dots are Democrats, open dots Republicans.</figcaption></figure>`;
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
  $("#prereg-status").textContent = meta.prereg_frozen_on
    ? `The pre-registration was frozen on ${fmtDate(meta.prereg_frozen_on)} (UTC).` : "The pre-registration has not been frozen yet.";
  $("#prereg-link").href = PREREG_URL;
  $("#review-link").href = issueUrl();
}

async function corrections() {
  const list = await load("corrections");
  $("#corr").innerHTML = list.length
    ? `<div class="table-wrap"><table><thead><tr><th>Date</th><th>Promise</th><th>Type</th><th>What changed</th></tr></thead><tbody>
      ${list.map((c) => `<tr><td>${fmtDate(c.date)}</td><td>${c.pledge_id ? `<a href="promise.html?id=${encodeURIComponent(c.pledge_id)}">${esc(c.pledge_id)}</a>` : "Whole site"}</td><td>${esc(CORRECTION_KIND[c.kind] || c.kind)}</td><td>${esc(c.what_changed)}${c.issue_url ? ` <a href="${esc(safeUrl(c.issue_url))}" rel="noopener">Request</a>` : ""}</td></tr>`).join("")}
      </tbody></table></div>`
    : `<div class="notice"><p>No corrections yet. When we fix a quote, a source or a rating, it will be listed here.</p></div>`;
  $("#review-link").href = issueUrl();
}

const pages = { home, promises, official, governor: official, promise, compare, methods, corrections };
const page = document.body.dataset.page;
(pages[page] || (async () => {}))().catch((e) => {
  const m = document.querySelector("main");
  m.insertAdjacentHTML("afterbegin", `<div class="notice" role="alert"><p>The data didn't load: ${esc(e.message)}. Reload the page, and if it keeps happening, run <code>python3 scripts/build.py</code>.</p></div>`);
});
