# Pledge extraction rules (codebook v0.1)

A pledge = a statement committing the candidate to ONE specific action or outcome that can be clearly
determined to have occurred or not (Comparative Party Pledges Project definition).

Include:
- Only the candidate's own words from first-party sources, in this priority order:
  1. campaign website issues/policy pages or platform PDFs (source_type=campaign_site)
  2. campaign press releases or official campaign social posts (source_type=campaign_release)
  3. debate transcripts or video where the candidate speaks (source_type=debate)
  4. news articles quoting the candidate DIRECTLY in quotation marks (source_type=news_quote) - last resort
- Testable statements only. "Cut the grocery tax to zero" = yes. "Fight for families" = no.
- Split compound promises into one row per action; give split rows the same compound_group value.
- The fulfillment criteria come from the candidate's wording (amounts, dates, scope) - copy them exactly.
- pledge_text = verbatim quote of the promise sentence(s), max ~40 words. Never paraphrase in this field.

Fields (CSV, header exactly as below, RFC 4180 quoting):
pledge_id,state,official,party,policy_area,pledge_text,source_type,source_url,source_title,date_seen,compound_group,instrument,requires_other_actor,status_quo,salience,extractor_notes

- pledge_id: <STATE>-<NNN>, e.g. GA-001
- policy_area: one of economy_tax, budget, education, health, housing, criminal_justice, immigration,
  environment_energy, infrastructure_transport, labor, social_services, elections_democracy, government_ethics,
  agriculture_rural, guns, reproductive_rights, civil_rights, technology, other
- date_seen: 2026-11-07
- instrument: bill | executive_order | budget | appointment | administrative | ballot_measure | mixed | unclear
- requires_other_actor: Y if the governor cannot do it alone (needs legislature, voters, feds, courts), else N
- status_quo: Y if pledge is to keep/protect/maintain something existing, N if it changes something
- salience: high (headline/repeated issue), medium, low
- extractor_notes: anything a coder should know (e.g. "same pledge also in debate", "vague timing")
