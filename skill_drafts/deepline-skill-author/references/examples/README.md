# Examples

Three of these are **real shipped skills**, projected from the library they were first written for.
Their reasoning is platform-neutral; their arm names and credit figures were measured on Clay's catalogue
(2026-08) and each one says so at the top. Their Step 0 shows the Deepline form. One is
**illustrative**. The distinction is stated because your own skill has to make it too — in its
`## What this skill does not claim` section, in prose — and because an example that claims more than
it has proven teaches the wrong lesson.

| Example | Provenance | Shape | Read it for |
|---|---|---|---|
| [`hiring-radar/`](hiring-radar/) | **shipped skill** | multi-file | an insight that earns its claim with measurement |
| [`account-health-audit/`](account-health-audit/) | **shipped skill** | multi-file | output shape derived from what the data can support |
| [`account-tier-scoring/`](account-tier-scoring/) | **shipped skill** | single-file | that good does not mean long |
| [`low-yield-fallback/`](low-yield-fallback/) | **illustrative** — written for this repo, never evaluated | single-file | the honest low-yield outcome |

## Read these three for the reasoning, not as a house style

They were picked for the quality of the thinking in them, not for being representative of the
library and not for covering the package shapes. Each one does something specific worth stealing.

**`hiring-radar` — an insight is a claim, and a claim needs evidence.** It opens by asserting there
is no such thing as "the number of jobs open at a company," then proves it: four providers, one
company, one day, returning 8,945 / 737 / 384 / 332 for a field each of them calls some variant of
*job count*. Everything downstream — fixing the time window before any call, never mixing providers
inside one cohort, reporting the measurement next to the number — follows from that table. Note what
it does *not* do: it never says "job counts can be unreliable." A vague insight cannot be built on.

**`account-health-audit` — let the data decide the output shape.** It starts from "re-running the
provider that filled the field is not an audit," which is already good, and then keeps going to the
part that actually determines the design: two independent providers disagreed by 51% on one company,
*and each contradicted itself inside its own payload*. Because there is no source of truth to
overwrite toward, the deliverable cannot be a corrected record — so it ships a reviewable delta and
writes nothing back. That is a conclusion, not a preference.

**`account-tier-scoring` — no supporting files, no actions, still excellent.** One file. Its insight
is about picking the right engine — deterministic arithmetic for anything countable, judgment only
where meaning lives — plus the trap that sinks most scoring builds: a missing dimension scored as
zero craters good accounts for being under-enriched. It states where the work runs *because that is
what it costs*, and it ships its weight table so the user can re-tune without rebuilding. If your
skill is one file, this is the bar, not the two above.

**All three name real limits in `## What this skill does not claim`**, and that was a selection
requirement. A line saying "v3 has never been run — a superset of something that passed is an
argument, not a result" tells you more about how to trust a skill than any amount of confident
prose. Write yours the same way.

## The illustrative one

`low-yield-fallback/` has no real counterpart because none of the shipped skills came from a
low-yield source — the library was authored directly, not converted. It shows the *shape* of what the
flow produces when your play has too little in it to convert: a complete, usable skill that
names the interview as the source of its logic, in the body, where a reader will see it. Treat it as
a template for that outcome, not as a validated skill.

## If your idea overlaps one of these

Build it anyway. The flow **carves the boundary** for you, as adjacent jobs in your description,
rather than telling you which jobs are taken. Overlapping PRs are welcome, and if yours does the same
job as an existing skill, saying so in the PR description is what lets a reviewer place it.
