import { definePlay } from 'deepline';
import type { ColumnMap } from 'deepline';
import {
  DEPTH_SETTINGS,
  cellAgreeingRoutes,
  cellEvidence,
  cellMissReason,
  cellOutput,
  cellScore,
  cellTag,
  cellUncertainty,
  cellValue,
  cellVerdict,
  cellWinningRoute,
  createRouteFanoutEngine,
  routeLedgerSummary,
  type FanoutCell,
  type FanoutCtx,
  type RouteDef,
} from './shared/route-fanout-core';
import {
  emailFieldPlugin,
  phoneFieldPlugin,
} from './shared/route-fanout-fields';
import { signalStrategy } from './shared/route-fanout-signals';
import { researchStrategy } from './shared/route-fanout-research';
import { scoreRoutesAgainstTruth } from './shared/route-fanout-search';

// ===========================================================================
// FAN OUT / FUSE / JUDGE — a DOMAIN-AGNOSTIC, forkable resolution engine
// ===========================================================================
//
// The algorithm (adapted from last30days v3.1.1 weighted RRF): run every route
// against every row concurrently, fuse candidates on a canonical key with
// weighted reciprocal-rank fusion, judge each through a trust gate, blend a
// final score, tag the winner by corroboration, and emit a legible route ledger.
// Judgment stays OUTSIDE the play: the agent plans the inputs and reads the
// ranked comparison; the play is deterministic TypeScript.
//
// DOMAIN-AGNOSTIC BY CONSTRUCTION. All domain-specific judgment lives in a
// ResolutionStrategy (./shared/route-fanout-fields.ts for contacts,
// ./shared/route-fanout-signals.ts for signals). The engine
// (./shared/route-fanout-core.ts, createRouteFanoutEngine) owns everything
// domain-neutral: RRF fusion, the diversity floor, the corroboration/tag
// vocabulary, row isolation, the route ledger, and the route-KIND dispatcher.
//
//   IT RESOLVES ANY TYPE OF THING, NOT JUST CONTACT FIELDS. A strategy's
//   `project` returns an ARBITRARY output: a scalar (email/phone), a structured
//   object (signal: { signal, confidence, evidence_urls }), or a ranked list
//   (research). The durable `output` column holds it verbatim. A route can be
//   ANYTHING that returns candidates — `kind: 'play' | 'tool' | 'fetch' |
//   'agent'` — so a route can be a ctx.runPlay, a provider tool, a durable page
//   fetch (via a web-extract tool), or a deeplineagent read.
//
//   A NEW USE CASE = ONE STRATEGY FILE (extractCandidates / canonicalize /
//   judge / project) + a route list. Register it in PLUGINS. The engine and
//   every other strategy stay untouched — analogous to last30days adding a
//   source handler.
//
//   THE JUDGE VARIES BY STRATEGY. Contact = identity (email: pure, free
//   domain-alignment, with leadmagic as the paid validator; PHONE inverts this —
//   its identity gate IS a PAID trestle_real_contact name_match call that also
//   returns line-type/activity). Signal = CORROBORATION (≥2 independent routes
//   agree, or a primary source confirms — no paid identity call). Before writing
//   a strategy, PROBE the tool/validator response shape with
//   `deepline tools execute <ref> --input '{...}' --json` (provider verdict
//   shapes differ — Trestle's FLAT dotted keys silently broke the first phone
//   pilot) and keep the candidate-shape check STRICT.
//
// TWO MODES, ONE ENGINE. `mode: 'exploit'` (default) runs the winning routes at
// scale and ships the fused per-row value + a per-route ledger. `mode: 'search'`
// runs the SAME fan-out over a small GOLDEN sample (rows carrying a
// `<strategy>__truth` column of known-correct values) and emits a per-route
// SCORECARD — each route's fill / precision / recall against truth, plus the
// engine's fused-winner accuracy. Search is how you pick routes: sweep many
// providers on ~10 golden rows for cents (receipts make re-runs nearly free),
// read the scorecard, then carry the winners into the exploit `routes` list.
// The search scorer is plain deterministic play code (scoreRoutesAgainstTruth
// below), NOT a runtime primitive — golden truth is a CSV convention.
//
// Replay-safety: every I/O op is a ctx.* call. No Date.now / Math.random / fetch.
// A generic fetch route runs through a web-extract TOOL (firecrawl_scrape)
// because a generic engine cannot hold a static literal `ctx.fetch` key.
//
// INPUT PREP: contact strategies expect person rows (first_name, last_name,
// domain, optional company_name / linkedin_url); the signal strategy expects
// company rows (company_name, domain). Real CSVs rarely arrive shaped — split a
// combined "Name" and derive `domain` from a website column BEFORE the run (or
// pass `columns` aliases). For EMAIL, rows without a domain skip as
// `missing_domain`; org-name rows skip as `not_a_person` for PERSON-scoped
// strategies only (the signal strategy is company-scoped, so that guard does not
// fire). Nothing ever fails the run.

// ---------------------------------------------------------------------------
// Row shape. Fork `columns` and this type together for a different source CSV.
// ---------------------------------------------------------------------------
type PersonRow = {
  first_name: string;
  last_name: string;
  domain?: string;
  company_name?: string;
  linkedin_url?: string;
  // Populated per-row from input.domainAliases so the email plugin's identity
  // gate can read declared parent/alias domains without engine plumbing.
  domainAliases?: string[];
  // SEARCH mode only: the known-correct value for this row (golden truth). A CSV
  // convention, not a runtime concept — read from a `<strategy>__truth` column.
  truth?: string;
  // RESEARCH strategy only: the research question for this row and an optional
  // entity to disambiguate. Falls back to company_name/domain as the topic.
  query?: string;
  entity?: string;
};

// ###########################################################################
// ###                                                                     ###
// ###   FORK HERE — edit the `routes` for your fieldClass.                 ###
// ###                                                                     ###
// ###   Each route is one independent way to reach a value; the plugin's  ###
// ###   identity gate + validator do the judging. Confirm refs are live   ###
// ###   before forking:  deepline plays search <field> --json /           ###
// ###   deepline tools search "<field> validation" --json.                ###
// ###                                                                     ###
// ###########################################################################

// EMAIL routes: name+domain waterfall, LinkedIn→email (gated on /in/), a
// FullEnrich aggregator rung, a demoted pattern-guesser. The email plugin's
// leadmagic validator is the shared validation stage.
const emailRoutes: RouteDef<PersonRow>[] = [
  {
    key: 'name_domain_wf',
    weight: 1.0,
    // Quality prior (fusion.py source_weight): a validated, employer-resolving
    // waterfall is the strongest route.
    qualityPrior: 1.0,
    kind: 'play',
    primary: {
      ref: 'prebuilt/name-and-domain-to-email-waterfall',
      buildInput: (row) => ({
        first_name: row.first_name,
        last_name: row.last_name,
        domain: row.domain,
        company_name: row.company_name,
        linkedin_url: row.linkedin_url,
      }),
    },
    // Relaxed tier: drop company_name / linkedin hints so the waterfall probes
    // on name + domain alone (a stricter first pass can starve on bad hints).
    relaxed: {
      ref: 'prebuilt/name-and-domain-to-email-waterfall',
      buildInput: (row) => ({
        first_name: row.first_name,
        last_name: row.last_name,
        domain: row.domain,
      }),
    },
  },
  {
    // LinkedIn profile -> work email. Only fires when the row carries a /in/ URL.
    key: 'linkedin_email',
    weight: 0.9,
    qualityPrior: 0.9,
    kind: 'play',
    runIf: (row) =>
      Boolean(row.linkedin_url && /\/in\//.test(row.linkedin_url)),
    primary: {
      ref: 'prebuilt/person-linkedin-to-email',
      buildInput: (row) => ({ linkedin_url: row.linkedin_url }),
    },
  },
  {
    // Aggregator rung: FullEnrich waterfalls its OWN providers and resolves the
    // contact independently (current employer included), so it does not simply
    // inherit a stale input domain the way a pattern-guesser does.
    key: 'fullenrich_agg',
    weight: 0.8,
    qualityPrior: 0.85,
    kind: 'tool',
    primary: {
      ref: 'fullenrich_bulk_enrich',
      buildInput: (row) => ({
        name: `route-fanout-${row.first_name}-${row.last_name}-${row.domain}`.toLowerCase(),
        wait_for_completion: true,
        max_wait_ms: 120000,
        data: [
          {
            first_name: row.first_name,
            last_name: row.last_name,
            domain: row.domain,
            company_name: row.company_name,
            linkedin_url: row.linkedin_url,
            enrich_fields: ['contact.emails'],
          },
        ],
      }),
    },
  },
  {
    // Pattern-guesser, deliberately DEMOTED below the waterfall (0.4 < 1.0):
    // zerobounce_email_finder guesses <first>.<last>@<input domain>, so it
    // inherits every stale-domain error and fabricates addresses for org-name
    // rows. The org-row guard skips it for non-people, the verdict gate keeps
    // unvalidated guesses out of the column, and the low weight keeps a lone
    // guess from outranking a looked-up record.
    key: 'zerobounce_finder',
    weight: 0.4,
    // Lowest quality prior: a pattern-guesser inherits stale-domain errors.
    qualityPrior: 0.5,
    kind: 'tool',
    primary: {
      ref: 'zerobounce_email_finder',
      buildInput: (row) => ({
        domain: row.domain,
        first_name: row.first_name,
        last_name: row.last_name,
      }),
    },
  },
];

// PHONE routes: provider waterfall (Trestle-validated), an independent mobile
// finder, and a LinkedIn-gated finder. The phone plugin's PAID
// trestle_real_contact call is BOTH its identity gate and its validator.
const phoneRoutes: RouteDef<PersonRow>[] = [
  {
    key: 'person_phone_wf',
    weight: 1.0,
    qualityPrior: 1.0,
    kind: 'play',
    primary: {
      ref: 'prebuilt/person-to-phone',
      buildInput: (row) => ({
        first_name: row.first_name,
        last_name: row.last_name,
        domain: row.domain,
        linkedin_url: row.linkedin_url,
      }),
    },
    relaxed: {
      ref: 'prebuilt/person-to-phone',
      buildInput: (row) => ({
        first_name: row.first_name,
        last_name: row.last_name,
        linkedin_url: row.linkedin_url,
      }),
    },
  },
  {
    key: 'ai_ark_finder',
    weight: 0.8,
    qualityPrior: 0.8,
    kind: 'tool',
    primary: {
      ref: 'ai_ark_mobile_phone_finder',
      buildInput: (row) => ({
        name: `${row.first_name} ${row.last_name}`.trim(),
        domain: row.domain,
        linkedin: row.linkedin_url,
      }),
    },
  },
  {
    key: 'leadmagic_mobile',
    weight: 0.7,
    qualityPrior: 0.75,
    kind: 'tool',
    runIf: (row) =>
      Boolean(row.linkedin_url && /\/in\//.test(row.linkedin_url)),
    primary: {
      ref: 'leadmagic_mobile_finder',
      buildInput: (row) => ({ profile_url: row.linkedin_url }),
    },
  },
];

// SIGNAL routes — a HETEROGENEOUS mix proving a route is anything that returns
// candidates: a hiring-search TOOL, a durable FETCH of the careers page, and a
// deeplineagent READ of that page. The signal strategy's judge is corroboration
// across these, and its output is a structured { signal, confidence,
// evidence_urls } object — all through the same engine, no engine edits.
const signalRoutes: RouteDef<PersonRow>[] = [
  {
    // Hiring-signal search (openwebninja jsearch). Returns live job postings.
    key: 'jsearch_hiring',
    weight: 1.0,
    qualityPrior: 0.8,
    kind: 'tool',
    primary: {
      ref: 'openwebninja_jsearch_search',
      buildInput: (row) => ({
        query: `${row.company_name || row.domain} jobs`,
        num_pages: 1,
      }),
    },
  },
  {
    // PRIMARY source: FETCH the company careers page and scan for hiring terms.
    // A `fetch`-kind route — a durable page fetch, not a contact provider. The
    // engine runs a fetch route through a web-extract tool (firecrawl_scrape)
    // because a generic engine cannot hold a static literal ctx.fetch key.
    key: 'careers_fetch',
    weight: 1.0,
    qualityPrior: 1.0,
    kind: 'fetch',
    runIf: (row) => Boolean(row.domain),
    primary: {
      ref: 'firecrawl_scrape',
      buildInput: (row) => ({
        url: `https://${cleanHost(row.domain)}/careers`,
      }),
      buildUrl: (row) => `https://${cleanHost(row.domain)}/careers`,
    },
    // Relaxed: the site root when /careers 404s.
    relaxed: {
      ref: 'firecrawl_scrape',
      buildInput: (row) => ({ url: `https://${cleanHost(row.domain)}` }),
      buildUrl: (row) => `https://${cleanHost(row.domain)}`,
    },
  },
  {
    // deeplineagent reads the careers page and judges hiring. An `agent` route.
    key: 'agent_read',
    weight: 0.9,
    qualityPrior: 0.9,
    kind: 'agent',
    runIf: (row) => Boolean(row.domain),
    primary: {
      ref: 'deeplineagent',
      buildInput: (row) => ({
        prompt:
          `Is the company at ${cleanHost(row.domain)} (${row.company_name || ''}) ` +
          `actively hiring right now? Check their careers/jobs page. ` +
          `Answer with evidence.`,
        jsonSchema: {
          type: 'object',
          properties: {
            hiring: { type: 'boolean' },
            evidence: { type: 'string' },
            url: { type: 'string' },
          },
          // deeplineagent requires the jsonSchema `required` to list EVERY
          // property (strict extracted-JSON contract).
          required: ['hiring', 'evidence', 'url'],
        },
        maxToolCalls: 4,
      }),
    },
  },
];

// RESEARCH routes — TWO independent web-search tools (corroboration when they
// surface the same source) plus a deeplineagent research read. Topic-agnostic:
// the query is built from the row's question, so the SAME routes answer any
// research question. `research__query` / `entity` columns carry the topic.
const researchRoutes: RouteDef<PersonRow>[] = [
  {
    key: 'serper_web',
    weight: 1.0,
    qualityPrior: 1.0,
    kind: 'tool',
    primary: {
      ref: 'serper_google_search',
      buildInput: (row) => ({ query: researchQuery(row), num: 10 }),
    },
  },
  {
    key: 'exa_web',
    weight: 0.9,
    qualityPrior: 0.9,
    kind: 'tool',
    primary: {
      ref: 'exa_search',
      buildInput: (row) => ({ query: researchQuery(row), num_results: 10 }),
    },
  },
  {
    // A deeplineagent research read — an independent route that returns a
    // structured findings list. Corroborates the search routes.
    key: 'agent_research',
    weight: 0.85,
    qualityPrior: 0.85,
    kind: 'agent',
    primary: {
      ref: 'deeplineagent',
      buildInput: (row) => ({
        prompt:
          `Research this question and return sources: "${researchQuery(row)}". ` +
          `Return the most relevant findings with a title, one-line summary, and URL each.`,
        jsonSchema: {
          type: 'object',
          properties: {
            findings: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  title: { type: 'string' },
                  summary: { type: 'string' },
                  url: { type: 'string' },
                },
                required: ['title', 'summary', 'url'],
              },
            },
          },
          required: ['findings'],
        },
        maxToolCalls: 5,
      }),
    },
  },
];

// The strategy + routes registry. Adding a NEW use case = one entry here + one
// strategy file. The strategy is NOT baked as a silent default — `strategy`
// (a.k.a. `fieldClass`) is required, with a loud fallback + log below.
const PLUGINS = {
  // personScoped strategies get the engine's person org-name guard; the
  // company-scoped signal/research strategies do not (their row IS a topic).
  email: { plugin: emailFieldPlugin, routes: emailRoutes, personScoped: true },
  phone: { plugin: phoneFieldPlugin, routes: phoneRoutes, personScoped: true },
  signal: { plugin: signalStrategy, routes: signalRoutes, personScoped: false },
  research: {
    plugin: researchStrategy,
    routes: researchRoutes,
    personScoped: false,
  },
} as const;

// The research question for a row: explicit query, else the entity/company
// topic, else the domain. Mirrors researchStrategy.questionFor so routes and
// judge agree on the topic.
function researchQuery(row: PersonRow): string {
  return (
    row.query?.trim() ||
    [row.entity, row.company_name].filter(Boolean).join(' ').trim() ||
    row.domain?.trim() ||
    ''
  );
}

type FieldKey = keyof typeof PLUGINS;

// Registrable host from a domain or URL (for fetch URLs and agent prompts).
function cleanHost(value: string | undefined): string {
  return (value ?? '')
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('/')[0]!
    .split('?')[0]!
    .replace(/\.$/, '');
}

const SANE_CREDIT_CAP = 250;

export default definePlay(
  'route-fanout',
  async (
    ctx,
    input: {
      csv: string;
      // Which ResolutionStrategy to run: 'email' | 'phone' | 'signal'. `strategy`
      // is the preferred name; `fieldClass` is the back-compat alias. REQUIRED in
      // spirit — defaults to 'email' with a LOUD log so a missing value is never
      // silent.
      strategy?: FieldKey;
      fieldClass?: FieldKey;
      // 'exploit' (default): run winning routes at scale, ship value + ledger.
      // 'search': same fan-out over a golden sample; emit a per-route accuracy
      // scorecard vs a `<strategy>__truth` column. Use search to pick routes.
      mode?: 'exploit' | 'search';
      columns?: ColumnMap<PersonRow>;
      // Soft budget: bounds how many rows the run processes.
      budget?: number;
      // A route whose yield is below this after pass 1 gets ONE relaxed re-probe.
      yieldFloor?: number;
      // Budget tier (pipeline.py DEPTH_SETTINGS): quick / default / deep. Sets
      // the fused comparison depth. An explicit numeric `depth` overrides it.
      depthTier?: keyof typeof DEPTH_SETTINGS;
      // How many fused candidates per row survive into the comparison output.
      depth?: number;
      // Known alternate/parent domains that count as identity-aligned (email).
      domainAliases?: string[];
    },
  ) => {
    const fieldClass: FieldKey = input.strategy ?? input.fieldClass ?? 'email';
    if (!input.strategy && !input.fieldClass) {
      ctx.log(
        'strategy not set — defaulting to "email". Set strategy explicitly to run phone/signal/etc.',
      );
    }
    const selected = PLUGINS[fieldClass];
    if (!selected) {
      throw new Error(
        `Unknown strategy "${fieldClass}". Known: ${Object.keys(PLUGINS).join(', ')}. Add a ResolutionStrategy to run a new use case.`,
      );
    }
    const mode = input.mode ?? 'exploit';
    ctx.log(
      `mode=${mode} fieldClass=${fieldClass}: ${selected.routes.length} routes`,
    );

    const yieldFloor = clamp(input.yieldFloor ?? 0.5, 0, 1);
    // Depth: explicit numeric wins; else the named budget tier (DEPTH_SETTINGS);
    // else the `default` tier's poolDepth.
    const tierDepth =
      DEPTH_SETTINGS[input.depthTier ?? 'default']?.poolDepth ??
      DEPTH_SETTINGS.default!.poolDepth;
    const depth = Math.max(1, Math.min(input.depth ?? tierDepth, 10));
    const budgetRows =
      input.budget && input.budget > 0 ? input.budget : undefined;
    const aliases = input.domainAliases ?? [];

    const sourceRows = await ctx.csv<PersonRow>(input.csv, {
      columns: {
        first_name: ['first_name', 'First Name', 'FIRST_NAME'],
        last_name: ['last_name', 'Last Name', 'LAST_NAME'],
        domain: ['domain', 'Domain', 'COMPANY_DOMAIN', 'Company Domain'],
        company_name: [
          'company_name',
          'Company',
          'COMPANY_NAME',
          'Company Name',
        ],
        linkedin_url: ['linkedin_url', 'LinkedIn URL', 'LINKEDIN_URL'],
        // RESEARCH strategy topic columns (absent for contact/signal runs).
        query: ['query', 'question', 'research__query', 'Query', 'Question'],
        entity: ['entity', 'Entity', 'subject', 'Subject'],
        // SEARCH mode golden truth. Accept the strategy-specific header first,
        // then any of the field-specific / generic ones (only one is present per
        // sample). Absent in exploit mode — the column just stays blank.
        truth: [
          `${fieldClass}__truth`,
          'email__truth',
          'phone__truth',
          'signal__truth',
          'truth',
          'TRUTH',
          'expected',
          'Expected',
        ],
        ...input.columns,
      },
      // Deliberately NO `required`: a blank domain or unsplit name on ONE row
      // must isolate to that row (skipped with a miss_reason), never fail the run.
    });

    const boundedRows = budgetRows
      ? sourceRows.slice(0, budgetRows)
      : sourceRows;
    // Carry domainAliases onto each row so the email plugin's identity gate reads
    // them without engine plumbing. A cheap map; still a durable dataset feed.
    const preparedRows = boundedRows.map((row) => ({
      ...row,
      domainAliases: aliases,
    }));

    // Build the field-agnostic engine; delegate every field-specific decision to
    // the plugin. The PLAY owns the ctx.dataset chain below (literal column names
    // are a sheet-contract requirement, so the dataset skeleton cannot live in
    // the imported engine); the engine owns the per-cell compute + the ledger.
    const engine = createRouteFanoutEngine<PersonRow, never>(
      ctx as unknown as FanoutCtx,
      {
        plugin: selected.plugin as never,
        routes: selected.routes,
        depth,
        yieldFloor,
        seedIdentity: (row) => ({
          firstName: row.first_name,
          lastName: row.last_name,
          domain: row.domain,
          companyName: row.company_name,
        }),
        // Person-scoped strategies get the engine's org-name guard; the signal
        // strategy is company-scoped, so it does not.
        personScoped: selected.personScoped,
      },
    );

    // FAN OUT / FUSE / JUDGE / TAG — one durable dataset stage. The `cell` column
    // runs the engine's per-row compute; the rest are LITERAL-named projections
    // off that cell. `value` holds the resolved field (email or phone); `field`
    // names which one, so one static sheet contract serves both fieldClasses.
    const enriched = await ctx
      .dataset('fanout', preparedRows)
      .withColumn('cell', (row, rowCtx) =>
        engine.computeCell(row, rowCtx as never),
      )
      .withColumn('field', () => fieldClass)
      // Carry golden truth forward so the search scorer can join it to the cell
      // after materialize. Blank in exploit mode; costs nothing.
      .withColumn('truth', (row) => (row as PersonRow).truth ?? '')
      .withColumn('value', (row) => cellValue(row as { cell?: FanoutCell }))
      // The FULL structured strategy output (JSON) — a scalar for contact
      // strategies, { signal, confidence, evidence_urls } for the signal.
      .withColumn('output', (row) => cellOutput(row as { cell?: FanoutCell }))
      .withColumn('tag', (row) => cellTag(row as { cell?: FanoutCell }))
      .withColumn('miss_reason', (row) =>
        cellMissReason(row as { cell?: FanoutCell }),
      )
      .withColumn('verdict', (row) => cellVerdict(row as { cell?: FanoutCell }))
      .withColumn('score', (row) => cellScore(row as { cell?: FanoutCell }))
      .withColumn('uncertainty', (row) =>
        cellUncertainty(row as { cell?: FanoutCell }),
      )
      .withColumn('winning_route', (row) =>
        cellWinningRoute(row as { cell?: FanoutCell }),
      )
      .withColumn('agreeing_routes', (row) =>
        cellAgreeingRoutes(row as { cell?: FanoutCell }),
      )
      .withColumn('evidence', (row) =>
        cellEvidence(row as { cell?: FanoutCell }),
      )
      .run({
        key: (row, index) =>
          [
            canonicalizeDomainKey(row.domain) || 'no-domain',
            (row.first_name ?? '').trim().toLowerCase() || 'row',
            (row.last_name ?? '').trim().toLowerCase() || String(index),
          ].join('|'),
        description: 'Fan out routes, fuse candidates, judge, and tag per row.',
        onRowError: 'isolate',
      });

    // LEDGER — one row per route, derived from the materialized cells.
    const materialized = (await enriched.materialize(10000)) as Array<{
      cell?: FanoutCell;
      truth?: string;
    }>;
    const ledgerRows = engine.buildLedgerRows(materialized);
    const routeLedger = await ctx
      .dataset('route_ledger', ledgerRows)
      .withColumn('summary', (row) => routeLedgerSummary(row))
      .run({ key: 'route', description: 'Per-route run ledger.' });

    if (mode !== 'search') {
      return { rows: enriched, ledger: routeLedger };
    }

    // SEARCH — score each route (and the engine's fused winner) against the
    // golden truth column, ranked best-first. This is the route-selection output:
    // read it, carry the winners into the exploit `routes` list.
    const scored = scoreRoutesAgainstTruth(
      materialized,
      selected.routes.map((route) => route.key),
      fieldClass,
    );
    const gradedRows = scored[0]?.tested ?? 0;
    if (gradedRows === 0) {
      // Loud failure: search mode is meaningless without golden truth.
      throw new Error(
        `mode="search" needs golden truth: add a "${fieldClass}__truth" column of ` +
          `known-correct values to the sample CSV. No truth values were found on any row.`,
      );
    }
    ctx.log(
      `search: graded ${gradedRows} golden rows across ${scored.length - 1} routes ` +
        `(best: ${scored[0]?.route} precision=${scored[0]?.precision.toFixed(2)})`,
    );
    const scorecard = await ctx
      .dataset('route_scorecard', scored)
      .withColumn('summary', (row) => {
        const base =
          `tested=${row.tested} filled=${row.filled} correct=${row.correct}` +
          ` precision=${row.precision.toFixed(2)} recall=${row.recall.toFixed(2)}`;
        // An uncredentialed route never ran — its 0.0 is not a fair score. Flag
        // it distinctly so route selection connects it instead of discarding it.
        if (row.uncredentialed) {
          return (
            `route ${row.route}: UNCREDENTIALED — connect this provider and re-run; ` +
            `the 0.0 score is not a measurement. ${base} no_cred=${row.no_credential}`
          );
        }
        return base;
      })
      .run({
        key: 'route',
        description: 'Per-route accuracy vs golden truth (search mode).',
      });

    return { rows: enriched, ledger: routeLedger, scorecard };
  },
  {
    description:
      'Fan out configured routes over each row for a chosen strategy (email/phone/signal), fuse candidate values with weighted reciprocal-rank fusion, judge with a per-field identity gate and validator, and emit ranked cells plus a per-route ledger. mode="search" grades every route against a golden `<strategy>__truth` column and emits an accuracy scorecard for route selection.',
    billing: { maxCreditsPerRun: SANE_CREDIT_CAP },
  },
);

// A tiny local domain key normalizer for the row key (registrable host only).
// The plugins own real canonicalization; this only needs a stable, non-empty
// key component so a blank-domain row cannot throw and fail the run.
function canonicalizeDomainKey(value: string | undefined): string {
  const host = (value ?? '')
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('/')[0]!
    .split('?')[0]!
    .replace(/\.$/, '');
  return /^[a-z0-9.-]+\.[a-z]{2,}$/.test(host) ? host : '';
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
