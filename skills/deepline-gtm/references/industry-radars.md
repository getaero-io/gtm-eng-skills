# Industry radars

`deepline_native.industry_radar` watches an industry instead of a named company or
person. Use it when the request names a topic, a role or "every new" funding
round or company rather than target accounts. Read its live contract with
`deepline describe deepline_native.industry_radar --json` (or the per-type
variant, such as `deepline describe deepline_native.industry_funding_rounds`).

| Signal                  | `radar_type`              | Scope                                          |
| ----------------------- | ------------------------- | ---------------------------------------------- |
| Web and social mentions | `industry_mentions`       | `industry`: the keyword or phrase (required)   |
| Job postings            | `industry_job_openings`   | `industry` (required); optional `countries` ≤5 |
| Funding rounds          | `industry_funding_rounds` | none: every new funding round                  |
| Newly founded companies | `industry_new_companies`  | none: every new company and its founder        |

Adapt the [monitor setup](../recipes/deepline-monitors.md) like this:

- **Scope.** The keyword or country list is the target; there is no company to
  resolve. Take the keyword from the request ("AI agents", "revenue
  operations"). For funding rounds and new companies there is nothing to scope:
  say once, plainly, that the feed brings every new funding round (or newly
  founded company), not only the user's sector, and that each one is charged.
  Give the expected bill from the live price: roughly 150 funding rounds a
  month, and several thousand new companies a month (about 100 a day).
  Narrowing to a sector, country or round size happens in the action Play's
  filter, which changes what is posted, not what is billed. Never pass
  `industry` or `countries` to these two; `monitors check` refuses them.
- **Duplicates.** A workspace holds one monitor per global feed. Before
  deploying one, page `monitors list --state all` and reuse or start the
  existing one.
- **Sample.** New companies get no sample: their history can take hours to
  arrive, so never offer or try one, and deploy without `updates_since` or
  priority. For the other three, use the same sample card and loop with the
  industry definition:

```json
{
  "key": "<signal>",
  "tool": "deepline_native.industry_radar",
  "payload": {
    "radar_type": "<radar type>",
    "industry": "<keyword; omit for funding rounds>",
    "updates_since": "<first window start>"
  },
  "controls": { "execution_type": "priority" }
}
```

Treat funding rounds and mentions of a broad keyword as **very high** volume,
and job openings for a broad keyword as **high**. The funding feed's sample is
the feed itself, so there is no next target to try: when its widest window is
empty, tear it down and say no sample was found.

- **Destination.** For a global feed, recommend the Play filter the request
  implies (for example `company_hq_country = 'United States'` or
  `amount_usd >= 10000000` on funding rounds) and say every match is still
  billed.
- **Price.** Read the live price from `monitors check` or `deploy --dry-run`;
  the four types are priced differently.

To remove an industry monitor for good, run
`deepline monitors delete <key> --yes`; it closes the upstream feed, and its
stored rows remain. Confirm with `deepline monitors get <key>`.
