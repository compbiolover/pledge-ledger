# Promise Tracker Codebook

**Version 1.1** (2026-11-08). Every rating records the codebook version it used. If a rule changes, bump the version, log the change at the bottom, and re-code the affected pledges.

This codebook adapts the Comparative Party Pledges Project (CPP) definitions and the Polimeter rating scale, and adds two fields of its own: effort and blocker.

---

## Part 1. Extraction: what counts as a pledge

A **pledge** is a statement committing the candidate to one specific action or outcome that can be clearly determined to have occurred or not (CPP definition).

### 1.1 Inclusion rules
1. **First-party source.** The candidate's own words. In order of preference:
   1. the campaign site or a platform document
   2. a campaign release or campaign post
   3. a debate or forum where the candidate speaks
   4. a news article quoting the candidate directly, inside quotation marks
2. **Before the election.** Statements made after Election Day (victory speeches, transition releases) are not campaign pledges. Code `drop`.
3. **Testable.** A reasonable observer could later say yes or no. "Eliminate the state grocery tax" passes. "Fight for families" fails.
4. **One action per row.** Split compound pledges and give the split rows the same `compound_group`.
5. **Verbatim.** `pledge_text` must match the source word for word. An ellipsis may not remove a condition, amount, date or limit that narrows the pledge.
6. **One pledge, one row.** If the same commitment appears in two sources, keep the most authoritative source and `merge` the other into it.

### 1.2 Extraction review (the task for coders before inauguration)
Each coder independently reviews every pledge and records:

| Field | Values | Rule |
|---|---|---|
| `decision` | `keep`, `drop`, `merge` | `drop` if any inclusion rule fails; `merge` if it duplicates another pledge |
| `merge_into` | pledge_id | Required when `decision = merge` |
| `testable` | `Y`, `N` | Rule 1.1.3 |
| `verbatim_ok` | `Y`, `N` | Open the archived source and check the quote. `N` if words differ or a qualifier was dropped |
| `note` | text | Why, especially for `drop` and `N` |

A pledge stays in the public dataset unless both coders agree to drop or merge it, or an adjudicator decides so.

---

## Part 2. Status rating (from inauguration onward)

Ratings are made **as of a review date** (`period_end`). Default review dates are day 100, day 365 and the end of each legislative session, then end of term. Each review rates every pledge again from scratch, using only evidence dated on or before `period_end`.

### 2.1 Outcome
Rate what happened, judged against the candidate's own wording (amounts, dates, scope).

| Code | Label | Rule |
|---|---|---|
| `kept` | Kept | The action or outcome happened as worded. For a pledge to act ("veto any tax increase"), every relevant occasion so far went the pledged way. |
| `partial` | Partially kept | Some, but not all, of the stated criteria are met: a smaller amount, narrower scope, later date, or only some of a compound list. |
| `in_progress` | In progress | A formal step is underway (bill filed, rule proposed, order drafted, budget line requested) and no final result yet. |
| `not_rated` | Not yet rated | No formal step yet. This is the default at inauguration. |
| `broken` | Broken | Formally reversed or rejected, made impossible, a deadline in the pledge passed unmet, or the term ended without it. |

Tie-breakers:
- A deadline in the pledge ("first session", "by 2028") that passes unmet makes the pledge `broken`, even if work continues. Record the later work in `note`.
- "Work to" or "support" pledges are rated on the outcome named, not on the effort. Effort goes in the effort field.
- A pledge kept and later undone by the same official is `broken`.
- If the evidence is too thin to tell `in_progress` from `not_rated`, choose `not_rated`.

### 2.2 Effort
Rate what the official did, using only observable, documented actions. Never rate intentions.

| Code | Label | Requires evidence of |
|---|---|---|
| `0` | None | No public action during the period |
| `1` | Talk | Only speeches, statements, interviews or posts |
| `2` | Formal start | A bill introduced at the administration's request, an executive order, a budget request, a rule proposal, an appointment, or a task force with a deadline |
| `3` | Spent capital | Leverage used: tied to a must-pass budget, a veto or veto threat, a special session, a public campaign naming holdouts, or a trade-off on another priority |
| `4` | Exhausted options | Every available instrument tried, including executive action, a ballot measure, or litigation where relevant |
| `-1` | Undermined | Signed or backed something contrary, or publicly walked the pledge back |

Rate the **highest** level reached during the period, except that `-1` overrides everything.

### 2.3 Blocker
Code a blocker only when the outcome is not `kept`. Pick the **main** reason the pledge is not kept.

| Code | Meaning | Evidence needed |
|---|---|---|
| `none_attempted` | The official did not try (effort 0–1) | Effort record |
| `legislature_opposition` | The other party's legislators stopped it | Vote, committee inaction, or a named leader's refusal |
| `legislature_own_party` | The official's own party's legislators stopped it | Same, with the legislators named |
| `courts` | A court blocked it | Ruling or injunction |
| `federal` | Federal law, an agency or funding blocked it | Document |
| `voters` | A ballot measure failed | Result |
| `budget` | Revenue shortfall, explicitly cited | Budget document |
| `self_reversed` | The official changed position | Statement or action |
| `too_early` | No deadline has passed and no blocker is visible yet | — |

Name the actors in `note` with sources, for example "Senate Finance chair X declined a hearing, [link]".

### 2.4 Evidence
Each status rating lists its evidence as URLs (`evidence_urls`, separated by `|`), most authoritative first:
1. Enacted text: statute, signed executive order, adopted budget, final rule
2. Official records: roll calls, bill histories, veto messages, agency reports
3. Government press releases
4. News reporting. Use it only for effort and blocker facts, and confirm with two outlets.

Archive every evidence URL (run `scripts/archive_sources.py` on the evidence list).

---

## Part 2b. Senators: effort comes first

A single senator rarely makes a law happen alone, so for senators the **effort** rating is the headline and the outcome is shown second. The outcome still uses the scale in 2.1, judged at the level of policy: did the promised thing happen?

**Pledges a senator can keep alone** (`requires_other_actor = N`: "I will introduce a bill", "I will vote against", "I won't take corporate PAC money", "I will hold a town hall in every county") are rated on the senator's own action, so outcome and effort usually match.

### Effort for senators
| Code | Label | Requires evidence of |
|---|---|---|
| `0` | None | No public action during the period |
| `1` | Talk | Only speeches, statements, interviews or posts |
| `2` | Formal start | Introduced or cosponsored a bill, offered an amendment, voted as pledged on a recorded vote, or sent a formal oversight letter |
| `3` | Spent capital | Led the effort: got a hearing or markup as lead sponsor, whipped votes, used procedural tools (holds, objections to unanimous consent, discharge efforts), traded support, or publicly pressured named holdouts |
| `4` | Exhausted options | Every available route tried: standalone bill, amendment to must-pass legislation, appropriations rider, and procedural pressure |
| `-1` | Undermined | Voted against the pledge, cosponsored something contrary, or publicly walked it back |

A recorded vote counts only when the vote is on the pledged policy itself, not on an unrelated package that happened to contain it, unless the senator publicly tied the vote to the pledge.

### Extra blocker codes for Congress
| Code | Meaning |
|---|---|
| `other_chamber` | Passed the Senate but the House did not act or voted it down |
| `president` | Vetoed, or a veto threat stopped it |
| `filibuster` | Failed a cloture vote despite majority support |

`legislature_opposition` means the other party in the Senate, and `legislature_own_party` means the senator's own party, including leadership declining to schedule a vote.

### Senate instruments
`sponsor_bill`, `vote`, `appropriations`, `oversight`, `nomination`, `constituent_service`, `mixed`, `unclear`.

### Reporting for senators
The headline measure is the share of a senator's rated promises with effort 2 or higher ("took formal action"), with a 95% Wilson interval. Delivery rates are shown second. Senators and governors are never pooled together.

---

## Part 3. Reliability procedure

1. **Two coders, independently.** Each coder uses the rating tool alone. The tool never shows the other coder's ratings.
2. **Partial blinding.** The tool hides the official's name and party. The state is shown because evidence searches need it. This is a real limit of blinding, so agreement scores are reported knowing it.
3. **Agreement.** For each field the build reports percent agreement and Cohen's kappa. Effort uses quadratic-weighted kappa because it is ordinal. The target is κ ≥ 0.70 per field. Below 0.60, stop, revise the codebook, retrain, and re-code.
4. **Consensus.** Values the two coders agree on are published. Disagreements go to an adjudication queue. A third person decides and writes the reason in `data/adjudications.csv`.
5. **Nothing is published from one coder alone.** Until a second rating exists, the public site shows "Not yet rated (review in progress)".
6. **Appeals.** Anyone, including the officials' offices, can open an appeal. Each appeal is logged and answered publicly, and any change is versioned.

---

## Part 4. Reporting rules

- Report outcome and effort separately. Never merge them into one grade.
- Show uncertainty: kept rates come with 95% Wilson intervals.
- Compare cohorts two ways: pooled pledges, and the average of each official's rate (so one long platform does not dominate).
- Always show power context (trifecta or divided government) next to any comparison.
- Report rates out of all pledges, and separately out of pledges whose deadline has passed.

---

## Change log
- **1.1** (2026-11-08): adds senators. Effort-first reporting, a Senate effort scale, three Congress blocker codes and Senate instruments (Part 2b).
- **1.0** (2026-11-07): first full version. Adds effort, blocker and review-date rules to the extraction rules from v0.1.
- **0.1** (2026-11-07): extraction rules used to build the initial dataset.
