# News arms — cost ladder, call mechanics, and the graduation path

Tool IDs confirmed with `deepline tools describe <id> --json` on 2026-09-30; re-verify
per org (catalogs and prices drift, and a provider can be disconnected in your org —
`describe` shows `connected`; check before promising an arm).

## The cost ladder (verify before quoting)

| Arm | Tool ID | Declared price (2026-09-30) | When |
|---|---|---|---|
| Structured company news | `predictleads_company_news_events` | 0.56 credits per call | the default sweep arm: domain-keyed, dated, categorized |
| Structured funding | `predictleads_company_financing_events` | 0.56 credits per call | when funding is on the menu; amounts + round types |
| Funding rounds (alt) | `aviato_get_company_funding_rounds` | 0.14 credits per call | cross-check a funding claim; keyed on website/LinkedIn |
| Google web search, recency-bucketed | `serper_google_search` | 0.02 credits per result | cheap name-keyed arm for a NAMED shortlist; entity discipline applies |
| Google News SERP | `dataforseo_serp_google_news_live_advanced` | usage-based (read after execution) | news-tab results for a shortlist when the structured arm is thin |
| Company news search | `contextdev_post_news_search` | free | alternative news search; `searchBy` is required — read its schema with `describe` before first use |
| Standing news monitor | `deepline_native.company_radar`, `radar_type: company_mentions` | 1.5 credits per accepted event | standing watches — see Graduation |
| Standing leadership-hire monitor | `deepline_native.company_radar`, `radar_type: company_new_hires` | 1.75 credits per accepted event | exec-hire watches; `seniorities` / `job_titles` filters |
| Funding-rounds radar feed | `prebuilt/funding-updates` (play) | read `deepline plays describe prebuilt/funding-updates --json` | pages new funding rounds discovered since a timestamp |

Read the actual charge from the run where you can (`deepline runs get <run-id> --full
--json` for plays); an ad-hoc `tools execute` call is reported at its declared price —
say "declared estimate" when that is what it is.

## Call mechanics

**`predictleads_company_news_events`**: inputs `company_id_or_domain` (required),
`found_at_from` / `found_at_until` (ISO 8601), `categories`, `page`, `limit`. The window
inputs are the whole point — ALWAYS pin them to the sweep window. Note what they bound:
`found_at` is when the provider FOUND the event, not when it happened; still apply the
event-date rule in `signal-menu.md` to whatever date the event carries.

```bash
deepline tools execute predictleads_company_news_events \
  --input '{"company_id_or_domain":"northwind.example","found_at_from":"2026-07-12T00:00:00Z","found_at_until":"2026-08-11T00:00:00Z","limit":25}'
```

**`predictleads_company_financing_events`**: `company_id_or_domain` (required),
`first_seen_at_from` / `first_seen_at_until`, `page`, `limit`. Same window discipline.

**Web-search arms** (`serper_google_search` with `tbs: "qdr:w"` / `"qdr:m"`;
`dataforseo_serp_google_news_live_advanced` with `keyword`): these are keyed on a query
string, not a domain, so every result needs entity discipline (signal-menu rule 4). The
recency bucket bounds when the index saw the page, not when the event happened, and
result dates often arrive as relative strings ("2 days ago") — parse to absolute at
sweep time. Lessons measured on Clay's 1-credit Google News action (2026-08) that apply
to any search-index arm: a quiet result can omit the results field entirely rather than
return an empty list (gate on absence-of-events), and a quiet call still bills.

**Field names**: `describe` does not publish these tools' output fields. Read the first
response before writing the classifier: find the event's title/summary, its date field,
its category, and its source URL, and map Step 4's four non-nullable fields to them.
Gate on the payload's events, not the call's success.

**Many domains**: past ~20 domains, run the sweep as a play (CSV in, one `.withColumn`
per arm) rather than a loop of `tools execute` calls — the play persists every response
in the Customer DB, so a rerun reuses filled cells instead of re-buying them. See the
deepline-gtm skill (`recipes/deepline-plays.md`) for play authoring.

**Window state**: the sweep's only state is the last sweep date. Store it in the
digest (and/or the output table); next window = [last sweep → today]. First sweep uses
the user's lookback. Never run unwindowed.

## Graduation: from sweeps to a Deepline monitor

Windowed sweeps are for lists you look at occasionally. The moment the watch is
STANDING (weekly+ cadence, 100+ accounts, or the user says "always tell me"), the
right shape is a Deepline monitor, not a re-scraping loop:

- Gate first: `deepline monitors status --json`. Only `has_access: true` proceeds;
  otherwise say monitors are access-gated and the user should contact the Deepline team.
- Read the contract: `deepline tools get deepline_native.company_mentions --json` (and
  `deepline_native.company_new_hires` for exec hires). One monitor per domain per radar
  type:

  ```json
  {"key":"northwind-mentions","tool":"deepline_native.company_radar",
   "payload":{"domain":"northwind.example","radar_type":"company_mentions"}}
  ```

  For a list, use a Fleet (`deepline monitors fleets init` / `sync --dry-run`).
- `deepline monitors check '<def>' --json` → `deepline monitors deploy --dry-run '<def>'
  --json` → show the user scope, per-event price and that total volume is unknown →
  deploy only on an explicit yes. Follow the deepline-monitors recipe for the approval
  wording and the 30/60/90-day history ladder.
- Events land in a Customer DB table (`deepline_native.deepline_native_company_mentions`:
  `domain`, `mention_content`, `mention_url`, `mention_channel`, `mention_posted_at`,
  `discovered_at`, …). A play bound with a `sqlListeners` trigger
  (`deepline plays bootstrap monitor-triggered --tool deepline_native.company_radar
  --stream company_mentions`) runs this skill's Step 4-5 (classify → route → digest) on
  each new row exactly as on sweep results.
- Funding has no per-domain monitor here: run `prebuilt/funding-updates` on the cadence
  with `since` = last run, and join its rows to the account list on domain.
- Economics: cost scales with EVENTS, not accounts × sweeps. Don't deploy the same
  domain + radar type twice (the dry-run lists existing monitors that already cover the
  scope), and don't monitor one-shot lists nobody will watch.

This skill can set up and run sweeps end-to-end; the monitor is a hand-off it should
offer with the arithmetic ("your cadence × list size × per-call price vs per-event
price"), not silently build around.
