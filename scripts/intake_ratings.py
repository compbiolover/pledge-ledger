#!/usr/bin/env python3
"""Turn a "Send my ratings" issue into data/ratings/<id>.csv.

Reads the issue body from the ISSUE_BODY environment variable, downloads the attached CSV and
writes it in place. It prints the reviewer ID. build.py and check_append_only.py do the full
checks afterwards (header, coder matches file name, draws, nothing deleted).

Usage: ISSUE_BODY=... python3 scripts/intake_ratings.py
"""
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build import CODER_RE  # noqa: E402

# Only files GitHub itself stored for this issue; never fetch an arbitrary link from issue text.
ATTACH_RE = re.compile(r"https://github\.com/user-attachments/files/\d+/[A-Za-z0-9._-]+\.csv")
MAX_BYTES = 20 * 1024 * 1024


def parse(body):
    """Return (coder, attachment_url) from an issue-form body, or raise SystemExit."""
    m = re.search(r"^### Reviewer ID\s*\n+(.*?)\s*$", body or "", re.M)
    coder = (m.group(1) if m else "").strip().lower()
    if not CODER_RE.match(coder):
        raise SystemExit(f"The reviewer ID '{coder}' isn't valid. Use the ID from the rating tool: "
                         "lowercase letters, numbers or underscores.")
    urls = ATTACH_RE.findall(body)
    if len(urls) != 1:
        raise SystemExit(f"Expected one attached .csv file, found {len(urls)}. Edit the issue and drag "
                         "in the file from Download my ratings.")
    return coder, urls[0]


def main():
    coder, url = parse(os.environ.get("ISSUE_BODY", ""))
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise SystemExit("The attached file is too large to be a ratings file.")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SystemExit("The attached file isn't a plain-text CSV. Attach the file the tool downloaded.")
    with open(os.path.join(ROOT, "data", "ratings", f"{coder}.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(coder)


if __name__ == "__main__":
    main()
