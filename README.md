# Promise Tracker

Tracks every specific campaign promise made by the 12 governors and 17 U.S. senators who won flipped or open seats in November 2026. Each promise gets three separate ratings: what happened, how hard the governor pushed, and what stood in the way.

- **Public site:** `site/` (static, no build tools; deployed to GitHub Pages)
- **Rating tool:** `site/coder/` (two reviewers rate independently, without seeing names, parties, or each other's ratings)
- **Rules:** `codebook/CODEBOOK.md`
- **Data:** `data/` (plain CSV; every rating is a row, nothing is overwritten)

## How it fits together

```
data/pledges.csv ─┐
data/officials.csv├─► scripts/build.py ─► site/data/*.json  (public site)
data/ratings/*.csv│        │          └─► site/coder/pledges.json (blinded queue)
data/adjudications┘        └─► out/adjudication_queue.csv (disagreements)
```

`build.py` validates everything, works out what both reviewers agreed on, applies tie-breaker decisions, computes agreement (Cohen's kappa) and writes the JSON the site reads. Nothing from a single reviewer is ever published.

## Run it locally

```
python3 -m unittest discover -s tests     # tests
python3 scripts/build.py                  # validate + build
cd site && python3 -m http.server 8000    # open http://localhost:8000
```

Python 3.9+ with no extra packages.

## Publish on GitHub Pages (one time)

```
cd ~/promise-tracker/tracker
git init -b main
git add .
git commit -m "Promise tracker: data, codebook, site, rating tool"
gh repo create compbiolover/promise-tracker --public --source . --push
```

Then on GitHub: **Settings, Pages, Build and deployment, Source: GitHub Actions**. Every push to `main` now runs the tests, rebuilds the data and redeploys the site.

If you use a different repository name, change `REPO` at the top of `site/assets/app.js` and the codebook link in `site/coder/index.html`.

## The review workflow

**Now, before inauguration: check the promise list.** Each reviewer opens `/coder/`, picks "Check the promise list", and marks every promise keep, drop or merge, testable or not, and whether the quote matches the saved copy. Promises flagged `check_wording` deserve the closest look.

**After inauguration: rate status at each review date** (day 100, one year, after each session, end of term).

For both tasks:
1. Each reviewer works alone and clicks **Download my ratings**.
2. Commit the file as `data/ratings/<reviewer-id>.csv`. Use a pull request so the build checks it.
3. The build lists disagreements in `out/adjudication_queue.csv` (also printed in the Actions log).
4. A third person resolves each one by adding a row to `data/adjudications.csv` with a written reason.

To continue on another computer, use **Load my ratings file** in the tool.

## Adding data

- **Legislative control:** fill `data/power_context.csv` once 2027 control is certified. The site shows it on each governor's page.
- **Inauguration dates:** fill `term_start` in `data/officials.csv`.
- **Alaska:** the race is provisional until ranked-choice tabulation (Nov 18) and certification (Nov 25). If the result changes, update `data/officials.csv` and drop or replace the AK pledges.
- **Archiving sources:** `python3 scripts/archive_sources.py data/pledges.csv --in-place` archives every promise that has no `archive_url` yet and fills in the link, timestamp and fingerprint (keeps a `.bak`). Run it whenever you add promises.
- **Senators** use office `Senator`, IDs like `S-TX`, and are rated effort-first (codebook Part 2b). Alaska and Mississippi Senate races were not called when the list was built; add them with the same rule if the winner is new to the seat.

## Before going public

- Recruit the second reviewer. Nothing gets rated without one.
