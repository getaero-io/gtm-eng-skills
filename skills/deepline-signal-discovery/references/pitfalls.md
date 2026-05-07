# Common pitfalls (full list)

The most critical pitfalls are kept inline in `SKILL.md`. This file is the long form — read it when you hit unexpected behavior or before shipping a report.

## Pipeline execution

1. **Skipping target discovery (Step 0)** — Without understanding what the target sells, you'll generate generic/irrelevant configs.
2. **Homepage-only scraping** — Always use multi-page discovery. Homepage alone misses pricing, integrations, security, careers.
3. **Using hardcoded examples** — Don't copy sales-focused keywords for a creative-ops tool. Generate configs per vertical.
4. **Skipping config review (Step 3.5)** — Always validate generated configs against enriched data before analysis.
5. **Running analysis immediately after enrichment** — `deepline enrich` returns to terminal before OS buffers flush. Run the file completeness check in Step 3 before executing `analyze_signals.py`. A `won_with_jobs: 0` result when you expect data is the symptom; re-running the analysis (without re-enriching) fixes it.
6. **Duplicate domains in input** — CRM exports often have the same company in both won and lost (multiple deals). Deepline only fetches job listings once per domain, so the duplicate's job data lands on one row only — silently undercounting `won_with_jobs`. Always deduplicate in Step 1.

## Signal interpretation

7. **Generic tech stack** — "AWS", "GitHub", "Slack" appear on most B2B sites and aren't differentiating. Search for niche SaaS tools specific to the buyer persona (e.g., Figma for creative teams, NetSuite for finance teams).
8. **Ignoring source context** — "prospect" on a product page = seller signal. "prospect" in a job listing = buyer signal. Same keyword, opposite meaning.
9. **Missing lost data** — Verify lost companies have content before analysis. Empty lost = meaningless lift scores.
10. **Substring false positives** — "sequenc" matches "consequences". Spot-check high-lift keywords for false matches.
11. **Treating vendor signals as buyer signals** — "accounts receivable automation" on a company's product page means they SELL AR tools (competitor). The same phrase in a job listing means they NEED AR tools (buyer). Source context is everything — see `references/signal-interpretation.md`.
12. **Trusting n=1 signals** — A signal in 1 won company with 0 lost = mathematically high lift but statistically meaningless. Require 3+ companies for Tier 1 scoring signals. Flag single-company signals in the report with a verification note.
13. **Including generic business words as signals** — "platform", "automat*", "integrat*" appear at near-identical rates in won and lost (1.0-1.1x lift). These are baseline terms, not differentiators. Focus on signals with lift > 1.5x that are specific to the target's vertical.

## Data hygiene

14. **Domain mismatches in auto-extracted lists** — When using CRM exports or automated customer discovery, domain → company name mapping can be wrong. In actual runs, up to 53% of auto-extracted domains were false positives. Always validate domains against expected company names before enrichment.
15. **Expecting website signals for back-office tools** — Companies buying AR automation, billing, or compliance tools don't discuss these needs on their marketing websites. For these verticals, rely on job listings (hiring AR Manager = budget + pain), tech stack (NetSuite, Salesforce in jobs), and firmographics (wholesale/distribution/manufacturing) instead.

## Dedupe + prospect output

16. **Raw-string dedupe that misses parent domains** — `amsynergy.nikon.com` and `nikon.com` are the same buyer. A naive set lookup treats them as unrelated and ships Nikon twice on the prospect list. Always normalize to apex domain with a public-suffix-aware parser (`scripts/dedupe_utils.py:extract_apex()`) BEFORE comparing. On one real run, **24 of 50 "net-new" prospects were already in the CRM** as parent-domain entries the raw-string dedupe missed. See `references/dedupe.md`.
17. **Shipping a signal report without a prospect list** — The signals tell you what to look for; they don't tell you who to email tomorrow morning. A report that stops at the scoring model forces the reader to do their own prospecting pass — exactly the expensive thing they were hoping to skip. Step 7 (top 10 prospects) is required, not a nice-to-have.
18. **Trusting confirmation-biased CRM fields as signals** — Catalyst note count, champions/DM counts, OCR-derived fields, MEDDPICC picklists are all downstream artifacts of AE engagement. They correlate with win-rate because AEs work the deals they think will win, not because these properties cause wins. On one real run, catalyst note count showed "109x lift" — the most extreme signal in the dataset — and was this close to making the TL;DR before we caught the direction of causality. See `references/scoring-pitfalls.md`.
