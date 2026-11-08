#!/usr/bin/env python3
"""Freeze the pre-registration: fingerprint the codebook, officials and every promise.

Run once, before any status rating, then publish a GitHub release of the commit.
Refuses to overwrite an existing manifest; later changes go in PREREGISTRATION.md
(Amendments) and data/corrections.csv.
"""
import csv
import hashlib
import json
import os
import sys
from datetime import date

ROOT = os.environ.get("PT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "prereg", "manifest.json")
FILES = ["PREREGISTRATION.md", "codebook/CODEBOOK.md", "data/officials.csv", "data/pledges.csv"]


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def pledge_hash(p):
    """Fingerprint of the parts of a promise that must not change without a logged correction."""
    s = "\x1f".join([p["official_id"], p["pledge_text"].strip(), p["source_url"].strip()])
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main():
    if os.path.exists(MANIFEST) and "--force" not in sys.argv:
        sys.exit("prereg/manifest.json already exists. Record changes as amendments instead.")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build import CODEBOOK_VERSION
    with open(os.path.join(ROOT, "data", "pledges.csv"), newline="", encoding="utf-8") as f:
        pledges = list(csv.DictReader(f))
    with open(os.path.join(ROOT, "data", "officials.csv"), newline="", encoding="utf-8") as f:
        officials = [o["official_id"] for o in csv.DictReader(f)]
    manifest = {
        "frozen_on": date.today().isoformat(),
        "codebook_version": CODEBOOK_VERSION,
        "files": {p: file_hash(os.path.join(ROOT, p)) for p in FILES},
        "officials": officials,
        "pledges": {p["pledge_id"]: pledge_hash(p) for p in pledges},
    }
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=False)
        f.write("\n")
    print(f"Frozen {len(pledges)} promises from {len(officials)} officials on {manifest['frozen_on']}")


if __name__ == "__main__":
    main()
