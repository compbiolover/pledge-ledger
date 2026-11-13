# Maintaining Pledge Ledger

Notes for the people who run the project: building the site, running reviews and adding data. If you just want to read or use the data, start with the [README](../README.md).

## How it fits together

```
data/pledges.csv ─┐
data/officials.csv├─► scripts/build.py ─► site/data/*.json  (public site)
data/ratings/*.csv│        │          └─► site/coder/pledges.json (blinded queue)
data/adjudications┘        └─► out/adjudication_queue.csv (disagreements)
```

`build.py` validates everything, works out what both reviewers agreed on, applies tie-breaker decisions, computes agreement (Cohen's kappa) and writes the JSON the site reads. Nothing from a single reviewer is ever published.

## Share links

`build.py` writes a static page for every person (`/people/<id>/`) and every promise (`/promises/<id>/`), plus `sitemap.xml`. Each carries its own title, description and preview image tags, so links shared in iMessage, WhatsApp, Signal, Slack and social apps show a proper card. Those crawlers don't run JavaScript, which is why the tags are written at build time. The preview image is `site/assets/og.png`. Pages use root-relative links (`/assets/...`), so the site must be served from the domain root.

## Deploying

The site is deployed by GitHub Actions (`.github/workflows/deploy.yml`). In the repository settings, **Pages, Build and deployment, Source** must be set to **GitHub Actions**. Every push to `main` runs the tests, rebuilds the data and redeploys the site.

If the repository is renamed, change `REPO` at the top of `site/assets/app.js`, `sendUrl` in `site/coder/coder.js` and the codebook link in `site/coder/index.html`.

## The review workflow

**Before inauguration: check the promise list.** Each reviewer opens `/coder/`, picks "Check the promise list", and marks every promise keep, drop or merge, testable or not, and whether the quote matches the saved copy. Promises flagged `check_wording` deserve the closest look.

**After inauguration: rate status at each review date** (day 100, one year, after each session, end of term).

For both tasks:

1. Each reviewer works alone and clicks **Download my ratings**.
2. Send it with **Open the send form** in the tool (the "Send my ratings" issue form). The reviewer drags the file in; no git needed. The `Ratings intake` Action saves it as `data/ratings/<reviewer-id>.csv`, runs the append-only check, the tests and the build, and opens a pull request. If a check fails, it comments on the issue with the reason, and editing the issue with a fixed file runs it again. A maintainer reviews and merges the pull request. Reviewers who use git can still commit the file through their own pull request.

   One-time setup: in **Settings, Actions, General**, turn on **Allow GitHub Actions to create and approve pull requests**, and create a `ratings` label. Pull requests opened by the Action don't trigger the deploy workflow's checks, which is why the Action runs them itself.
3. The build lists disagreements in `out/adjudication_queue.csv` (also printed in the Actions log).
4. A third person resolves each one by adding a row to `data/adjudications.csv` with a written reason. The tie-breaker must not be one of the two people who rated that promise; the build fails if they are.

### More than two reviewers: the public draw

Each promise is still rated by exactly two people. With a larger pool, a random draw decides who rates what. No one picks the pairs by hand, including the maintainer.

1. **Announce the draw first.** Open a public issue that lists the reviewer IDs and the review round (extraction, or the review date). Name a future round of the [drand](https://drand.love) public randomness beacon as the seed. Pick a round at least a day after the issue is posted, so no one knows its value yet.
2. **Wait for that round,** then copy its `randomness` value.
3. **Add one row to `data/draws.csv`** through a pull request that links the issue:
   `task,period_end,reviewers,seed,seed_source`, for example
   `status,2027-04-30,ann;bob;cat,<randomness>,drand round <n> (issue #<number>)`.
4. The build works out each promise's pair from the seed and prints how many promises each reviewer got. Anyone can rerun it and get the same pairs.

Rules the build enforces:

- Add the draw before anyone starts that round. Once a round has a draw, only each promise's two drawn reviewers may rate it, and ratings can't be deleted.
- A round with no draw is open to anyone, which is fine with exactly two reviewers.
- Three people rating the same promise fails the build, because agreement is measured between two.
- Each draw is for one round. A later round can use a different pool.
- A promise's pair depends only on the seed and its ID. Adding a promise later doesn't change anyone else's assignments.

Each pair gets a random mix of both parties' promises. Reviewers can see who they're paired with, since the draw is public. Remind them to work alone anyway.

To continue on another computer, use **Load my ratings file** in the tool.

## Adding data

- **Legislative control:** fill `data/power_context.csv` once 2027 control is certified. The site shows it on each governor's page.
- **Inauguration dates:** fill `term_start` in `data/officials.csv`.
- **Alaska:** the race is provisional until ranked-choice tabulation (Nov 18) and certification (Nov 25). If the result changes, update `data/officials.csv` and drop or replace the AK pledges.
- **Archiving sources:** `python3 scripts/archive_sources.py data/pledges.csv --in-place` archives every promise that has no `archive_url` yet and fills in the link, timestamp and fingerprint (keeps a `.bak`). Run it whenever you add promises.
- **Senators** use office `Senator`, IDs like `S-TX`, and are rated effort-first (codebook Part 2b). The Alaska Senate race was not called when the list was built; add it with the same rule if the winner is new to the seat. Mississippi (Scott Colom, `S-MS`) was called on 2026-11-11 and added. His promises are extracted but still need `archive_sources.py`.

## Pre-registration and corrections

- **Freeze (done once, before any status rating):** `python3 scripts/freeze.py` writes `prereg/manifest.json` with fingerprints of the codebook, officials, `PREREGISTRATION.md` and every promise. Commit it and publish a GitHub release of that commit. If Zenodo is linked to the repo, the release also gets a DOI.
- **After the freeze,** the build fails if a promise's official, wording or source changes without a matching `quote` or `source` row in `data/corrections.csv`. New promises are allowed and shown as "added after pre-registration". Other changes go under Amendments in `PREREGISTRATION.md`.
- **Corrections log:** add a row to `data/corrections.csv` (`date,pledge_id,kind,what_changed,issue_url`; kind is quote, source, rating, metadata or other) for every fix. The site lists them on `corrections.html` and on the promise's page.
- **Review requests** use the issue form in `.github/ISSUE_TEMPLATE/review.yml`, which labels them `appeal`.

## Open tasks

- Recruit at least two reviewers. Nothing gets rated without two.
