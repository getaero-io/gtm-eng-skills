# Discover organizational relationships

Public sources cannot guarantee a complete organization tree. Record the search scope and gaps.

## Scope and sources

Record starting identities, former names, jurisdictions, languages, node types, relationship types, effective date, and transaction window. Keep historical matches separate.

Set approved limits for depth, nodes, requests, time, and cost. Limits stop work; they do not establish completeness.

For each source check, retain query, coverage period, retrieval time, evidence, and status. Use `checked`, `unavailable`, `not_applicable`, or `pending`. Explain unavailable and inapplicable checks.

| Source                                    | Use                                          | Limit                                               |
| ----------------------------------------- | -------------------------------------------- | --------------------------------------------------- |
| Registry and ownership filings            | Legal identity, status, disclosed control    | Coverage and update delays vary                     |
| GLEIF relationships and exceptions        | Accounting-consolidation parents             | Exceptions do not prove independence                |
| Annual reports and subsidiary lists       | Dated group members                          | Lists can omit entities or predate transactions     |
| Segment disclosures                       | Activities and operating segments            | Segments need not be legal entities or buying units |
| Deal filings and closing releases         | Parties, completion, date, transferred scope | Partial deals can leave scope unknown               |
| Official brand, location, and legal pages | Units, sites, operators, brands              | Website scope can differ from ownership             |
| Domain and technical evidence             | Candidate sites and aliases                  | Shared services do not prove control                |

Use the defined meaning of each source. GLEIF defines [accounting-consolidation parents](https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-who-owns-whom/roc-policy-on-level-2-data).

For US filers, inspect [Form 8-K](https://www.sec.gov/files/form8-k.pdf) for agreement, completion, and termination evidence. Missing filings do not prove no transaction. Subsidiary lists have [permitted omissions](https://www.ecfr.gov/current/title-17/chapter-II/part-229/section-229.601). [IFRS 8](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-8-operating-segments/) describes operating segments, not legal ownership.

## Search and verify

1. Resolve each starting identity from official evidence.
2. Search the applicable source classes.
3. Queue new candidates with discovery source and proposed type.
4. Expand supported parents, children, units, brands, and locations within scope.
5. Reconcile discovered nodes with source lists.
6. Search another source class for omitted nodes and contrary evidence.
7. Check later closing, termination, sale, restructuring, and renaming evidence.
8. Save unvisited candidates and the stopping reason at each limit.
9. Validate relationship direction, dates, paths, and prohibited cycles.

Track visited identities to avoid repeated expansion. Ask independent reviewers to challenge scope, missing nodes, relationship type, and transferred assets. Model agreement is not source evidence.

## Transaction rules

Keep stage and type separate. Stages include announced, signed, closed, terminated, and unknown. Types include equity purchase, asset purchase, merger, divestiture, minority investment, and joint venture.

Record buyer, seller, parties, affected nodes, effective date, and known exclusions. Leave undisclosed target scope unresolved.

- Announcements and regulatory clearance do not establish completion.
- Asset purchases do not establish acquisition of the seller's legal entity.
- Minority interests do not establish sole control.
- Licenses and franchises do not establish ownership.
- Supported divestitures close the former relationship interval; preserve its history.

## Report coverage

Report source checks, node types, unresolved candidates, conflicts, stale evidence, remaining work, and CRM mapping gaps. Calculate recall only against a complete frozen reference list for the same type, scope, and date.

Assign each unresolved case a next step. Propose refresh intervals for accepted facts. Apply the safety rule before enabling any refresh or notification.

Report partial coverage while required sources, candidates, or transaction scope remain unresolved.
