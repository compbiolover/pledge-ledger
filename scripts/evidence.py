#!/usr/bin/env python3
"""
Build the shared evidence lists that both reviewers of a promise get before a review date.
See the 2026-11-13 amendment in PREREGISTRATION.md for the rules this follows.

Every promise gets the same treatment, whatever the official's party:
  1. Search terms come from the promise's own words by a fixed rule (search_terms below):
     the 3 least common words of the promise across all promises, after dropping common
     words. Nobody picks them by hand.
  2. An item is kept if its date falls between the official's term start (or --since)
     and the review date, and its title has at least 2 of the terms (or the only term).
  3. Sources:
       congress     bills each senator sponsored or cosponsored (Congress.gov API)
       votes        each senator's Senate roll-call votes (senate.gov XML)
       legiscan     bills in each governor's state legislature (LegiScan API)
       gdelt        news articles naming the official and a term (GDELT; last 3 months only)

The list holds no rating, summary or judgment. Reviewers still search on their own.

Output, one folder per review date:
  evidence/<review-date>/terms.csv      the search terms for every promise
  evidence/<review-date>/<source>.csv   the items found, one row per item and promise

Keys:
  Congress.gov  sent in the X-Api-Key header from CONGRESS_API_KEY (in a cloud session the
                proxy adds it; set CONGRESS_API_KEY=proxy-injected there)
  LegiScan      LEGISCAN_API_KEY, e.g. bws run -- 'python3 scripts/evidence.py ...'
  GDELT, senate.gov need no key.

Run:
  python3 scripts/evidence.py --review-date 2027-04-13
  add --sources congress,votes to run some sources only, --only S-WY,TN for some officials,
  and --since YYYY-MM-DD for officials whose term_start is blank (default 2027-01-01).

Uses only the Python standard library.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "pledge-ledger-evidence/1.0 (research; https://pledgeledger.org/)"
SOURCES = ["congress", "votes", "legiscan", "gdelt"]
FIELDS = ["pledge_id", "official_id", "source", "date", "kind", "title", "url", "detail", "matched_terms"]
MAX_TERMS = 3

# Words that say nothing about the subject of a promise. Applied the same way to every promise.
STOP = set("""
a an the and or but nor of to in on for with by at from as is are was were be been being that this these those
it its our we us my me i you your their they them he she his her him hers who whom whose which what when where
why how there here than then into onto over under up down out off about above below before after until while
during through again further once all any both each every few more most other some such no not only own same so
too very can could will would shall should may might must do does did done just also still even ever never
make makes made making sure ensure ensures fight fights fighting fought work works working worked push pushing
support supports supporting supported help helps helping keep keeps keeping continue continues bring brings
take takes taking give gives giving get gets getting got real new plan plans want wants need needs know like
lead leads leading stand stands standing vote votes voting voted pass passes passing passed act acts law laws
bill bills legislation policy policies program programs effort efforts first day days year years time times
people person families family folks everyone everybody anyone community communities american americans america
country nation national government federal state states local public congress senate senator senators governor
office washington d.c. u.s. us usa end ends ending going go goes use uses using way ways put puts set sets
much many back top bottom high higher low lower raise raises raising cut cuts cutting direct directly provide
provides providing doesn't don't won't can't isn't aren't i'll we'll he'll she'll they'll i'm we're it's that's
let's one two three four five six ten second last next full fully deserve deserves deserved wait tie ties join
joins cancel restore restores restoring strengthen strengthens expand expands expanding create creates creating
establish establishes establishing build builds increase increases increasing reduce reduces reducing protect
protects protecting require requires requiring allow allows allowing ban bans banning stop stops stopping oppose
opposes opposing fund funds funding invest invests investing return returns bring back across without within
including include includes well good better best great strong stronger fair fairly right able already always
today now against because since though although whether either per via among whole entire half part parts
proud proudly propose proposes proposal promise promises pledge pledges commit committed priority priorities
agenda candidate between around along toward towards instead rather yet once enough little less lot lots
eliminate eliminates eliminating regardless said say says call calls called ask asks asked look looks hard everything something nothing anything thing things
""".split())


def stem(word):
    """Crude stem so that tariff/tariffs and trade/trading match. Same for every promise."""
    w = word.lower().replace("’", "'")
    w = re.sub(r"'s$", "", w)
    for suffix in ("ing", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            w = w[: -len(suffix)]
            break
    return w[:-1] if w.endswith("e") and len(w) > 3 else w


def words(text):
    return re.findall(r"[A-Za-z][A-Za-z'’-]*", text)


def content_stems(text, names=()):
    """Stems of the words that carry meaning, in text order, without repeats.

    names: stems of people and places to drop, including words built on them (Mississippians)."""
    out = []
    for w in words(text):
        lw = w.lower().replace("’", "'").removesuffix("'s")
        if (len(lw) < 3 and not (len(w) == 2 and w.isupper())) or lw in STOP:  # keep acronyms like VA, AI
            continue
        s = stem(lw)
        if any(s.startswith(n) for n in names):
            continue
        if s not in out:
            out.append(s)
    return out


def search_terms(pledges, officials):
    """{pledge_id: [stems]}: each promise's MAX_TERMS least common words across all promises.

    Ties go to the word that comes first in the promise. Names of officials and states are dropped,
    so a term is about the subject, not the person or place."""
    names = set()
    for o in officials.values():
        names.update(stem(w) for w in words(o["name"]) + words(o["state_name"]) if len(w) >= 4)
    per = {p["pledge_id"]: content_stems(p["pledge_text"], names) for p in pledges}
    df = Counter(s for stems in per.values() for s in stems)
    return {pid: sorted(stems, key=lambda s: (df[s], stems.index(s)))[:MAX_TERMS] for pid, stems in per.items()}


def matched(text, terms):
    """Terms found in the text. An item counts if it has 2 terms, or the only term there is."""
    have = {stem(w) for w in words(text)}
    hits = [t for t in terms if t in have]
    return hits if terms and len(hits) >= min(2, len(terms)) else []


def get(url, headers=None, tries=3, pause=0.0):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            time.sleep(pause)
            return body
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(20 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries - 1:
                time.sleep(10)
                continue
            raise


def in_window(date, start, end):
    return bool(date) and start <= date <= end


def congress_of(year):
    return (year - 1789) // 2 + 1


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


BILL_PATH = {"S": "senate-bill", "HR": "house-bill", "SRES": "senate-resolution", "HRES": "house-resolution",
             "SJRES": "senate-joint-resolution", "HJRES": "house-joint-resolution",
             "SCONRES": "senate-concurrent-resolution", "HCONRES": "house-concurrent-resolution"}


def bill_url(congress, kind, number):
    path = BILL_PATH.get(kind.upper())
    return f"https://www.congress.gov/bill/{ordinal(int(congress))}-congress/{path}/{number}" if path else ""


# ---------- Congress.gov: sponsored and cosponsored bills ----------

def congress_api(path, params, key):
    q = urllib.parse.urlencode({**params, "format": "json"})
    return json.loads(get(f"https://api.congress.gov/v3/{path}?{q}", {"X-Api-Key": key}, pause=0.5))


def member_id(o, congress, key):
    """Bioguide ID of the member from this official's state whose last name matches."""
    last = o["name"].split()[-1].lower()
    data = congress_api(f"member/congress/{congress}/{o['state']}", {"limit": 250, "currentMember": "false"}, key)
    ids = [m["bioguideId"] for m in data.get("members", []) if m["name"].split(",")[0].strip().lower() == last]
    return ids[0] if len(ids) == 1 else None


def congress_items(o, rows, terms, start, end, key):
    congress = congress_of(int(end[:4]))
    bid = member_id(o, congress, key)
    if not bid:
        print(f"  {o['official_id']}: no single member match in the {ordinal(congress)} Congress", file=sys.stderr)
        return []
    out = []
    for kind, field in (("sponsored", "sponsoredLegislation"), ("cosponsored", "cosponsoredLegislation")):
        offset = 0
        while True:
            data = congress_api(f"member/{bid}/{kind}-legislation", {"limit": 250, "offset": offset}, key)
            items = data.get(field, [])
            for b in items:
                if not b.get("title") or not in_window(b.get("introducedDate", ""), start, end):
                    continue
                text = b["title"] + " " + ((b.get("policyArea") or {}).get("name") or "")
                act = b.get("latestAction") or {}
                for p in rows:
                    hits = matched(text, terms[p["pledge_id"]])
                    if hits:
                        out.append({"pledge_id": p["pledge_id"], "official_id": o["official_id"], "source": "congress",
                                    "date": b["introducedDate"], "kind": kind, "title": b["title"],
                                    "url": bill_url(b["congress"], b["type"], b["number"]),
                                    "detail": f"{b['type']} {b['number']}; latest action {act.get('actionDate', '')}: {act.get('text', '')}",
                                    "matched_terms": " ".join(hits)})
            offset += len(items)
            if not items or offset >= data.get("pagination", {}).get("count", 0):
                break
    return out


# ---------- senate.gov: roll-call votes ----------

MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def vote_menu(congress, session):
    url = f"https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_{congress}_{session}.xml"
    root = ET.fromstring(get(url, pause=1))
    year = int(root.findtext("congress_year"))
    for v in root.iter("vote"):
        day, mon = v.findtext("vote_date").strip().split("-")
        yield {"number": v.findtext("vote_number").strip(), "date": f"{year}-{MONTHS[mon]:02d}-{int(day):02d}",
               "title": " ".join((v.findtext("title") or "").split()), "issue": (v.findtext("issue") or "").strip(),
               "question": " ".join((v.findtext("question") or "").split()), "result": (v.findtext("result") or "").strip()}


def vote_casts(congress, session, number):
    """{(STATE, last name): vote_cast} for one roll call."""
    url = f"https://www.senate.gov/legislative/LIS/roll_call_votes/vote{congress}{session}/vote_{congress}_{session}_{number}.xml"
    root = ET.fromstring(get(url, pause=1))
    return {(m.findtext("state"), m.findtext("last_name").lower()): m.findtext("vote_cast") for m in root.iter("member")}


def vote_items(senators, rows_by_off, terms, windows, end):
    out = []
    first = min(w[0] for w in windows.values())
    for year in range(int(first[:4]), int(end[:4]) + 1):
        congress, session = congress_of(year), 1 if year % 2 else 2
        try:
            menu = list(vote_menu(congress, session))
        except urllib.error.HTTPError:
            continue  # no votes yet that year
        for v in menu:
            text = f"{v['title']} {v['question']}"
            hits_by = {}
            for o in senators:
                start = windows[o["official_id"]][0]
                if not in_window(v["date"], start, end):
                    continue
                for p in rows_by_off[o["official_id"]]:
                    hits = matched(text, terms[p["pledge_id"]])
                    if hits:
                        hits_by[(o["official_id"], p["pledge_id"])] = hits
            if not hits_by:
                continue
            casts = vote_casts(congress, session, v["number"])
            off = {o["official_id"]: o for o in senators}
            for (oid, pid), hits in hits_by.items():
                o = off[oid]
                cast = casts.get((o["state"], o["name"].split()[-1].lower()), "not listed")
                out.append({"pledge_id": pid, "official_id": oid, "source": "votes", "date": v["date"], "kind": "roll_call",
                            "title": v["title"],
                            "url": f"https://www.senate.gov/legislative/LIS/roll_call_votes/vote{congress}{session}/vote_{congress}_{session}_{v['number']}.htm",
                            "detail": f"Vote {int(v['number'])}: {v['question']}; {v['result']}; voted {cast}",
                            "matched_terms": " ".join(hits)})
    return out


# ---------- LegiScan: state bills ----------

LEGISCAN_STATUS = {"1": "Introduced", "2": "Engrossed", "3": "Enrolled", "4": "Passed", "5": "Vetoed", "6": "Failed"}


def legiscan(op, key, **params):
    q = urllib.parse.urlencode({"key": key, "op": op, **params})
    data = json.loads(get(f"https://api.legiscan.com/?{q}", pause=1))
    if data.get("status") != "OK":
        raise RuntimeError(f"LegiScan {op}: {data.get('alert', {}).get('message', data.get('status'))}")
    return data


def legiscan_items(o, rows, terms, start, end, key):
    out = []
    sessions = legiscan("getSessionList", key, state=o["state"])["sessions"]
    for s in sessions:
        if int(s["year_end"]) < int(start[:4]) or int(s["year_start"]) > int(end[:4]):
            continue
        master = legiscan("getMasterList", key, id=s["session_id"])["masterlist"]
        for k, b in master.items():
            if k == "session" or not in_window(b.get("last_action_date", ""), start, end):
                continue
            text = f"{b.get('title', '')} {b.get('description', '')}"
            for p in rows:
                hits = matched(text, terms[p["pledge_id"]])
                if hits:
                    out.append({"pledge_id": p["pledge_id"], "official_id": o["official_id"], "source": "legiscan",
                                "date": b["last_action_date"], "kind": "state_bill", "title": b.get("title", ""),
                                "url": b.get("url", ""),
                                "detail": f"{b.get('number', '')} ({s.get('session_name', '')}); "
                                          f"{LEGISCAN_STATUS.get(str(b.get('status')), 'status ' + str(b.get('status')))}; "
                                          f"last action {b['last_action_date']}: {b.get('last_action', '')}",
                                "matched_terms": " ".join(hits)})
    return out


# ---------- GDELT: news ----------

def gdelt_items(o, rows, terms, start, end, words_by_pid):
    """GDELT's article search only covers the last 3 months, so the window is cut to that."""
    out = []
    end_d = dt.date.fromisoformat(end)
    start_d = max(dt.date.fromisoformat(start), end_d - dt.timedelta(days=89))
    for p in rows:
        ws = words_by_pid[p["pledge_id"]]
        if not ws:
            continue
        query = f'"{o["name"]}" ' + ("(" + " OR ".join(ws) + ")" if len(ws) > 1 else ws[0])
        q = urllib.parse.urlencode({"query": query, "mode": "ArtList", "format": "json", "maxrecords": 50,
                                    "sourcelang": "english", "sort": "DateDesc",
                                    "startdatetime": start_d.strftime("%Y%m%d000000"),
                                    "enddatetime": end_d.strftime("%Y%m%d235959")})
        body = get(f"https://api.gdeltproject.org/api/v2/doc/doc?{q}", pause=5)
        try:
            arts = json.loads(body or b"{}").get("articles", [])
        except json.JSONDecodeError:
            arts = []  # GDELT answers a query it can't run with a plain-text message
        for a in arts:
            date = f"{a['seendate'][:4]}-{a['seendate'][4:6]}-{a['seendate'][6:8]}"
            out.append({"pledge_id": p["pledge_id"], "official_id": o["official_id"], "source": "gdelt", "date": date,
                        "kind": "news", "title": a.get("title", ""), "url": a.get("url", ""),
                        "detail": a.get("domain", ""), "matched_terms": " ".join(ws)})
    return out


def gdelt_words(pledges, terms):
    """For news search, the original word behind each stem (first use in the promise)."""
    out = {}
    for p in pledges:
        first = {}
        for w in words(p["pledge_text"]):
            first.setdefault(stem(w.lower()), w.lower().replace("’", "'").removesuffix("'s"))
        out[p["pledge_id"]] = [first[t] for t in terms[p["pledge_id"]] if t in first]
    return out


def write(path, rows, fields=FIELDS):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: tuple(r[k] for k in fields[:5])) if fields == FIELDS else rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--review-date", required=True, help="YYYY-MM-DD; nothing dated after it is kept")
    ap.add_argument("--since", default="2027-01-01", help="window start for officials with no term_start")
    ap.add_argument("--sources", default=",".join(SOURCES))
    ap.add_argument("--only", default="", help="comma-separated official IDs")
    ap.add_argument("--out", default=os.path.join(ROOT, "evidence"))
    args = ap.parse_args()

    end = dt.date.fromisoformat(args.review_date).isoformat()
    sources = [s for s in args.sources.split(",") if s]
    bad = set(sources) - set(SOURCES)
    if bad:
        sys.exit(f"unknown sources: {', '.join(sorted(bad))}")

    officials = {o["official_id"]: o for o in csv.DictReader(open(os.path.join(DATA, "officials.csv"), encoding="utf-8"))}
    pledges = list(csv.DictReader(open(os.path.join(DATA, "pledges.csv"), encoding="utf-8")))
    terms = search_terms(pledges, officials)  # always over all promises, so --only never changes anyone's terms
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    chosen = [o for oid, o in officials.items() if not only or oid in only]
    rows_by_off = {o["official_id"]: [p for p in pledges if p["official_id"] == o["official_id"]] for o in chosen}
    windows = {o["official_id"]: (o["term_start"] or args.since, end) for o in chosen}
    folder = os.path.join(args.out, end)

    write(os.path.join(folder, "terms.csv"),
          [{"pledge_id": p["pledge_id"], "official_id": p["official_id"], "terms": " ".join(terms[p["pledge_id"]])}
           for p in pledges], ["pledge_id", "official_id", "terms"])

    senators = [o for o in chosen if o["office"] == "Senator"]
    governors = [o for o in chosen if o["office"] == "Governor"]
    for source in sources:
        found = []
        if source == "congress":
            key = os.environ.get("CONGRESS_API_KEY") or sys.exit("Set CONGRESS_API_KEY (see the top of this file).")
            for o in senators:
                print(f"congress: {o['official_id']}", file=sys.stderr)
                found += congress_items(o, rows_by_off[o["official_id"]], terms, *windows[o["official_id"]], key)
        elif source == "votes" and senators:
            print("votes: Senate roll calls", file=sys.stderr)
            found = vote_items(senators, rows_by_off, terms, windows, end)
        elif source == "legiscan":
            key = os.environ.get("LEGISCAN_API_KEY") or sys.exit("Set LEGISCAN_API_KEY (see the top of this file).")
            for o in governors:
                print(f"legiscan: {o['official_id']}", file=sys.stderr)
                found += legiscan_items(o, rows_by_off[o["official_id"]], terms, *windows[o["official_id"]], key)
        elif source == "gdelt":
            ws = gdelt_words(pledges, terms)
            for o in chosen:
                print(f"gdelt: {o['official_id']}", file=sys.stderr)
                found += gdelt_items(o, rows_by_off[o["official_id"]], terms, *windows[o["official_id"]], ws)
        write(os.path.join(folder, f"{source}.csv"), found)
        print(f"{source}: {len(found)} items -> {os.path.relpath(os.path.join(folder, source + '.csv'), ROOT)}")


if __name__ == "__main__":
    main()
