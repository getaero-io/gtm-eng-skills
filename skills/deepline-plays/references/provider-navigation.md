# Provider navigation: source geometry to scale path

Use this reference when a category browse does not reveal the right information
path, or when a successful probe must become a bounded production mechanism.
Providers are implementations of stages. The mechanism is the full path from
input uncertainty to terminal evidence.

## Table of contents

1. Start from the contract
2. Browse the capability map
3. Choose a source geometry
4. Design seams
5. Probe, pattern, scale
6. Preserve lineage
7. Evaluate mechanisms
8. Compile the waterfall

## Start from the contract

Record:

- input unit and canonical result identity;
- required claims and accepted terminal evidence;
- cohort rules with fixed denominators;
- target count, freshness, latency, and Deepline credit caps.

The contract distinguishes a candidate from a completed row. Search output can
nominate an entity or page. Only evidence accepted by the claim contract can
complete it.

## Browse the capability map

```bash
deepline tools list
deepline tools list <category> --json
deepline tools search "<information role and controls>" --json
deepline tools grep "<literal capability or provider>" --json
deepline tools describe <tool-id> --json
```

Start with `tools list`, not a remembered vendor. The first command enumerates
the live categories. The second gives the exhaustive provider inventory inside
one category. Search ranks likely actions. Grep finds literal capabilities.
Keep the exhaustive category result as the candidate pool. Describe the small
initial wave and every action whose mapping you bind into a dormant program:
IDs, schemas, result paths, limits, async behavior, Deepline credit ceilings,
and whether an empty result is charged. A new catalog action should become an
eligible challenger without forcing it across every row.

Names and payloads are live catalog facts. Categories and information roles are
the durable reasoning layer.

## Choose a source geometry

| Geometry                    | Best first move                                            |
| --------------------------- | ---------------------------------------------------------- |
| Crisp entity filters        | Structured company, people, jobs, maps, or registry search |
| Unknown public source       | Web/SERP or semantic research to discover candidate URLs   |
| Known authoritative page    | Fetch or scrape that page directly                         |
| Known domain, unknown paths | Map or sitemap, select URLs, then retrieve content         |
| Bounded linked section      | Capped crawl with explicit path and page limits            |
| Variable page layouts       | Schema-guided extraction over the smallest known URL set   |
| Private operational fact    | CRM, warehouse, product, intent, or first-party event join |
| Partial identity            | Identity resolution before downstream enrichment           |
| Repeated known-row lookup   | Batch action or governed row-wise execution                |

Source geometry determines the mechanism. Vendor reputation does not.

## Design seams

A seam is the artifact one stage gives the next. Prefer seams that survive a
provider swap:

- canonical entity key;
- candidate URL or bounded URL set;
- structured provider record with stable identifiers;
- raw source text plus exact excerpt;
- unresolved claim IDs;
- typed miss or adapter failure.

Examples of mechanisms:

```text
structured candidate search → canonical domain → official page → bound claim
web source discovery → selected directory → pagination adapter → bound rows
known people → identity resolution → contact lookup → independent validation
company set → job/event search → dated source retrieval → signal claim
```

The seam, not the provider response object, is what makes a route composable.

## Probe, pattern, scale

1. **Probe:** register broadly, then compare a small maximally heterogeneous
   wave on the same representative units. Preserve queries, URLs, calls,
   misses, raw source types, and every dormant eligible program.
2. **Pattern:** identify the durable access path: stable filter, entity key,
   directory pagination, sitemap section, URL prefix, or page template.
3. **Scale:** replace repeated open-ended discovery with the cheapest bounded
   path that follows the pattern: batch lookup, direct fetch, map plus selected
   retrieval, capped crawl, or provider pagination.

The seed provider need not be the scale provider. A search may reveal an
official directory that direct retrieval can traverse more completely and
cheaply. Re-probe when the source template, query policy, or acceptance rule
changes.

## Preserve lineage

Consensus is agreement between independent terminal sources, not agreement
between APIs. Provider siblings remain useful route competitors because their
coverage, latency, and Deepline-credit behavior can differ; they simply do not
create extra evidence lineages when they terminate at the same source.

For every accepted claim, retain the terminal URL or record, publisher/owner,
raw excerpt, retrieval time, and provider action. Group duplicate URLs,
syndicated copies, and providers backed by the same corpus into one lineage.
Keep discovery provenance separate from terminal evidence provenance.

An official page and a public registry may form two lineages. Two search tools
returning the same page form one. A model may reject a bound excerpt that fails
the contract; it cannot create absent evidence.

## Evaluate mechanisms

Each program card states:

```text
hypothesis → diversity features → seams → terminal lineage → call/credit cap → expected miss
```

Choose the bounded initial and challenge waves by maximum new diversity-feature
coverage, then known lower Deepline-credit ceilings. Apply hard claim and cohort
gates first, then complete-row yield, unique rescues, adapter stability,
observed Deepline credits, and calls. A catalog credit ceiling is a bound, not
observed spend. An adapter failure is not a source miss, and a source miss is
not proof that the entity lacks the fact. Confirmed uncharged misses justify
broader challenge waves; unknown cost never becomes zero. Compile the described
pricing unit into `billingUnit`; only a catalog `result` unit proves that a
source miss cost zero credits.

If the user supplies a total Deepline-credit limit, set
`maximumDeeplineCredits` on the experiment and a ceiling on every registered
program. This is a conservative admission bound, not a substitute for the
opening-minus-closing billing delta.
Do not use `maxFallbacks: 0` as a cost control when the pool has dormant
programs; it disables the very challenge path those programs were registered
for. Use the experiment credit ceiling for spend.

## Compile the waterfall

Promote the smallest dependency-closed portfolio that passes holdout. Preserve
the producer/consumer order and invoke later programs only for unresolved
claims. Keep the registered pool broad and the active waterfall small. On any
unresolved comparison, pilot, holdout, or exploit unit, give untried programs a
bounded heterogeneous challenge and retain them only when they add verified
coverage. Do not re-run the same program/unit pair without new candidate or
evidence state.

The resulting Play should contain literal provider calls, explicit seams,
terminal evidence bindings, and stop conditions. Exploration discovers the
route. The waterfall makes it deterministic, replayable, and economical.
