# ContactOut hashed identifiers

Read this before planning or running a ContactOut hashed-identifier pass. It behaves unlike every other hash provider in this skill, and the differences cost money.

## Contents

- [Why it cannot waterfall](#why-it-cannot-waterfall)
- [Expect overlap](#expect-overlap)
- [The exclusion trade-off](#the-exclusion-trade-off)
- [What it contributes on Meta](#what-it-contributes-on-meta)
- [Choosing the send set](#choosing-the-send-set)
- [Contract details](#contract-details)

## Why it cannot waterfall

Every other layer runs row by row, so each can skip rows an earlier layer covered. ContactOut cannot, and slotting it into the ladder as another step quietly overspends.

- **The output is unattributed.** You send up to 100 LinkedIn URLs and get back a pool of hashes plus a `matches_found` count. Nothing maps a hash to a person, so after the call you still do not know which of those people were covered.
- **Skipping does not help downstream either.** Because the pool is unattributed, providers running after ContactOut cannot skip anyone. Reordering the ladder recovers nothing.
- **Attribution cannot be bought back.** Re-sending in smaller batches fails twice over: ContactOut bills per matched profile on every call, so a second pass pays for the same people again, and the 5-profile floor means even the smallest legal batch cannot isolate one person. A live 5-profile probe returned 7 hashes for 4 matched profiles, identifying neither which four matched nor whose hash is whose.

So it runs as a bulk pass beside the ladder. The only levers are which rows you send and whether to run it at all.

## What it costs

Look the price up before quoting it. Rates change, and a number written here will be wrong eventually:

```bash
deepline tools describe contactout_get_hashed_email_identifiers --json
```

What does not change is the billing shape, and it is what makes cost comparisons across these providers misleading:

| Billed on | Providers | Consequence |
| --- | --- | --- |
| Each matched profile | ContactOut hashed identifiers | Misses in a batch cost nothing, so the effective cost per row sent falls as match rate falls |
| Each call, hit or miss | The per-row hash providers such as Aviato and LimaData | Every row costs the same whether or not it returns a hash |

So a per-row price comparison flatters ContactOut on a low-match list and penalises it on a high-match one. To compare like for like, multiply ContactOut's per-match price by the match rate you actually observe, then compare that against a per-call provider's price.

When quoting cost to a user, quote per matched profile and say so. At the roughly 75% match rate measured on a real B2B list, a 100-profile batch bills about 75 profiles, so the per-row figure is around three quarters of the per-match price. Presenting that lower number as the price understates the bill.

## Expect overlap

In one production audience run, ContactOut returned 1,691 unique hashes. 979 were already in the pool from other providers and 712 were net-new, so roughly 58% of that spend bought hashes the audience already had. That is a property of the endpoint rather than a mistake in the run, and it is the reason the send set matters.

## The exclusion trade-off

Excluding rows that already carry a hash is the only pre-call saving. On pool size it costs nothing, because the hashes it drops were already in the pool. It is not free in every mode though.

Roughly a quarter to a third of what ContactOut returns is a second or third address for a person it already matched. Measured on two independent samples: 228 matched profiles returned 313 hashes (27% extra), and a separate 100-profile batch returned 111 hashes for 84 matched profiles (24% extra). Excluding a row because it holds an Aviato or LimaData hash forfeits any different address ContactOut would have found for that same person.

| Mode | Send already-hashed rows? | Why |
| --- | --- | --- |
| `cost_effective` | No | A second address for an already-covered person is the least valuable hash available |
| `max_coverage` | Yes | More addresses per person means more chances a platform matches them, and the spend is already approved |

The hash-pool play defaults to excluding and takes `includeRowsWithExistingHash` for the max-coverage case.

Read the coverage columns the other layers actually write. The hash providers here populate named per-provider columns such as `aviato_hash` and `limadata_hash`. A check that only reads `email_sha256` finds nothing on a real workflow CSV and sends every already-covered row while reporting that it excluded them.

## What it contributes on Meta

From the same production run, two audiences differing only by ContactOut's contribution:

| Audience | Rows | Matched | Match rate |
| --- | --- | --- | --- |
| Baseline only | 9,670 | 2,800-3,300 | 31.5% |
| Baseline plus ContactOut | 10,382 | 3,000-3,600 | 31.8% |

The 712 rows it added brought roughly 250 matched people, an incremental match rate near 35% against an audience averaging 31.5%. The rows it contributes match better than the list as a whole.

Note that the overall percentage moved only 31.5% to 31.8% while 250 more real people became reachable. Judge this on matched people, not the ratio.

## Choosing the send set

Decide on inputs known before the call:

| Situation | Do |
| --- | --- |
| Many rows have a verified LinkedIn URL and no personal hash | Send those rows. Best case, lowest overlap. |
| Most rows already carry a hash, `cost_effective` | Send only the rows still missing one. |
| Most rows already carry a hash, `max_coverage` | Send them anyway, for the additional addresses. |
| Few rows have a verified LinkedIn URL | Skip it, or run LinkedIn repair first. A LinkedIn URL is the only accepted input. |
| Strict cost control on a small list | Skip it. Per-row providers give attributable spend; this one does not. |

## Contract details

- Batch of 5 to 100 unique LinkedIn URLs. Fewer than 5 is rejected with HTTP 400.
- A chunk where nothing matches returns HTTP 404 `No hashed emails found`. That is a normal empty result, not a failure, and it is not billed. Keep processing the other chunks.
- Billing reads `matches_found`, never the length of `matches.emails`. One matched profile can return several hashes, so the hash list overstates the charge.
- Merge results into the audience-level hash pool, never into per-row `email_sha256` cells.
- Report contribution as net-new hashes added to the pool plus the summed `matches_found`. A per-row hit rate is not computable here, so quoting one would be invented.
