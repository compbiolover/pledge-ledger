# Pledge Ledger

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24047632.svg)](https://doi.org/10.5281/zenodo.24047632)

**Did they do what they said they would?** Pledge Ledger tracks the specific campaign promises of the 12 governors and 17 U.S. senators who won flipped or open seats in November 2026, and records what happens to each one while they are in office.

**Visit the site: [pledgeledger.org](https://pledgeledger.org/)**

The project is modeled on Canada's Polimeter and the Comparative Party Pledges Project. It applies the same rules to both parties, and it fixed those rules in public before anyone took office.

## What it tracks

- **29 officials:** governors and senators elected in 2026 to a seat they did not already hold. The exact selection rules are in [`PREREGISTRATION.md`](PREREGISTRATION.md).
- **About 1,300 promises,** each one quoted word for word from a campaign source dated before Election Day, with a saved copy on the Wayback Machine.

## How promises are rated

Each promise gets three separate ratings at fixed review dates (day 100, one year, the end of each legislative session, and the end of the term):

| Rating | Question | Examples |
|---|---|---|
| **Outcome** | What happened? | kept, partially kept, in progress, broken |
| **Effort** | How hard did the official push? | only talk, filed a bill, used a veto threat |
| **Blocker** | If it wasn't kept, what stood in the way? | the legislature, the courts, the budget |

Keeping these apart matters. A governor can fight hard for a promise and still lose, or get credit for something that passed without their help. A single senator rarely makes a law happen alone, so for senators effort is the headline and the outcome is shown second.

Full definitions are in the [codebook](codebook/CODEBOOK.md).

## Why you can trust the numbers

- **Rules first, results later.** The list of officials, every promise and the rating rules were frozen on 2026-11-08, before any rating. The fingerprints are in [`prereg/manifest.json`](prereg/manifest.json), archived on [Zenodo](https://doi.org/10.5281/zenodo.24047633). Anyone can check that nothing changed after the fact.
- **Two blind reviewers.** Two people rate every promise on their own. The rating tool hides the official's name and party, and neither reviewer sees the other's ratings. Only ratings they agree on are published. A third person settles disagreements and writes down why.
- **Agreement is measured.** The site reports how often reviewers agreed (Cohen's kappa) for every field.
- **Nothing is overwritten.** Every rating is a new row in a plain CSV file. Changes are logged on the site's [corrections page](https://pledgeledger.org/corrections.html).
- **Uncertainty is shown.** Rates come with 95% intervals. With about a dozen officials per office, the project does not claim that one party is "better".

## Project status

The promise list is frozen. Status ratings start after each official takes office in early 2027. Until two reviewers have rated a promise, the site shows it as "Not yet rated".

## Use the data

Everything is in [`data/`](data/) as plain CSV:

| File | What's in it |
|---|---|
| `officials.csv` | Who is tracked: office, state, party, term dates |
| `pledges.csv` | Every promise: exact quote, source link, archive link, policy area |
| `ratings/*.csv` | Each reviewer's ratings, one row per rating |
| `adjudications.csv` | How disagreements between reviewers were settled |
| `assignments.csv` | Which two reviewers rate each promise, when there are more than two |
| `corrections.csv` | Every fix to a quote, source or rating |
| `power_context.csv` | Which party controls each state legislature |

## Spot a mistake?

If a quote, source or rating looks wrong, [open a review request](https://github.com/compbiolover/pledge-ledger/issues/new?template=review.yml). Anyone can ask, including the officials' offices. Every request is answered in public, and any change is logged.

## Run it yourself

You need Python 3.9 or newer. There is nothing else to install.

```
python3 -m unittest discover -s tests     # run the tests
python3 scripts/build.py                  # check the data and build the site
cd site && python3 -m http.server 8000    # open http://localhost:8000
```

How the build works, how reviews are run and how to add data: [`docs/MAINTAINING.md`](docs/MAINTAINING.md).

## License

Data, codebook and site text: [CC BY 4.0](LICENSE-DATA.md). Code: [MIT](LICENSE). Quoted campaign promises belong to their authors.

## Cite

Willems, A. (2026). *Pledge Ledger: campaign promises of governors and senators elected in 2026* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.24047632

Frozen pre-registration release: https://doi.org/10.5281/zenodo.24047633
