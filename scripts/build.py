#!/usr/bin/env python3
"""Validate the data, compute consensus ratings and reliability, and write the site's JSON.

Usage:  python3 scripts/build.py            (writes site/data/*.json and out/*.csv)
        python3 scripts/build.py --check    (validate only; non-zero exit on errors)

Inputs (data/):
  officials.csv, pledges.csv, power_context.csv, adjudications.csv, corrections.csv, ratings/<coder>.csv
  ../prereg/manifest.json (optional; once present, changed promises need a logged correction)
Outputs:
  site/data/{officials,pledges,summary,reliability,meta,corrections}.json   public site
  site/coder/pledges.json                                         blinded coder queue
  out/adjudication_queue.csv                                      disagreements to resolve
"""
import csv
import glob
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

from freeze import pledge_hash

ROOT = os.environ.get("PT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "out")

CODEBOOK_VERSION = "1.1"
OUTCOMES = ["kept", "partial", "in_progress", "not_rated", "broken"]
EFFORTS = ["-1", "0", "1", "2", "3", "4"]
BLOCKERS = ["none_attempted", "legislature_opposition", "legislature_own_party", "courts",
            "federal", "voters", "budget", "self_reversed", "too_early",
            # Congress only
            "other_chamber", "president", "filibuster"]
OFFICES = ["Governor", "Senator"]
ACTION_EFFORTS = ("2", "3", "4")  # a formal step or more
DECISIONS = ["keep", "drop", "merge"]
YN = ["Y", "N"]
TASKS = ["extraction", "status"]
FIELDS = {"extraction": ["decision", "testable", "verbatim_ok"],
          "status": ["outcome", "effort", "blocker"]}
RATING_COLUMNS = ["pledge_id", "coder", "rated_at", "codebook_version", "task", "period_end",
                  "decision", "merge_into", "testable", "verbatim_ok",
                  "outcome", "effort", "blocker", "evidence_urls", "note"]
URL_RE = re.compile(r"^https?://[^\s\"'<>]+$")
ALLOWED = {"outcome": OUTCOMES, "effort": EFFORTS, "blocker": BLOCKERS + [""],
           "testable": YN, "verbatim_ok": YN}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- statistics ----------

def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes out of n. Returns (low, high) or None."""
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def cohen_kappa(pairs, categories=None, weights=None):
    """Cohen's kappa for a list of (a, b) labels.
    weights='quadratic' treats `categories` as an ordered scale. Returns None if undefined."""
    pairs = [(a, b) for a, b in pairs if a != "" and b != ""]
    n = len(pairs)
    if n == 0 or len({x for p in pairs for x in p}) < 2:
        return None  # undefined: nothing to correct for chance with a single observed category
    cats = list(categories) if categories else sorted({x for p in pairs for x in p})
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    if k < 2:
        return None
    obs = [[0.0] * k for _ in range(k)]
    for a, b in pairs:
        obs[idx[a]][idx[b]] += 1
    row = [sum(obs[i]) for i in range(k)]
    col = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i, j):
        if weights == "quadratic":
            return 1 - ((i - j) ** 2) / ((k - 1) ** 2)
        return 1.0 if i == j else 0.0

    po = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w(i, j) * row[i] * col[j] for i in range(k) for j in range(k)) / (n * n)
    if pe == 1:
        return 1.0 if po == 1 else None
    return (po - pe) / (1 - pe)


# ---------- validation ----------

def validate(officials, pledges, ratings, adjudications, power):
    errors, warnings = [], []
    off_ids = {o["official_id"] for o in officials}
    pids = set()
    for p in pledges:
        if p["pledge_id"] in pids:
            errors.append(f"pledges: duplicate pledge_id {p['pledge_id']}")
        pids.add(p["pledge_id"])
        if p["official_id"] not in off_ids:
            errors.append(f"pledges: {p['pledge_id']} has unknown official_id {p['official_id']}")
        if not p["pledge_text"].strip():
            errors.append(f"pledges: {p['pledge_id']} has empty pledge_text")
        if not p.get("archive_url"):
            warnings.append(f"pledges: {p['pledge_id']} has no archive_url")
        for col in ("source_url", "archive_url"):
            if p.get(col) and not URL_RE.match(p[col]):
                errors.append(f"pledges: {p['pledge_id']} {col} must be an http(s) URL")
    for o in officials:
        if o["party"] not in ("D", "R", "I"):
            errors.append(f"officials: {o['official_id']} party must be D, R or I")
        if o["office"] not in OFFICES:
            errors.append(f"officials: {o['official_id']} office must be one of {OFFICES}")
    for i, r in enumerate(ratings, 2):
        where = f"{r['_file']} line {i if '_line' not in r else r['_line']}"
        if r["pledge_id"] not in pids:
            errors.append(f"{where}: unknown pledge_id {r['pledge_id']}")
        if r["task"] not in TASKS:
            errors.append(f"{where}: task must be one of {TASKS}")
            continue
        if not TS_RE.match(r["rated_at"] or ""):
            errors.append(f"{where}: rated_at must be an ISO date or timestamp")
        if not r["codebook_version"]:
            errors.append(f"{where}: codebook_version is required")
        if r["task"] == "extraction":
            if r["decision"] not in DECISIONS:
                errors.append(f"{where}: decision must be one of {DECISIONS}")
            if r["decision"] == "merge" and (r["merge_into"] not in pids or r["merge_into"] == r["pledge_id"]):
                errors.append(f"{where}: merge_into must be another existing pledge_id")
            for f in ("testable", "verbatim_ok"):
                if r[f] not in YN:
                    errors.append(f"{where}: {f} must be Y or N")
        else:
            if not DATE_RE.match(r["period_end"] or ""):
                errors.append(f"{where}: period_end (YYYY-MM-DD) is required for status ratings")
            if r["outcome"] not in OUTCOMES:
                errors.append(f"{where}: outcome must be one of {OUTCOMES}")
            if r["effort"] not in EFFORTS:
                errors.append(f"{where}: effort must be one of {EFFORTS}")
            if r["outcome"] == "kept":
                if r["blocker"]:
                    warnings.append(f"{where}: blocker is ignored when outcome is kept")
            elif r["blocker"] not in BLOCKERS:
                errors.append(f"{where}: blocker must be one of {BLOCKERS} when outcome is not kept")
            if r["outcome"] not in ("not_rated",) and not r["evidence_urls"].strip():
                warnings.append(f"{where}: {r['outcome']} rating has no evidence_urls")
            for u in filter(None, (x.strip() for x in r["evidence_urls"].split("|"))):
                if not URL_RE.match(u):
                    errors.append(f"{where}: evidence URL must start with http:// or https:// ({u[:60]})")
    for a in adjudications:
        if a["pledge_id"] not in pids:
            errors.append(f"adjudications: unknown pledge_id {a['pledge_id']}")
        if a["task"] not in TASKS or a["field"] not in FIELDS.get(a["task"], []):
            errors.append(f"adjudications: bad task/field {a['task']}/{a['field']} for {a['pledge_id']}")
        if not a["reason"].strip():
            errors.append(f"adjudications: {a['pledge_id']} {a['field']} needs a reason")
        v = a["final_value"]
        if a["field"] == "decision":
            ok = v in ("keep", "drop") or (v.startswith("merge:") and v[6:] in pids and v[6:] != a["pledge_id"])
        else:
            ok = v in ALLOWED.get(a["field"], [])
        if not ok:
            errors.append(f"adjudications: {a['pledge_id']} {a['field']} has invalid final_value '{v[:40]}'")
        if a["task"] == "status" and not DATE_RE.match(a.get("period_end") or ""):
            errors.append(f"adjudications: {a['pledge_id']} status adjudication needs period_end")
    for pc in power:
        if pc["official_id"] not in off_ids:
            errors.append(f"power_context: unknown official_id {pc['official_id']}")
    return errors, warnings


CORRECTION_KINDS = ("quote", "source", "rating", "metadata", "other")


def validate_corrections(corrections, pledge_ids):
    errors = []
    for i, c in enumerate(corrections, start=2):
        where = f"corrections.csv line {i}"
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", c.get("date", "")):
            errors.append(f"{where}: date must be YYYY-MM-DD")
        if c.get("pledge_id") and c["pledge_id"] not in pledge_ids:
            errors.append(f"{where}: unknown pledge_id {c['pledge_id']}")
        if c.get("kind") not in CORRECTION_KINDS:
            errors.append(f"{where}: kind must be one of {CORRECTION_KINDS}")
        if not c.get("what_changed", "").strip():
            errors.append(f"{where}: what_changed is required")
        if c.get("issue_url") and not re.match(r"https?://", c["issue_url"]):
            errors.append(f"{where}: issue_url must be an http(s) URL")
    return errors


def check_prereg(pledges, manifest, corrections):
    """Label each promise frozen/added/changed against the pre-registration manifest.

    A promise whose official, wording or source changed after the freeze must have a
    quote or source correction logged for it, or the build fails."""
    if not manifest:
        return {p["pledge_id"]: None for p in pledges}, []
    fixed = {c["pledge_id"] for c in corrections if c.get("kind") in ("quote", "source")}
    status, errors = {}, []
    for p in pledges:
        pid = p["pledge_id"]
        frozen = manifest["pledges"].get(pid)
        if frozen is None:
            status[pid] = "added"
        elif frozen == pledge_hash(p):
            status[pid] = "frozen"
        else:
            status[pid] = "changed"
            if pid not in fixed:
                errors.append(f"prereg: {pid} changed since the pre-registration freeze; "
                              "log a quote or source entry in data/corrections.csv")
    return status, errors


def load_ratings():
    rows = []
    for path in sorted(glob.glob(os.path.join(DATA, "ratings", "*.csv"))):
        name = os.path.basename(path)
        recs = read_csv(path)
        if recs and list(recs[0].keys()) != RATING_COLUMNS:
            raise SystemExit(f"{name}: header must be exactly: {','.join(RATING_COLUMNS)}")
        for i, r in enumerate(recs, 2):
            r = {k: (v or "").strip() for k, v in r.items()}
            r["_file"], r["_line"] = name, i
            if r["coder"] != os.path.splitext(name)[0]:
                raise SystemExit(f"{name} line {i}: coder '{r['coder']}' must match file name")
            rows.append(r)
    return rows


# ---------- consensus ----------

def field_value(r, field):
    if field == "decision" and r["decision"] == "merge":
        return f"merge:{r['merge_into']}"
    if field == "blocker" and r["outcome"] == "kept":
        return ""
    return r[field]


def consensus(ratings, adjudications):
    """Returns {(pledge_id, task, period): {field: {...}}} and the pairs used for kappa."""
    latest = {}
    for r in ratings:
        period = r["period_end"] if r["task"] == "status" else ""
        key = (r["pledge_id"], r["task"], period, r["coder"])
        if key not in latest or r["rated_at"] >= latest[key]["rated_at"]:
            latest[key] = r
    grouped = defaultdict(dict)
    for (pid, task, period, coder), r in latest.items():
        grouped[(pid, task, period)][coder] = r
    adj = {}
    for a in adjudications:
        adj[(a["pledge_id"], a["task"], a.get("period_end", "") or "", a["field"])] = a

    results, pairs, adj_errors = {}, defaultdict(list), []
    for key, by_coder in grouped.items():
        pid, task, period = key
        coders = sorted(by_coder)
        res = {"coders": coders, "fields": {}}
        for field in FIELDS[task]:
            vals = {c: field_value(by_coder[c], field) for c in coders}
            a = adj.get((pid, task, period, field))
            if len(coders) >= 2:
                pair = (vals[coders[0]], vals[coders[1]])
                if not (field == "blocker" and "" in pair):  # blocker only compared when both coded one
                    pairs[(task, field, coders[0], coders[1])].append(pair)
            if len(coders) < 2:
                state, value = "pending", None
            elif len(set(vals.values())) == 1:
                state, value = "agreed", next(iter(vals.values()))
            elif a:
                state, value = "adjudicated", a["final_value"]
            else:
                state, value = "disputed", None
            if a and state != "adjudicated":
                adj_errors.append(f"adjudications: {pid} {field} ({period or task}) is {state}, not disputed; "
                                  "tie-breakers may only resolve disagreements between two coders")
            res["fields"][field] = {"state": state, "value": value,
                                    "reason": a["reason"] if a else ""}
        # evidence and notes: union from coders, only shown once outcome is final
        if task == "status":
            cited = {}
            for c in coders:
                for u in by_coder[c]["evidence_urls"].split("|"):
                    u = u.strip()
                    if u:
                        cited.setdefault(u, set()).add(c)
            res["evidence"] = [{"url": u, "cited_by": len(cs)} for u, cs in cited.items()]
        results[key] = res
    return results, pairs, adj_errors


def reliability(pairs, results):
    out = []
    for (task, field, ca, cb), ps in sorted(pairs.items()):
        if field == "effort":
            ordered = [x for x in EFFORTS]
            kappa = cohen_kappa(ps, ordered, "quadratic")
            method = "quadratic-weighted Cohen's kappa"
        else:
            cats = sorted({x for p in ps for x in p})
            kappa = cohen_kappa(ps, cats)
            method = "Cohen's kappa"
        agree = sum(1 for a, b in ps if a == b)
        out.append({"task": task, "field": field, "coders": [ca, cb], "n": len(ps),
                    "percent_agreement": round(agree / len(ps), 4) if ps else None,
                    "kappa": round(kappa, 4) if kappa is not None else None,
                    "method": method})
    states = Counter(f["state"] for r in results.values() for f in r["fields"].values())
    return {"fields": out, "field_states": dict(states), "target_kappa": 0.70}


# ---------- assemble ----------

def build(check_only=False):
    officials = read_csv(os.path.join(DATA, "officials.csv"))
    pledges = read_csv(os.path.join(DATA, "pledges.csv"))
    power = read_csv(os.path.join(DATA, "power_context.csv"))
    adjudications = read_csv(os.path.join(DATA, "adjudications.csv"))
    corr_path = os.path.join(DATA, "corrections.csv")
    corrections = read_csv(corr_path) if os.path.exists(corr_path) else []
    man_path = os.path.join(ROOT, "prereg", "manifest.json")
    manifest = json.load(open(man_path, encoding="utf-8")) if os.path.exists(man_path) else None
    ratings = load_ratings()

    errors, warnings = validate(officials, pledges, ratings, adjudications, power)
    errors += validate_corrections(corrections, {p["pledge_id"] for p in pledges})
    prereg, prereg_errors = check_prereg(pledges, manifest, corrections)
    errors += prereg_errors
    for w in warnings:
        print("warning:", w)
    if errors:
        for e in errors:
            print("ERROR:", e)
        raise SystemExit(f"{len(errors)} error(s); nothing written")
    results, pairs, adj_errors = consensus(ratings, adjudications)
    # merges must point at a pledge that stays public, with no loops
    final_dec = {pid: r["fields"]["decision"]["value"] for (pid, t, _), r in results.items() if t == "extraction"}
    for pid, d in final_dec.items():
        if d and d.startswith("merge:"):
            tgt = final_dec.get(d[6:])
            if tgt == "drop" or (tgt or "").startswith("merge:"):
                adj_errors.append(f"extraction: {pid} is merged into {d[6:]}, which is itself dropped or merged")
    if adj_errors:
        for e in adj_errors:
            print("ERROR:", e)
        raise SystemExit(f"{len(adj_errors)} error(s); nothing written")
    if check_only:
        print(f"OK: {len(pledges)} pledges, {len(ratings)} rating events, {len(warnings)} warnings")
        return
    rel = reliability(pairs, results)

    by_pid = defaultdict(list)
    for (pid, task, period), res in results.items():
        by_pid[pid].append((task, period, res))

    pub_pledges = []
    for p in pledges:
        rec = {k: p[k] for k in ("pledge_id", "official_id", "state", "policy_area", "pledge_text",
                                 "source_type", "source_url", "source_title", "date_seen",
                                 "archive_url", "archive_timestamp", "sha256", "compound_group",
                                 "instrument", "requires_other_actor", "status_quo", "salience",
                                 "extractor_notes")}
        rec["review_flags"] = [f for f in p["review_flags"].split(";") if f]
        ext = next((res for t, _, res in by_pid[p["pledge_id"]] if t == "extraction"), None)
        rec["extraction"] = ({f: ext["fields"][f]["state"] for f in FIELDS["extraction"]}
                             if ext else None)
        decision = ext["fields"]["decision"]["value"] if ext else None
        rec["active"] = not (decision == "drop" or (decision or "").startswith("merge:"))
        rec["merged_into"] = decision.split(":", 1)[1] if (decision or "").startswith("merge:") else None

        history = []
        for task, period, res in sorted((x for x in by_pid[p["pledge_id"]] if x[0] == "status"),
                                        key=lambda x: x[1]):
            f = res["fields"]
            entry = {"period_end": period,
                     "outcome": f["outcome"]["value"], "outcome_state": f["outcome"]["state"],
                     "effort": f["effort"]["value"], "effort_state": f["effort"]["state"],
                     "blocker": f["blocker"]["value"], "blocker_state": f["blocker"]["state"],
                     "adjudication_notes": [f[k]["reason"] for k in f if f[k]["reason"]]}
            entry["evidence"] = res["evidence"] if f["outcome"]["value"] else []
            history.append(entry)
        final = [h for h in history if h["outcome"]]
        cur = final[-1] if final else None
        rec["current"] = {
            "outcome": cur["outcome"] if cur else "not_rated",
            "effort": cur["effort"] if cur and cur["effort"] else None,
            "blocker": cur["blocker"] if cur and cur["blocker"] else None,
            "as_of": cur["period_end"] if cur else None,
            "in_review": bool(history and history[-1]["outcome"] is None),
        }
        rec["history"] = final
        rec["prereg"] = prereg[p["pledge_id"]]
        rec["corrections"] = [{k: c[k] for k in ("date", "kind", "what_changed", "issue_url")}
                              for c in corrections if c["pledge_id"] == p["pledge_id"]]
        pub_pledges.append(rec)

    # summaries
    def summarize(items):
        n = len(items)
        oc = Counter(x["current"]["outcome"] for x in items)
        kept_like = oc["kept"] + oc["partial"]
        ci = wilson(kept_like, n)
        grid = Counter()
        for x in items:
            e = x["current"]["effort"]
            band = "unrated" if e is None else ("undermined" if e == "-1" else ("low" if e in ("0", "1") else "high"))
            o = x["current"]["outcome"]
            ob = "kept" if o in ("kept", "partial") else ("not_kept" if o == "broken" else "open")
            grid[f"{ob}|{band}"] += 1
        efforts = [x["current"]["effort"] for x in items if x["current"]["effort"] is not None]
        acted = sum(1 for e in efforts if e in ACTION_EFFORTS)
        aci = wilson(acted, len(efforts))
        return {"n": n, "outcomes": {o: oc.get(o, 0) for o in OUTCOMES},
                "effort_rated": len(efforts),
                "acted_share": round(acted / len(efforts), 4) if efforts else None,
                "acted_ci95": [round(v, 4) for v in aci] if aci else None,
                "kept_or_partial_share": round(kept_like / n, 4) if n else None,
                "kept_or_partial_ci95": [round(v, 4) for v in ci] if ci else None,
                "effort_outcome_grid": dict(grid),
                "rated": n - oc.get("not_rated", 0)}

    active = [x for x in pub_pledges if x["active"]]
    pub_officials, by_off = [], defaultdict(list)
    for x in active:
        by_off[x["official_id"]].append(x)
    power_by = defaultdict(list)
    for pc in power:
        power_by[pc["official_id"]].append(pc)
    for o in officials:
        s = summarize(by_off[o["official_id"]])
        areas = Counter(x["policy_area"] for x in by_off[o["official_id"]])
        pub_officials.append({**o, "summary": s, "policy_areas": dict(areas.most_common()),
                              "power_context": power_by[o["official_id"]]})

    cohorts = {}
    for office in OFFICES:
        cohorts[office] = {}
        for party in sorted({o["party"] for o in officials if o["office"] == office}):
            offs = [o for o in pub_officials if o["party"] == party and o["office"] == office]
            ids = {o["official_id"] for o in offs}
            pooled = summarize([x for x in active if x["official_id"] in ids])
            shares = [o["summary"]["kept_or_partial_share"] for o in offs if o["summary"]["rated"]]
            acted = [o["summary"]["acted_share"] for o in offs if o["summary"]["acted_share"] is not None]
            cohorts[office][party] = {
                "officials": sorted(ids), "pooled": pooled,
                "mean_of_officials_kept_or_partial": round(sum(shares) / len(shares), 4) if shares else None,
                "mean_of_officials_acted": round(sum(acted) / len(acted), 4) if acted else None}

    meta = {"built": date.today().isoformat(), "codebook_version": CODEBOOK_VERSION,
            "pledges_total": len(pub_pledges), "pledges_active": len(active),
            "rating_events": len(ratings), "officials": len(officials),
            "prereg_frozen_on": manifest["frozen_on"] if manifest else None,
            "latest_period": max((h["period_end"] for x in pub_pledges for h in x["history"]), default=None)}

    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "coder"), exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    def dump(name, obj):
        with open(name, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))

    dump(os.path.join(SITE, "data", "pledges.json"), pub_pledges)
    dump(os.path.join(SITE, "data", "officials.json"), pub_officials)
    dump(os.path.join(SITE, "data", "summary.json"), {"cohorts": cohorts})
    dump(os.path.join(SITE, "data", "reliability.json"), rel)
    dump(os.path.join(SITE, "data", "meta.json"), meta)
    dump(os.path.join(SITE, "data", "corrections.json"),
         sorted(corrections, key=lambda c: c["date"], reverse=True))

    # blinded coder queue: no official name, party, notes, or anyone's ratings
    office_of = {o["official_id"]: o["office"] for o in officials}
    coder_q = [{"office": office_of[p["official_id"]]} | {k: p[k] for k in ("pledge_id", "state", "policy_area", "pledge_text", "source_type",
                                  "source_url", "archive_url", "instrument", "requires_other_actor",
                                  "compound_group")} | {"review_flags": [f for f in p["review_flags"].split(";") if f]}
               for p in pledges]
    dump(os.path.join(SITE, "coder", "pledges.json"),
         {"codebook_version": CODEBOOK_VERSION, "pledges": coder_q})

    with open(os.path.join(OUT, "adjudication_queue.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pledge_id", "task", "period_end", "field", "coder_values"])
        latest_vals = defaultdict(dict)
        for r in ratings:
            period = r["period_end"] if r["task"] == "status" else ""
            k = (r["pledge_id"], r["task"], period)
            prev = latest_vals[k].get(r["coder"])
            if prev is None or r["rated_at"] >= prev["rated_at"]:
                latest_vals[k][r["coder"]] = r
        n_disp = 0
        for (pid, task, period), res in sorted(results.items()):
            for field, fv in res["fields"].items():
                if fv["state"] == "disputed":
                    vals = "; ".join(f"{c}={field_value(latest_vals[(pid, task, period)][c], field)}"
                                     for c in res["coders"])
                    w.writerow([pid, task, period, field, vals])
                    n_disp += 1
    print(f"Built: {len(pub_pledges)} pledges ({len(active)} active), {len(ratings)} rating events, "
          f"{n_disp} disputes queued, {len(warnings)} warnings")


if __name__ == "__main__":
    build(check_only="--check" in sys.argv)
