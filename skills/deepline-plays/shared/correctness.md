# Correctness: golden data and verification

Two disciplines, one spine. Golden data ranks candidate routes against known truth **before** the spend; verification certifies **after** a run what shipped. They share three numbers — coverage, accuracy, cost. Read this when building or tuning an uncertain route (waterfall, provider order, prompt, threshold), before delivering any dataset, whenever the user asks "is this right?", and before scaling any AI/provider-filled column past its pilot.

## The philosophy

Every cell is a claim — a provider response is a claim, an AI column is a claim. The dataset becomes an asset the moment the claims are tested, and stays a liability until then; acting on wrong data (emailing the wrong person, mis-tiering an account) costs more than having no data. **A field is only good when you can name its source and the check it passed.** "Hunter returned it" names a source but no check. "Hunter returned it, the validator says deliverable, and the domain matches the company" is a field you can ship.

Write the test first. Before a single waterfall leg exists, make a golden CSV: ~20 rows where you already know the answer. Twenty rows you know beats a thousand you don't — a route that can't hit known truth on twenty won't earn trust on a thousand. Three consequences of "name the source and the check":

- **Attack every claim from an independent route.** One route agreeing with itself proves nothing; two independent routes agreeing (a second provider, AI web research, the primary source — the company site, a registry, the LinkedIn profile) is probably right; two disagreeing is a finding to investigate before shipping either. Independence is load-bearing: verifying an AI column with the same model and context that produced it just grades the author's own homework.
- **Sample like an auditor, not an optimist.** Check 20-30 rows per property, claimed value next to its evidence, match/miss row by row. A property is trustworthy when its sampled error rate is known and acceptable, not when you stopped finding errors because you stopped looking. Sampled errors are route problems: fix the route, don't patch the cell.
- **Read whole records, not just cells.** Coherence reading catches what no per-column check can: a "1000+ employees, enterprise" account whose headcount says 50; a CTO at a company whose research says two founders and no engineers.

## Score properties, not runs

A run succeeding says the pipeline executed; it says nothing about the data. Judge each property on three numbers and let them decide its fate — ship, re-route, or drop: **coverage** (filled ÷ total); **accuracy** (matches ÷ **filled**, never ÷ total — that conflates didn't-find-it with found-it-wrong); **cost** (credits per filled cell). A property at 40% coverage / high accuracy may be worth keeping with an honest `miss_reason`; one at 95% coverage / 70% accuracy is a liability wearing a success costume. Cost turns "add another fallback leg" from a reflex into a decision.

**Measure billing honestly.** `deepline runs get <id> --full --json` reports only the parent run; charges from `ctx.runPlay` children and per-row provider calls bill under child runs. For any composed play, take the `deepline billing usage` delta between before and after the run.

## Where truth comes from

Ranked by trust: (1) the customer's own closed-won accounts — they know headcount, segment, tier; strongest truth, and building the set with them is the ICP interview made concrete; (2) your own team's phones and emails — the only phone truth whose line-type and activity you can confirm for free; (3) companies you know firsthand (portfolio, past employers, design partners); (4) public anchors (filings, LinkedIn company page, the company's own site).

Mix on purpose: ~14 clean in-ICP rows, ~4 near-misses (right industry wrong size; agency vs product) to test the segment boundary, ~2 known-hard rows (stealth, renamed, catch-all domain). An all-easy set lies — it passes, then fails in production. When a golden row fails, never special-case the row; fix the route, then re-score the whole set.

**Cold start — borrow truth, or grade the first run.** Truth is borrowed or graded, never conjured. **Borrow** (default): with a customer, the kickoff call is the golden set — "15 accounts you know cold, 5 that look right but aren't"; their CRM labels are truth, the near-misses define the boundary. An agent proposes each truth cell with a source link; a human confirms every cell — twenty rows is an hour, and the highest-leverage hour of the build. **Grade** (when truth isn't borrowable): run the candidate route once over 20 raw rows, hand-verify every output against primary sources, and the corrected outputs become the answer key — then add two or three hand-researched rows the route missed, or the set flatters every future route. Phones have no grade path: a stranger's mobile can't be verified without calling it.

## The golden loop — red / green / refactor

- **Red** — write `golden.csv` and the bar first: identifier columns, a `truth_<property>` per target, a `truth_source`, an agreed threshold per property. A property with no stated bar can't fail, so it can't teach you.
- **Green** — build the cheapest candidate route (one provider, one leg), run it over the golden rows, clear the bar.
- **Refactor** — change exactly one thing per run (a provider, its order, a prompt, a gate) to cut cost or raise accuracy without dropping below the bar. One variable per run or you learn nothing.

Two things about TDD don't transfer: providers are probabilistic, so passing is a threshold on a scored sample, not exact-match; and runs are paid, so the set stays small and durable checkpoints keep reruns cheap. Match rules tolerate probabilistic truth: a band for headcount, exact label for segment, the deliverability contract for emails, the validity gate for phones. At n=20 the scorecard is coarse — one row is five points; trust direction and large gaps, never the third decimal. The harness is one play run over the golden CSV; truth columns ride through as ordinary CSV columns and a pure-TypeScript stage scores the match. The export is the scorecard — no framework.

```bash
deepline plays check ./phone-wf-eval.play.ts                        # static, free
deepline plays run ./phone-wf-eval.play.ts --csv golden.csv --watch # one paid ~20-row run
deepline runs export <run-id> --out scored.csv                      # coverage + accuracy fall out
deepline billing usage   # before AND after the run: the delta ÷ filled = cost (runs get undercounts composed plays)
```

```typescript
import { definePlay } from 'deepline';

type GoldenRow = {
  first_name: string;
  last_name: string;
  domain: string;
  truth_phone: string;
};

export default definePlay(
  'phone-wf-eval',
  async (ctx, input: { csv: string }) => {
    const rows = await ctx.csv<GoldenRow>(input.csv, {
      columns: {
        first_name: ['first_name', 'First Name'],
        last_name: ['last_name', 'Last Name'],
        domain: ['domain', 'Company Domain'],
        truth_phone: ['truth_phone'],
      },
      required: ['first_name', 'last_name', 'domain', 'truth_phone'],
    });

    const enriched = await ctx
      .dataset('phone_wf', rows)
      .withColumn('phone', async (row, rowCtx) => {
        const result = await rowCtx.runPlay<{ phone: string | null }>(
          'person_phone',
          'prebuilt/person-to-phone',
          {
            first_name: row.first_name,
            last_name: row.last_name,
            domain: row.domain,
          },
          { description: 'Recover a phone from person identity.' },
        );
        return result.phone ?? null;
      })
      .run({ key: 'domain', description: 'Recover phones for scoring.' });

    const digits = (value: string | null) =>
      (value ?? '').replace(/\D/g, '').slice(-10);
    const scored = await ctx
      .dataset('phone_score', enriched)
      .withColumn('match', (row) =>
        row.phone && digits(row.phone) === digits(row.truth_phone)
          ? 'hit'
          : 'miss',
      )
      .run({ key: 'domain', description: 'Score recovered phones against truth.' });

    return { rows: scored };
  },
  { description: 'Score a candidate phone waterfall against a golden set.' },
);
```

**Checkpoints are the test cache, at two layers.** Rows already filled never re-run their resolver: a filled cell is reused across runs (a null cell — a miss — re-runs, which is exactly what you want when adding a leg). Inside a re-running resolver, every tool call is receipted content-addressed on tool + input, so legs whose call is unchanged replay from the receipt — no provider call, no charge — including legs that previously returned no result. Net: edit leg 3 and re-run, and you pay only leg 3, only on the prior miss rows; the marginal cost of a new leg falls straight out of the billing delta between runs. What busts the cache is changing a leg's tool or input (the step id is not part of the key), a provider action version bump, an explicit `staleAfterSeconds` window rolling over, or `--force`, which recomputes everything.

## Finding the right waterfall

Provider order is a measured, marginal decision, not vendor folklore. Measure all candidates in **one comparison run**: each candidate route its own column, run in parallel (`authoring.md` § Parallelism), and read coverage/accuracy/cost side by side from one golden-set export. Candidates mean the whole category (`deepline tools list <category> --json` — complete recall) swept over a ~10-row batch; keep the top performers as legs and record the also-rans' numbers so the next tuning pass starts from measurements, not memory. On twenty rows, paying every route on every row is cheap and the ranking arrives in minutes. Then assemble the shipped waterfall sequentially — stop-on-first-hit is the *exploit* shape, ordered by marginal reachable-coverage per credit: a leg earns its place only when the correct values it adds, at acceptable accuracy, justify its marginal cost per newly-filled cell. A leg adding 3% coverage at 4× the cost-per-cell gets cut. Dropping legs that weren't paying for themselves — not finding a cheaper provider — is how the same pipeline gets an order of magnitude cheaper without losing coverage.

For phones, validity is read off the golden set, never asserted: mobile/direct coverage on a cold B2B list commonly measures 40-60%, and a route claiming 90% is usually counting switchboard numbers a dialer can't use. Gate with two thresholds — a soft coverage floor and a hard near-zero wrong-number rate, because a wrong number burns a rep's call and the account, so it is worse than a miss. Truth includes line-type and activity, so a returned-but-dead number is a miss: run the validity gate as a third dataset stage with its own key, flipping a digit-match hit to a miss on a bad verdict, before trusting any dialing list.

## Where checks live, and when to stop

Cheapest first, each layer earning the next: (1) **pure columns in the play** — `status`, `miss_reason`, cross-field checks (email domain vs company domain, headcount vs segment) are free code; every paid column deserves a status column, and AI research columns must require evidence in their `jsonSchema` (a claim field without a source field is unverifiable by construction); (2) **a verification pass** re-attacks sampled rows via an independent route (`verified`/`mismatch`/`unresolved`) on the pilot before approval and a sample after; (3) **the plan-vs-built check** diffs what the play does against what was agreed (branches, thresholds, provider order, gates) — a workflow can be perfectly built to the wrong spec, and this is the only check that catches it; (4) **human review** — the 20-30-per-property sample with evidence alongside, surfaced as critical/medium/low. Never present AI-only verification as the last word; its job is to shrink what the human looks at, not replace the look.

Applying it: **work emails** — validate after recovery and coalescing, once per final value; `valid` ships, `catch_all` → `verify_next` (needs a second independent finder/validator; keep the address, name the risk), `invalid` drops, `unknown` unresolved; email domain must match the company domain or you've likely found a previous employer. **Person identity** — the returned name must match and the target company must appear in the person's work history, or it's a same-name stranger; current role is the latest active work entry, not the profile's top-level title. **Phones** — verify line type and activity before any dialing list; a wrong-person number costs more than a missing one.

Stop when the bar is met and the last change moved the numbers by less than a row (inside sampling noise = converged). Golden proves the route (unit tier), a fresh-row pilot catches overfit (integration tier), approval and scale follow. Keep the golden set as a standing regression suite: re-run before every `set-live` and whenever a provider or threshold changes — providers degrade silently, and a dropped bar on twenty known rows is the cheapest detector you'll ever have. Good enough is a number the customer signed off on, not a feeling. The job docs name today's validators and plays; discover current names with `deepline tools search` / `deepline plays search`.
