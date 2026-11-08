# Pre-registration

This document, the codebook and the list of officials and promises were frozen before any official took office and before any status rating was made. The freeze date and a SHA-256 fingerprint of each frozen file are in [`prereg/manifest.json`](prereg/manifest.json). The same files are archived in a dated GitHub release (and a Zenodo DOI, if enabled), so anyone can check that nothing was quietly changed after results started coming in.

## What is frozen

- **Who is tracked** (`data/officials.csv`). Governors: every governor who flipped a seat in 2026, plus every Republican who won an open seat. Senators: every senator elected in 2026 to a seat they did not already hold. Selection did not depend on anything they did in office.
- **Which promises count** (`data/pledges.csv`). Every promise was collected from campaign sources dated before Election Day and saved to the Wayback Machine. Each promise's official, wording and source are fingerprinted one by one in the manifest.
- **How promises are rated** (`codebook/CODEBOOK.md`, version 1.1).

## What will be reported

These are descriptive measures. With roughly a dozen officials per office, the tracker does not run significance tests or claim one party is "better". It reports rates with 95% Wilson intervals and lets readers see the overlap.

1. **Governors, headline:** the share of promises kept or partly kept.
2. **Senators, headline:** the share of promises where the senator took formal action (effort 2 or higher). Delivery rates are shown second.
3. **Party comparison** within each office, Democrats vs Republicans, computed two ways: all promises pooled, and the average of each official's own rate. Governors and senators are never pooled together.
4. **Secondary:** effort and blocker breakdowns, rates by policy area, and rates restricted to promises whose deadline has passed. Power context (trifecta or divided government) is shown next to every comparison.

Ratings are made at fixed review dates: day 100, day 365, the end of each legislative session, and end of term. Each review uses only evidence dated on or before the review date.

## What can change after the freeze, and how

Nothing is changed silently. Every change below is public and dated.

- **Quote or source fixes.** If a quote was transcribed wrong or a source link dies, the fix is logged in `data/corrections.csv`. The build refuses to publish a changed promise unless a correction explains it.
- **Extraction review.** Before ratings start, two reviewers check every promise and may drop or merge duplicates using the codebook's written rules. Those decisions are published like any rating.
- **Late-called races.** Winners of races not called at the freeze (Alaska and Mississippi Senate) are added under the same selection rule if they are new to the seat. Their promises are shown as "added after pre-registration". The Alaska governor's race is included provisionally; if the final count changes the winner, the swap is logged as an amendment.
- **Codebook changes.** Any change gets a new version number and a change-log entry. Every rating records the codebook version it used.
- **Anything else** is listed under Amendments below, with the date and reason.

## Amendments

- **2026-11-08 (UTC).** Added the Zenodo DOI for the frozen release: https://doi.org/10.5281/zenodo.24047633. No other change. Because this file was edited after the freeze, its current fingerprint no longer matches `prereg/manifest.json`; the frozen version is the one in that release.
- **2026-11-08 (UTC).** Reviewers may come from a pool larger than two. Each promise is still rated independently by exactly two reviewers, now listed in `data/assignments.csv`. Where the codebook (section 1.2) says each coder reviews "every pledge", read it as every pledge assigned to that coder. Agreement is reported for each pair of reviewers. A tie-breaker may not have rated the promise they decide. The build enforces all of this. The outcome definitions, selection rule and reporting measures are unchanged.
