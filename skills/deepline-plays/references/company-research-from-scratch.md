# Company research from scratch

Use this route when company names and domains are not input. It separates the
high-recall question “which entities are candidates?” from the high-precision
question “which evidence actions complete a delivery row?”

## Table of contents

1. Materialize a shared candidate pool
2. Define the row's proof contracts
3. Use admission gates before expensive evidence
4. Author a diversified action frontier
5. Re-plan after every outcome
6. Promote only complete rows
7. Deliver the rows and the decision surface

## 1. Materialize a shared candidate pool

The first Play stage discovers more candidates than the requested count through
one or more cheap source families. Store the company name, discovered domain,
discovery URL, raw-bound excerpt, canonical key, source family, and an explicit
selected/excluded reason. A model-suggested company is only a hypothesis until
the discovery stage returns it; never type a plausible company list into
`pilotRows`.

For a local fuel-delivery example, a candidate needs an official or registry
source that proves both a permitted fuel offer and service in the requested
metro. HVAC, plumbing, equipment, or generic “energy” language is adjacent
service, not an exclusion, when a qualifying fuel offer is also present.
Preserve exclusions such as `wrong_geography`, `adjacent_only`,
`domain_unverified`, and `insufficient_core_evidence`.

The candidate pool is common setup. It is not a winner-take-all topology and
does not need to be repeated by every downstream action. Deduplicate after
filtering by canonical domain or other stable key, then freeze the pool for the
current pilot. If fewer than N candidates pass the core eligibility gate,
return the measured shortfall instead of filling gaps from memory.

## 2. Define the row's proof contracts

| Claim                 | Primary admissible source                                                                    | Terminal proof                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| ICP and service area  | Official service/product/location page or authoritative license/registry                     | Exact permitted offer and requested geography on a final allowed URL or record                   |
| Current operator      | Official leadership/contact page, officer/license record, or independent current-role record | Full name, target company, and allowed current role in one admissible source context             |
| Current hiring signal | Official careers/ATS page or a current verifiable job listing                                | Customer-service/CSR/dispatcher role, active state, and posting date within the requested window |

An official careers navigation item, undated job category, or marketing copy
containing “customer service” is not an active job. A staff testimonial is not
proof of current employment. Preserve either as a source considered and
rejected when it changes the next action.

For a request limited to `owner | operations | customer service | CX`, a bare
`President`, `Manager`, or `employee` title is a miss. The bound source must
establish an allowed role, for example `Owner and President`, `Operations
Manager`, or `Customer Service Supervisor`. A directory listing without a
current-role statement is a lead, not proof.

## 3. Use admission gates before expensive evidence

If a named operator is required, ICP is only the first gate. Run a cheap,
heterogeneous operator screen over the expanded candidate pool and retain the
first N companies that have **both** ICP and source-bound allowed-operator
proof. Keep every `operator_unresolved` near miss in the durable selection
audit. Only then spend on optional hiring checks or expensive comparative
actions.

This changes the economics. The agent does not pay for a hiring signal on a
company that can never satisfy the required operator field. When the source
frontier is thin, expand the candidate pool or adapt to an independent action
family; do not silently relax the role policy.

## 4. Author a diversified action frontier

Use `research-portfolio.ts` after the candidate pool exists. Define each action
as a literal branch and assign a correlation group based on the underlying
corpus, not the vendor logo.

| Operator gap                                       | Source family                             | Correlation group        | Evidence mode                         |
| -------------------------------------------------- | ----------------------------------------- | ------------------------ | ------------------------------------- |
| Official team/contact page                         | Official web                              | `first_party_site`       | terminal evidence                     |
| State/county license or corporate officer record   | Public registry                           | `public_registry`        | terminal evidence if role is explicit |
| Company-scoped people result                       | People database                           | `people_database`        | lead only                             |
| Current company/title validation after people lead | Public professional/current-role artifact | `public_role_validation` | terminal evidence                     |

The people branch is gap-only. First use low-cost official/registry actions. If
they miss, calculate:

```text
maximum_people_credits = unresolved_rows × people_limit × live_credits_per_result
```

Ask for the smallest candidate set that changes the next decision, normally
1–3 people. If that maximum conflicts with the pilot budget or verification
reserve, narrow the query, use a distinct public source family, expand the
candidate pool, or stop with the measured coverage shortfall. A raw people
result is never an operator claim without separate current-role validation.

Do not require every action to retrieve every field. An official source can
settle ICP and service area while a registry settles an operator and an ATS
settles hiring. The final claim contract, not a provider, defines a complete
row.

## 5. Re-plan after every outcome

After a literal action completes:

1. Bind its raw source evidence and evaluate the affected claims with
   `research-experiment.ts`.
2. Record `verified`, `lead_only`, `no_result`, `rejected`, `adapter_failure`,
   or `policy_violation` with observed credits and duration.
3. Recompute the portfolio plan for the same row and phenotype. An
   `adapter_failure` or `policy_violation` produces a terminal stop plan for
   that row, rather than a fallback spend.
4. Execute the highest positive-utility action that fits the remaining budget
   only when the plan selected one.

An adapter failure is an implementation repair, not a source-quality miss. A
no-result or semantic rejection is a real observation and should make an
independent correlation group more attractive than a same-corpus retry.

The task ends when N complete rows are promotable, a retained replacement
candidate can be promoted through the same gates, or the portfolio reports no
positive-utility admissible action. “No source found” is an abstention, never
evidence that a company is not hiring or lacks an operator.

Write this as a literal strategy-artifact transition, not just a data-retention
note:

```text
if candidate.required_claim_actions_exhausted and complete_rows < N:
    preserve(candidate, exclusion_or_unresolved_reason)
    advance(next_retained_or_bounded_expansion_candidate)
    rerun(the_same_required_claim_gates)
else if complete_rows == N:
    stop_success
else if candidate_pool_exhausted:
    stop_measured_shortfall
```

`preserve all near misses` without `advance the next candidate` is not an
adaptive cohort policy. It is a record of a partial failure. The agent must
name the successor mechanism, its bounded expansion condition, and the exact
promotion denominator.

## 6. Promote only complete rows

Compile the final action outcomes through the research experiment. If the user
asked for N fully populated rows, set:

```ts
promotion: {
  require: {
    minimumVerifiedRequiredClaimCoverage: 1,
    minimumCompleteRows: N,
    noAdapterFailures: true,
    noPolicyViolations: true,
    noUnknownDeeplineCredits: true,
  },
}
```

Only fields the user explicitly permits to remain unresolved are optional. For
the fuel-delivery example, a positive hiring signal may remain unresolved, but
company, domain, service area, ICP verdict, and named operator do not. A 3/3
ICP, 2/3 operator cohort is a failed selection state: screen the next retained
candidate or report the shortfall. Do not write a finalizer that hard-codes a
person or relaxes an earlier role rejection.

## 7. Deliver the rows and the decision surface

The customer-facing table is an exact projection of the completed Play output.
Alongside it, preserve the candidate selection audit, per-action decision
artifacts, source URLs/excerpts, claim outcomes, and the reason an unresolved
field stopped. Never use a browser result to fill a final field after the run.

For a cheap pilot, report the observed Deepline credit delta, not provider
spend. Explain what to scale only after the selected action path has verified
the requested contract on the pilot denominator.
