# Evidence lists

Before each review date, `scripts/evidence.py` builds one folder here, named for that date. Both reviewers of a promise get the same list. The rules are in the 2026-11-13 amendment in [`PREREGISTRATION.md`](../PREREGISTRATION.md).

Each folder has:

- `terms.csv`: the search terms for every promise. Code picks them from the promise's own words: the 3 words used least across all promises, after dropping common words, names and places. Nobody picks them by hand.
- `congress.csv`: bills each senator sponsored or cosponsored, from the Congress.gov API.
- `votes.csv`: each senator's Senate roll-call votes, from senate.gov.
- `legiscan.csv`: bills in each governor's state legislature, from LegiScan.
- `gdelt.csv`: news articles naming the official and a search term, from GDELT. GDELT only searches the last 3 months.

An item is listed if it is dated between the official's first day and the review date, and its title has at least 2 of the promise's terms (or the only term, if there is one).

These lists hold no rating, summary or judgment. They miss things: a bill worded differently from the promise won't match. A promise with nothing listed is not evidence that nothing happened. Reviewers still search on their own and cite evidence under codebook section 2.4.

Legislative data from [LegiScan](https://legiscan.com/), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
