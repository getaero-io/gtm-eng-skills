# Strategy map: <task>

Write this before binding routes. It is a short, disposable research artifact:
scouts can add cards independently; the parent removes duplicates and compiles
the retained cards into ordinary `SearchProgram` blocks in the Play.

## Contract

- Complete row: <user-visible fields plus evidence>
- Desired coverage / useful floor: <all recoverable rows / explicit floor>
- Deepline-credit ceiling: <cap or unknown>

## Source terrain

For each stage, name places the fact can live before choosing tools. Catalog
actions, public sources, private data, local artifacts, and existing Plays are
all peers.

| Stage                             | Acceptance fact                  | Places it may live                              | Stable join              | First cheap probe   |
| --------------------------------- | -------------------------------- | ----------------------------------------------- | ------------------------ | ------------------- |
| <company / supplied-row / signal> | <what makes this stage complete> | <index; registry; source page>                  | <domain / id / name+geo> | <one scope>         |
| <person / verification / signal>  | <what makes this stage complete> | <people index; leadership page; profile source> | <domain / profile URL>   | <one accepted unit> |

## Candidate route cards

Keep 6–12 cards across the relevant stages. A card needs a different corpus,
join, query geometry, or rescue path. Different vendor labels alone do not make
an independent route.

### <route-id>

- Stage: <stage>
- Hypothesis: <how it completes the stage contract>
- Corpus + lineage: <record family, source owner, or source URL>
- Join and query: <identifier / partition / search geometry>
- Proof: <fields or excerpt that make acceptance safe>
- Mechanism: <described tool | fetch | child Play | local artifact | connector>
- Pilot: <shared unit, max calls, Deepline-credit ceiling>
- Expected miss → rescue: <why it may fail and the next different route>

## Selection

- First wave: <three cards that differ in information geometry>
- Dormant gap routes: <the remaining cards, each with a distinct rescue>
- Excluded false diversity: <same terminal corpus / duplicate join>
- Output receipt: `run-and-export-search-experiment.py` → `{ ok, runId, output }`

## Evaluation plan

Write this when the task repeats, a route/scaffold changes, or a cost claim
needs proof. A pilot is the smallest eval; a provider label is not a concept.

- Concept under test: <source geometry, such as registry → operator proof>
- Frozen contract and denominator: <the same required claims and units for every route>
- Cases: <normal, sparse, and likely-miss units or partitions>
- Hard gates: <identity, freshness, evidence, cohort rules>
- Compare after gates: <verified coverage, marginal Deepline credits/calls, latency, adapter failures>
- Decision: <promote, retain as gap recovery, or exclude, with the failure slice>
