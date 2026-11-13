#!/usr/bin/env python3
"""
Check every promise against its archived source, and list the rows a person should look at.

It changes nothing in data/. It writes out/pledge_checks.csv, one row per problem found:

  quote_missing        the quote is not in the archived copy word for word
  quote_case_only      the quote is there, but only if you ignore upper and lower case
  archive_bot_check    the archived copy is a bot-check page, not the source
  archive_unreadable   the archived copy could not be fetched, or is a PDF (check those by hand)
  source_gone          the live source now returns 404 or 410
  source_blocked       the live source refused the script (403, 429, a bot check); check it in a browser
  source_unreachable   the live source did not answer
  ellipsis             the quote has an ellipsis; check that no condition, amount, date or limit was cut
  over_40_words        the quote is long; check that it is one promise
  possible_duplicate   the same official has a near-identical promise outside its compound group

Run:
  python3 scripts/check_pledges.py              all checks (needs network; about 216 sources)
  python3 scripts/check_pledges.py --offline    only the checks that need no network
  add --no-live to skip re-checking the live source pages

Downloaded archive copies are cached in out/check_cache/, so a second run is quick.
Uses only the Python standard library.
"""
import argparse
import csv
import difflib
import gzip
import hashlib
import html
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict

from archive_sources import bot_check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLEDGES = os.path.join(ROOT, "data", "pledges.csv")
OUT = os.path.join(ROOT, "out", "pledge_checks.csv")
CACHE = os.path.join(ROOT, "out", "check_cache")
UA = "pledge-ledger-checker/1.0 (research)"
DUPLICATE_RATIO = 0.9

# Typography that differs between the source and our CSV without changing the words.
SAME_CHAR = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
                           "“": '"', "”": '"', "„": '"', "″": '"',
                           "–": "-", "—": "-", "‑": "-", "‒": "-",
                           " ": " ", " ": " ", " ": " ", "​": "", "­": ""})


def norm(s):
    """Text with typography made uniform and whitespace collapsed. Words and case are kept."""
    s = html.unescape(s).translate(SAME_CHAR).replace("…", "...")
    return re.sub(r"\s+", " ", s).strip()


def page_text(body):
    """Readable text of an HTML page, normalized with norm()."""
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    raw = body.decode("utf-8", "replace")
    raw = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", raw)
    return norm(re.sub(r"<[^>]+>", " ", raw))


def quote_status(quote, text):
    """'ok', 'case_only' or 'missing'. Punctuation at either end of the quote is ignored."""
    q = norm(quote).strip(" \"'.,;:!?")
    if not q or q in text:
        return "ok"
    return "case_only" if q.lower() in text.lower() else "missing"


def text_checks(p):
    """Checks on the quote alone. Returns a list of (check, detail)."""
    out = []
    t = p["pledge_text"]
    if "..." in t or "…" in t:
        out.append(("ellipsis", "check that no condition, amount, date or limit was cut"))
    if len(t.split()) > 40:
        out.append(("over_40_words", f"{len(t.split())} words"))
    return out


def duplicates(pledges):
    """Pairs of near-identical promises from the same official, outside a shared compound group."""
    by_off = defaultdict(list)
    for p in pledges:
        by_off[p["official_id"]].append((p, norm(p["pledge_text"]).lower()))
    out = []
    for rows in by_off.values():
        for i, (a, ta) in enumerate(rows):
            for b, tb in rows[i + 1:]:
                if a["compound_group"] and a["compound_group"] == b["compound_group"]:
                    continue
                m = difflib.SequenceMatcher(None, ta, tb)
                if m.real_quick_ratio() >= DUPLICATE_RATIO and m.quick_ratio() >= DUPLICATE_RATIO \
                        and m.ratio() >= DUPLICATE_RATIO:
                    out.append((a, b, round(m.ratio(), 2)))
    return out


def raw_url(archive_url):
    """The Wayback link for the page exactly as captured, without the Wayback toolbar."""
    return re.sub(r"(/web/\d{14})/", r"\1id_/", archive_url, count=1)


def fetch(url, tries=3):
    """(status, body). Status is the HTTP code, or None if there was no answer."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and attempt < tries - 1:
                time.sleep(30 * (attempt + 1))
                continue
            return e.code, e.read() if e.fp else b""
        except Exception:  # noqa: BLE001
            if attempt < tries - 1:
                time.sleep(10)
                continue
            return None, b""
    return None, b""


def archived_copy(archive_url, pause):
    """(body, problem). Cached in out/check_cache/."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, hashlib.sha1(archive_url.encode()).hexdigest())
    if os.path.exists(path):
        return open(path, "rb").read(), None
    status, body = fetch(raw_url(archive_url))
    time.sleep(pause)
    if status != 200 or not body:
        return None, f"archive fetch failed (HTTP {status})"
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    with open(path, "wb") as f:
        f.write(body)
    return body, None


def live_check(url, pause):
    """(check, detail) for a live source that is down or blocked, else None."""
    status, body = fetch(url, tries=2)
    time.sleep(pause)
    if status is None:
        return "source_unreachable", "no answer"
    if status in (404, 410):
        return "source_gone", f"HTTP {status}"
    if status in (401, 403, 429) or (status == 200 and bot_check(body)):
        return "source_blocked", f"HTTP {status}" + (f", {bot_check(body)}" if status == 200 else "")
    if status >= 400:
        return "source_unreachable", f"HTTP {status}"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="only checks that need no network")
    ap.add_argument("--no-live", action="store_true", help="skip re-checking the live source pages")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    args = ap.parse_args()

    pledges = list(csv.DictReader(open(PLEDGES, encoding="utf-8")))
    found = []  # (pledge, check, detail)

    for p in pledges:
        found += [(p, c, d) for c, d in text_checks(p)]
    for a, b, ratio in duplicates(pledges):
        found.append((a, "possible_duplicate", f"{ratio:.0%} like {b['pledge_id']}"))
        found.append((b, "possible_duplicate", f"{ratio:.0%} like {a['pledge_id']}"))

    if not args.offline:
        by_archive = defaultdict(list)
        for p in pledges:
            by_archive[p["archive_url"].strip()].append(p)
        for i, (aurl, rows) in enumerate(sorted(by_archive.items()), 1):
            print(f"[{i}/{len(by_archive)}] {aurl or '(no archive link)'}", file=sys.stderr)
            if not aurl:
                found += [(p, "archive_unreadable", "no archive link") for p in rows]
                continue
            body, problem = archived_copy(aurl, args.pause)
            if problem:
                found += [(p, "archive_unreadable", problem) for p in rows]
            elif body[:4] == b"%PDF":
                found += [(p, "archive_unreadable", "PDF: check the quote by hand") for p in rows]
            elif bot_check(body):
                found += [(p, "archive_bot_check", bot_check(body)) for p in rows]
            else:
                text = page_text(body)
                for p in rows:
                    st = quote_status(p["pledge_text"], text)
                    if st != "ok":
                        found.append((p, f"quote_{st}", "not in the archived copy" if st == "missing"
                                      else "differs only in upper or lower case"))
        if not args.no_live:
            by_source = defaultdict(list)
            for p in pledges:
                by_source[p["source_url"].strip()].append(p)
            for i, (url, rows) in enumerate(sorted(by_source.items()), 1):
                print(f"[live {i}/{len(by_source)}] {url}", file=sys.stderr)
                hit = live_check(url, args.pause)
                if hit:
                    found += [(p, *hit) for p in rows]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    found.sort(key=lambda x: (x[0]["pledge_id"], x[1]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pledge_id", "official_id", "check", "detail", "source_url", "archive_url"])
        for p, check, detail in found:
            w.writerow([p["pledge_id"], p["official_id"], check, detail, p["source_url"], p["archive_url"]])

    counts = defaultdict(int)
    for _, check, _ in found:
        counts[check] += 1
    print(f"\n{len(pledges)} promises checked. Wrote {len(found)} flags to {os.path.relpath(OUT, ROOT)}")
    for check in sorted(counts):
        print(f"  {check:20} {counts[check]}")


if __name__ == "__main__":
    main()
