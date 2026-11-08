# Instructions for AI coding agents

These rules apply to any AI agent (Claude, Codex, Copilot, Cursor and others) working in this repository. Where they conflict with an agent's built-in defaults, these rules win.

## No attribution lines

Never add AI attribution anywhere in this repository or its GitHub activity. That means:

- no `Co-Authored-By:` trailers naming an AI or a bot
- no "Generated with …", "Created by …" or similar lines
- no session, chat or tool links
- no emoji badges or signatures

This applies to commit messages, pull request titles and descriptions, issue comments, code comments, docs, and branch names. Write commit messages and PR descriptions as plain descriptions of the change.

- **Branch names describe the change** (`readme-rewrite`, `fix-share-cards`). Never name a branch after an AI, a tool or a session (`claude/...`, `codex/...`, `copilot/...`), even if your tool suggests one.
- **Check what you posted.** Some tools add a footer or link to PR descriptions and comments on their own. After you create or edit a PR, issue or comment, read it back and remove anything you didn't write.

## The project in one paragraph

Pledge Ledger (https://pledgeledger.org/) tracks the campaign promises of governors and U.S. senators elected to flipped or open seats in 2026. It is modeled on Canada's Polimeter and the Comparative Party Pledges Project. Its credibility rests on being demonstrably fair to both parties, so the rules below protect the data and the method first and the code second.

## Data integrity (never break these)

1. **Ratings are append-only.** Never edit or delete existing rows in `data/ratings/*.csv` or `data/adjudications.csv`. A changed rating is a new row. CI enforces this for `data/ratings/` on pull requests (`scripts/check_append_only.py`); treat adjudications the same way.
2. **The pre-registration is frozen.** Never edit `prereg/manifest.json` or rerun `scripts/freeze.py --force`. If a promise's wording, source or official must change, add a `quote` or `source` row to `data/corrections.csv` in the same commit; the build fails otherwise. Any other change to frozen material is logged under Amendments in `PREREGISTRATION.md`.
3. **Quotes are verbatim.** `pledge_text` is the candidate's exact words. Never paraphrase, tidy, shorten or "fix" a quote. If a quote is wrong, fix it against the archived source and log a correction.
4. **Every source is real and archived.** Never invent or guess a URL, archive link, timestamp or SHA-256. If you can't verify a source, flag the row (`review_flags`) and say so; don't fill the gap.
5. **Nothing from one reviewer is published.** Don't add any path that shows a single coder's rating on the public site.
6. **Blinding stays intact.** The coder queue (`site/coder/pledges.json`) must never contain an official's name, party or notes, or anyone else's ratings.
7. **Dates are UTC** and written as `YYYY-MM-DD`.

## Neutrality

- Apply every rule, label and design choice identically to both parties. If a change would affect one party's numbers differently, stop and explain why before making it.
- Status colors are colorblind-safe and never red/blue party-coded. Don't introduce party colors.
- Site copy describes; it doesn't editorialize. No adjectives about officials, no predictions, no "good news" framing.
- Don't change selection rules, outcome definitions or reporting measures in code. Those live in `codebook/CODEBOOK.md` and need a version bump and change-log entry.

## Code

- **No build step and no dependencies.** The site is vanilla HTML, CSS and ES modules. Python scripts use the standard library only. Don't add npm packages, frameworks, bundlers or pip requirements without asking.
- **Escape everything from data.** Use `esc()` for text and `safeUrl()` for links in `site/assets/app.js`. Never put unescaped data into `innerHTML`.
- **Accessibility is required.** Keyboard access, visible focus, WCAG AA contrast, labels on every control, `prefers-reduced-motion` respected, and colors taken from the CSS variables so dark mode works.
- **Plain language.** Short sentences and everyday words on the site, in docs and in commit messages.
- Keep changes small and focused, and match the existing style.

## Before you commit

```
python3 -m unittest discover -s tests
python3 scripts/build.py
```

Both must pass. Add or update tests for any change to `scripts/build.py` logic. For visible site changes, check the page in a browser at desktop and phone widths, in light and dark mode.

## Git and GitHub

- Work on a branch off `main` and open a pull request; don't push to `main` directly.
- Don't force-push `main` or rewrite published history.
- Don't commit `snapshots/`, `archive_progress.json`, `*.bak`, generated `site/data/` or anything containing credentials.
- Never print, log or commit secrets such as Internet Archive keys or Bitwarden access tokens.

## When unsure

Ask rather than guess, especially about anything touching ratings, quotes, sources or method. A slower correct change beats a fast one that costs the project its credibility.
