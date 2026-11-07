#!/usr/bin/env python3
"""Fail if a change removes any rating that already exists on the base branch.

Ratings are an append-only log: a reviewer's new file must contain every row of their old
file (a re-rating adds a newer row; it never deletes the old one).

Usage: python3 scripts/check_append_only.py origin/main
"""
import csv
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = ("pledge_id", "coder", "rated_at", "task", "period_end")


def rows_at(ref, path):
    try:
        text = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return set()  # file is new on this branch
    return {tuple(r[k] for k in KEY) for r in csv.DictReader(io.StringIO(text))}


def main(base):
    names = subprocess.run(["git", "ls-tree", "--name-only", f"{base}:data/ratings"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split()
    missing = 0
    for name in names:
        if not name.endswith(".csv"):
            continue
        path = f"data/ratings/{name}"
        old = rows_at(base, path)
        local = os.path.join(ROOT, path)
        new = set()
        if os.path.exists(local):
            with open(local, newline="", encoding="utf-8") as f:
                new = {tuple(r[k] for k in KEY) for r in csv.DictReader(f)}
        gone = old - new
        if gone:
            missing += len(gone)
            print(f"ERROR: {path} drops {len(gone)} rating(s) that exist on {base}, e.g. {sorted(gone)[0]}")
            print("  The reviewer probably downloaded from a browser without loading their old file first.")
    if missing:
        sys.exit(1)
    print("OK: no existing ratings removed")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "origin/main")
