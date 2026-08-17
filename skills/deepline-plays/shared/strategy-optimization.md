# Strategy optimization

Read this when the route is not already proven and the agent must turn a live
provider/source landscape into a cost-effective custom Play.

## Contents

- Vocabulary
- Generate the strategy portfolio
- Model multi-step routes
- Pilot without lying to yourself
- Select the economic portfolio
- Compile the exploit topology
- Stopping rules
- Worked topology examples

## Vocabulary

- **Capability**: one callable tool or data surface.
- **Strategy route**: an end-to-end hypothesis for producing a terminal output.
  It may call several capabilities and mint intermediate identifiers.
- **Optimization unit**: the thing whose coverage matters: row, unique item,
  claim, or completed terminal path.
- **Portfolio**: the complementary strategy routes selected from the pilot.
- **Exploit topology**: the production graph compiled from that portfolio.

Provider names are not strategy names. “Provider A” and “Provider B” can be two
direct-lookup routes. “Resolve domain → search employees → validate title” is a
different strategy even if it uses Provider A at one stage.

## Generate the strategy portfolio

Start from the terminal output and work backward. For every required field ask:

1. Which source could state it directly?
2. Which stable identifier makes that source queryable?
3. How can that identifier be recovered if absent?
4. What independent source can verify the terminal value?
5. Which intermediate work can be reused by other routes?

Cover different source classes before trying prompt variants:

| Source class                      | Useful for                    | Common limitation                 |
| --------------------------------- | ----------------------------- | --------------------------------- |
| Structured company/person index   | Fast filtered recall          | Private coverage ceiling          |
| Search engine or SERP             | Broad public recall           | Needs fetch/extraction and dedupe |
| Official site or primary document | Authoritative verification    | Weak discovery surface            |
| Registry, directory, roster       | Niche identity and role truth | Domain-specific adapters          |
| Job board or event source         | Current intent signals        | Recency and company matching      |
| Customer CRM, warehouse, calls    | First-party fit and history   | Authorized scope only             |
| Contact finder or aggregator      | Terminal email/phone recovery | Requires validated identity       |
| Validator                         | Delivery eligibility          | Verifies; rarely discovers        |

Generate 2–5 routes that disagree about where coverage will come from. Two
queries to the same sourced-answer model are one route family, not independent
exploration.

### Source-family diversity for account-to-person work

Two routes are not independent merely because their tool IDs differ. A title
filter and an employee roster sourced from the same structured-data family can
miss the same companies. When the task needs one current person per named
account and public evidence is available, include both a structured lookup and
an executable public-search-and-extraction route in the same pilot. Record a
`mechanism_class` beside each route in the scorecard and select across measured
coverage, not provider labels.

The public route belongs in the authored Play: preserve its query, fetched URL,
excerpt, and identity gate. A browser/chat search done only after the provider
pilot may recover a person, but it did not compete in selection, cannot reuse a
receipt, and gives no reliable marginal-cost record.

## Model multi-step routes

Represent a dependent strategy inside one `RetrievalRoute.retrieve` callback.
Return terminal items only. Keep intermediate identifiers and outcomes in item
attributes/evidence so the route remains diagnosable.

```typescript
{
  id: 'company-to-verified-contact',
  sourceFamilies: ['company-index', 'people-index', 'contact-provider'],
  queryFamily: 'company resolve then scoped people then contact validation',
  estimatedCreditsPerRow: 4,
  retrieve: async ({ row, rowCtx }) => {
    const company = await resolveCompany(row, rowCtx);
    if (!company || !companyIdentityPasses(company, row)) return [];

    const people = await searchPeople(company, rowCtx);
    const accepted = people.filter((person) => personGate(person, row));
    if (!accepted.length) return [];

    const contact = await recoverAndValidateContact(accepted[0], rowCtx);
    return contact ? [adaptTerminalContact(contact, company)] : [];
  },
}
```

Use stable literal tool-call IDs for each node. A different node needs a
different ID. Tool receipts then cache unchanged calls when the route evolves.

If several strategies share an expensive prerequisite, pilot them independently
so their total economics remain measurable. In the compiled Play, hoist the
winning shared prerequisite into one persisted stage and reuse it.

## Pilot without lying to yourself

Use one schema-probe row, then 3–5 stratified rows. Include an easy row, a normal
row, a sparse/niche row, and a collision-prone row when relevant. Run all
candidate strategies on the same denominator.

Count only terminal outputs that pass the task's gates:

- company identity before company-derived contacts;
- current employer and accepted title before a person counts;
- deliverability or line validity before contact coverage;
- attributable evidence before a research claim counts;
- canonical dedup key before a discovery item counts.

Do not count raw response size. Ten candidates for the wrong company are zero
covered rows.

Record each route attempt as retrieved, no-results, partial, rate-limited,
auth-failed, unreachable, timeout, schema-drift, or error. Only retrieved and
no-results attempts belong in the coverage denominator.

Treat the pilot and exploit as one budget. Before the pilot, reserve:

```text
exploit reserve = max(selected-route admission floor,
                      estimated selected-route exploit credits)
```

An admission floor is the minimum available Deepline balance needed to launch
a call. It is different from the amount ultimately charged. Capture it from
the live tool contract or the first excluded probe. Keep the pilot small enough
that at least one viable strategy remains admissible for the full denominator.

If the catalog does not expose an admission floor:

1. treat it as unknown rather than zero;
2. probe the cheapest or dynamically priced strategy before a high-fanout paid
   route can lower the wallet;
3. request the smallest terminal result count, normally one per pilot row;
4. reuse identical pilot receipts during exploit so pilot coverage is not paid
   for twice;
5. preserve a conservative platform reserve until a live probe proves the
   route remains admissible.

The exploit denominator excludes already solved pilot rows. Estimate remaining
spend on unresolved pilot rows plus non-pilot rows, not on the original input
count again.

## Select the economic portfolio

Treat selection as a small set-cover problem. With 2–8 candidate strategies,
evaluate every portfolio allowed by `portfolioSize` and the credit cap rather
than relying on vendor intuition.

Use this lexicographic objective:

1. maximize verified optimization units covered;
2. minimize estimated Deepline credits for the portfolio;
3. minimize route count and expected latency;
4. maximize summed best task-fit/correctness score for covered units;
5. maximize reliability across evaluable attempts;
6. prefer source/mechanism diversity when otherwise tied.

Eligibility gates define whether a unit is covered. Task-fit scores refine
quality after coverage and cost; they must not make an equally covering route
six times more expensive without an explicit user quality threshold.

For a ranked discovery list, the unit is `row + canonical item`. For one-answer
enrichment, the unit is the denominator row regardless of how many candidates a
route returned. For claim research, the unit is `row + claim`.

Set the route-experiment task controls explicitly for one-answer optimization:

```typescript
const task = {
  question: 'Return one verified answer for every input row.',
  selectionUnit: 'row' as const,
  selectionRequiresEligibility: true,
  optimizationObjective: 'coverage_then_cost' as const,
  minimumPilotRows: 3,
  minimumRelevantRows: 2,
  portfolioSize: 3,
};
```

Use `selectionUnit: 'item'` for ranked discovery. Keep
`selectionRequiresEligibility: true` whenever deterministic fact gates define
what the user can actually ship.

The scorecard must expose per-route coverage, unique contribution, reliability,
estimated credits, and the winning portfolio's marginal contribution. A route
that finds nothing new after cheaper routes is selected does not earn an exploit
slot.

Before promotion, compute the post-pilot balance and reject any selected route
whose admission floor or estimated exploit cost cannot fit. Re-pilot only when
the rejection reveals a materially different feasible route; do not spend the
reserve retrying the same mechanism.

## Compile the exploit topology

Selection chooses capabilities; compilation chooses when to call them.

### One terminal answer per row

Use a conditional waterfall. Order routes by verified marginal fills per credit
from the pilot. Later routes receive only unresolved rows. Stop on the first
terminal output that passes every gate.

```text
rows → cheap direct route → verified fills
                       └→ misses → identifier route → verified fills
                                                └→ misses → aggregator
```

### Ranked discovery

Run complementary routes concurrently because their union is the product. Fuse
on canonical IDs, preserve route provenance, apply eligibility gates, then spend
enrichment only on survivors.

```text
structured search ─┐
SERP extraction ───┼→ canonical fusion → task rerank → survivor enrichment
registry search ───┘
```

### Multi-hop graph

Persist reusable prerequisites. A company-to-contact workflow normally becomes:

```text
company candidates
  → canonical company resolution
  → scoped people strategies in parallel
  → person identity/title gate
  → contact recovery waterfall
  → contact validator
```

Do not run contact providers before the person gate. A cheap wrong identity
poisons every expensive downstream call.

### Claim coverage

Retrieve broad evidence once. Evaluate claim cells mechanically. Send only
missing cells to one materially independent supplemental strategy. Reuse the
broad evidence and recovered identifiers; do not restart the research job.

## Stopping rules

Stop when any condition is met:

- target verified coverage or target list size is reached;
- the next route exceeds the credit cap;
- the next route added no verified unit in the pilot;
- two attempts of the same mechanism family produced no new evidence;
- remaining gaps require a source or credential outside the authorized scope;
- marginal credits per new unit exceed the user's stated value threshold.

Persist unresolved rows and gap reasons. They are the input to a future strategy
iteration, not permission to fabricate values.

Before delivery, compare artifact schemas to the frozen task contract with
code, not visual inspection. Assert exact CSV header names, exact top-level JSON
keys, stable denominator keys, and row counts. Do not substitute `company` for
`company_name`, nest a requested top-level field, or rename a metric without
updating the contract first.

## Worked topology examples

### Find buyers at target companies

Candidate strategies:

1. company domain → scoped people index using function + seniority;
2. company site/team pages → extract named role holders;
3. company LinkedIn identity → employee search → title gate.

Pilot the three strategies. Select the portfolio with the best verified company
coverage. Compile selected discovery strategies in parallel, then run contact
recovery only for identity-gated survivors.

### Research companies from public and private evidence

Candidate strategies:

1. structured company index for firmographics;
2. SERP → official pages → evidence extraction;
3. job/news sources for recent signals;
4. authorized CRM/warehouse join for first-party fit.

Fuse public evidence by canonical company. Keep private facts separately
attributed. Evaluate the requested claim cells, supplement only the gaps, then
synthesize from supported values.
