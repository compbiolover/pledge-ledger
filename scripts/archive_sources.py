#!/usr/bin/env python3
"""
Archive every source URL in the pledge dataset to the Wayback Machine,
and keep your own hashed copy of each page as evidence.

What it does, for each unique source_url in the CSV:
  1. Downloads the page itself, saves it to snapshots/, and records its SHA-256.
  2. Asks the Wayback Machine (Save Page Now 2 API) to capture it, with a screenshot.
  3. Waits for the capture to finish and records the permanent archive link.
Results go into a new CSV with four added columns:
  archive_url, archive_timestamp, sha256, local_snapshot

It is resumable: progress is kept in archive_progress.json, so if it stops
(or you hit a rate limit), just run it again and it skips finished URLs.

Setup (one time):
  1. Log in at archive.org, then open https://archive.org/account/s3.php
     and copy your "access key" and "secret key".
  2. In a terminal:
       export IA_ACCESS_KEY="your-access-key"
       export IA_SECRET_KEY="your-secret-key"

Run:
  python3 scripts/archive_sources.py data/pledges.csv --in-place   # fill missing archive links in the repo data
  python3 scripts/archive_sources.py some.csv                      # write some_archived.csv next to it
  add --dry-run to just list what would be archived

With --in-place, only rows whose archive_url is empty are archived, and the
file is rewritten with archive_url, archive_timestamp and sha256 filled in
(a .bak copy is kept).

Only uses the Python standard library (Python 3.8+). Expect roughly
30-60 seconds per URL; ~113 URLs takes about an hour or two.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SAVE_URL = "https://web.archive.org/save"
STATUS_URL = "https://web.archive.org/save/status/{}"
UA = "pledge-tracker-archiver/1.0 (research; contact via archive.org account)"
PROGRESS = "archive_progress.json"
SNAP_DIR = "snapshots"


def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return json.load(f)
    return {}


def save_progress(p):
    tmp = PROGRESS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(p, f, indent=1)
    os.replace(tmp, PROGRESS)


def request(url, data=None, headers=None, timeout=60):
    h = {"User-Agent": UA}
    h.update(headers or {})
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def local_copy(url):
    """Download the page ourselves and hash it. Returns (sha256, path) or (None, error)."""
    os.makedirs(SNAP_DIR, exist_ok=True)
    try:
        _, body = request(url, timeout=60)
    except Exception as e:  # noqa: BLE001
        return None, f"download failed: {e}"
    digest = hashlib.sha256(body).hexdigest()
    ext = ".pdf" if body[:4] == b"%PDF" else ".html"
    name = re.sub(r"[^A-Za-z0-9]+", "_", url)[:120] + "_" + digest[:10] + ext
    path = os.path.join(SNAP_DIR, name)
    with open(path, "wb") as f:
        f.write(body)
    return digest, path


def wayback_capture(url, auth):
    """Submit to Save Page Now and poll until done. Returns (archive_url, timestamp) or raises."""
    headers = {"Accept": "application/json", "Authorization": auth}
    data = {"url": url, "capture_screenshot": "1", "skip_first_archive": "1"}
    for attempt in range(6):
        try:
            _, body = request(SAVE_URL, data=data, headers=headers, timeout=90)
            job = json.loads(body)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 520, 523):
                wait = 60 * (attempt + 1)
                print(f"    rate limited / busy (HTTP {e.code}); waiting {wait}s")
                time.sleep(wait)
                continue
            raise
    else:
        raise RuntimeError("gave up after repeated rate limits")

    if "job_id" not in job:
        raise RuntimeError(f"no job id: {job.get('message') or job}")

    job_id = job["job_id"]
    for _ in range(40):  # up to ~10 minutes
        time.sleep(15)
        _, body = request(STATUS_URL.format(job_id), headers=headers, timeout=60)
        st = json.loads(body)
        if st.get("status") == "success":
            ts = st["timestamp"]
            orig = st.get("original_url", url)
            return f"https://web.archive.org/web/{ts}/{orig}", ts
        if st.get("status") == "error":
            raise RuntimeError(st.get("message") or st.get("status_ext") or "capture error")
    raise RuntimeError("timed out waiting for capture")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--in-place", action="store_true", help="fill empty archive columns in the input file")
    ap.add_argument("--pause", type=float, default=8.0, help="seconds between URLs")
    args = ap.parse_args()

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    pending = [r for r in rows if not args.in_place or not r.get("archive_url", "").strip()]
    urls = sorted({r["source_url"].strip() for r in pending if r["source_url"].strip()})
    print(f"{len(rows)} pledges, {len(urls)} unique source URLs")

    if args.dry_run:
        for u in urls:
            print(" ", u)
        return

    key, secret = os.environ.get("IA_ACCESS_KEY"), os.environ.get("IA_SECRET_KEY")
    if not key or not secret:
        sys.exit("Set IA_ACCESS_KEY and IA_SECRET_KEY first (see the top of this file).")
    auth = f"LOW {key}:{secret}"

    prog = load_progress()
    for i, u in enumerate(urls, 1):
        rec = prog.get(u, {})
        if rec.get("archive_url"):
            continue
        print(f"[{i}/{len(urls)}] {u}")
        if not rec.get("sha256"):
            digest, path = local_copy(u)
            rec["sha256"], rec["local_snapshot"] = (digest or ""), path
            print(f"    local copy: {'ok ' + digest[:12] if digest else path}")
        try:
            aurl, ts = wayback_capture(u, auth)
            rec["archive_url"], rec["archive_timestamp"] = aurl, ts
            rec.pop("error", None)
            print(f"    archived: {aurl}")
        except Exception as e:  # noqa: BLE001
            rec["error"] = str(e)
            print(f"    FAILED: {e}  (will retry next run)")
        prog[u] = rec
        save_progress(prog)
        time.sleep(args.pause)

    if args.in_place:
        import shutil
        shutil.copyfile(args.csv_path, args.csv_path + ".bak")
        fields = list(rows[0].keys())
        filled = 0
        for r in rows:
            rec = prog.get(r["source_url"].strip(), {})
            if not r.get("archive_url", "").strip() and rec.get("archive_url"):
                r["archive_url"], r["archive_timestamp"], r["sha256"] = rec["archive_url"], rec["archive_timestamp"], rec.get("sha256", "")
                filled += 1
        with open(args.csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"\nFilled archive links for {filled} rows in {args.csv_path} (backup: {args.csv_path}.bak)")
        return

    out = re.sub(r"\.csv$", "", args.csv_path) + "_archived.csv"
    fields = list(rows[0].keys()) + ["archive_url", "archive_timestamp", "sha256", "local_snapshot"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            rec = prog.get(r["source_url"].strip(), {})
            w.writerow({**r, **{k: rec.get(k, "") for k in fields[-4:]}})
    done = sum(1 for u in urls if prog.get(u, {}).get("archive_url"))
    print(f"\nArchived {done}/{len(urls)} URLs. Wrote {out}")
    if done < len(urls):
        print("Some failed; run the same command again to retry them.")


if __name__ == "__main__":
    main()
