# Dedupe against the user's existing list

Used in Step 1.0.5 (filter prospect candidates) and Step 7 (validate emails against the company's apex domain). The shipped helper is `scripts/dedupe_utils.py`.

## Why this exists

The common failure mode is shipping a "net-new" list that repeats companies the user has already tried. Two failure modes drive this:

1. **Raw string match misses parent-domain relationships.** `amsynergy.nikon.com` and `nikon.com` are the same buyer, but a naive set lookup treats them as unrelated. On one real run, **24 of 50 "net-new" prospects were already in the CRM** as parent-domain entries the raw-string dedupe missed. Apex normalization with a public-suffix-aware parser fixes this.

2. **Name-only matching is noisy.** "Rocket Propulsion Systems" can collide with an unrelated row that has "rocket propulsion" as a substring. Apex domain is a stronger primary key when it's available.

The fix is a layered check.

## The two-phase match

**Step A — apex domain match.** Normalize both sides to the registrable apex domain. Strip `www.`, strip subdomains to the root, handle multi-label suffixes (`co.uk`, `co.jp`, `com.au`). Use `extract_apex()` from `scripts/dedupe_utils.py`. This is the strong primary key — when it matches, you're done.

**Step B — fuzzy company name fallback.** For candidates that don't match on apex domain (either because the candidate has no website in the input, or the existing list only has names), compare normalized company names with `difflib.SequenceMatcher` ratio ≥ 0.85 after stripping corporate suffixes (Inc, LLC, Ltd, GmbH, SA, AG, Co, Corp, Holdings, Technologies, Systems, etc.). Use `norm_name()` from `scripts/dedupe_utils.py`. **Only as a fallback** — never as the primary check.

## Always ask the user first

Before running any dedupe, ask explicitly: *"Do you have an existing customer list, CRM export, or past outbound list I should dedupe the prospect output against? A CSV with a `domain` column and optionally a `name` column is enough."* If they say no, note it as a caveat in the final report. **Don't silently skip the dedupe** — a downstream user reading the prospect section deserves to know whether one was applied.

## Usage

Sanity-test the helper after install — runs entirely in stdlib:

```bash
python3 scripts/dedupe_utils.py --selftest
```

CLI for one-shot dedupes:

```bash
python3 scripts/dedupe_utils.py \
    --existing customers.csv \
    --candidates prospects_raw.csv \
    --out-actionable prospects_actionable.csv \
    --out-matched prospects_already_known.csv \
    --name-threshold 0.85
```

Library import for pipeline integration:

```python
import sys; sys.path.insert(0, "scripts")
from dedupe_utils import match_against_existing

existing = load_csv("customers.csv")   # rows with 'domain' / 'name' / 'website'
candidates = load_csv("prospects_raw.csv")
actionable, matched = match_against_existing(candidates, existing, name_threshold=0.85)
```

Each row in the output carries a `dedupe_match` field — empty for actionable, populated with the match reason for matched rows (`apex:nikon.com` or `name:astura medical (0.91)`). Surface this in the final report so the user can audit what was excluded and why.

## Don't silently drop matches — categorize them

Even after dedupe, the "already in CRM" bucket often contains accounts still worth outbound, just with a different wedge or timing. Prefer to categorize:

| Category | Treatment |
|---|---|
| **Net-new** (not in existing list) | Standard outbound. |
| **Already in CRM, no opps ever** | Effectively net-new from an activity perspective; surface with a note. |
| **Previously lost / rejected, no active engagement** | Fresh outbound wedge. Flag the previous loss reason so the AE can address it. |
| **Active open opportunity** | Exclude — don't step on an active sales cycle. |
| **Current customer** | Exclude from net-new; expansion is a different motion. |

This categorization requires some signal from the existing list beyond "do they show up" — if the user's list has columns like `opp_count`, `open_count`, `won_count`, `last_opp_date`, use them. If it doesn't, just split into "net-new" vs "already known" and flag the latter for manual triage.
