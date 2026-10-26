#!/usr/bin/env node
// Clay workspace -> Deepline Plays. Read-only against Clay; never runs a paid Deepline call.
//
//   node clay-to-deepline.mjs export  <dir> [--rows 25] [--tables t_a,t_b]   # clay CLI -> <dir>
//   node clay-to-deepline.mjs compile <dir>                                 # <dir> -> <dir>/plays/*.play.ts + report
//   node clay-to-deepline.mjs sample  <dir> --table t_x --column "Work Email" [--rows 3 | --row-ids r_a,r_b]  # one column's play
//   node clay-to-deepline.mjs parity  <dir>                                 # formula cells vs Clay's stored values
//   node clay-to-deepline.mjs check   <dir>                                 # deepline plays check on every play (free)
//   node clay-to-deepline.mjs selftest                                      # Clay-semantics assertions, no network
//
// Requires: `clay` CLI logged in to the source workspace (`clay workspaces switch <id>`), `deepline` CLI for
// compile (tool schemas via `deepline describe`) and check. No npm dependencies.
import { execFileSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const [cmd, dir, ...rest] = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = rest.indexOf(`--${name}`);
  return i >= 0 ? rest[i + 1] : dflt;
};
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const writeJson = (p, v) => {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(v, null, 1));
};
const run = (bin, args) =>
  new Promise((resolve) => {
    const p = spawn(bin, args);
    let out = '',
      err = '';
    p.stdout.on('data', (d) => (out += d));
    p.stderr.on('data', (d) => (err += d));
    p.on('close', (code) => resolve({ code, out, err }));
  });
async function pool(items, n, fn) {
  const res = [];
  let i = 0;
  await Promise.all(
    Array.from({ length: n }, async () => {
      while (i < items.length) {
        const k = i++;
        res[k] = await fn(items[k]);
      }
    }),
  );
  return res;
}
async function clay(...args) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const r = await run('clay', args);
    if (r.code === 0) return JSON.parse(r.out);
    if (attempt === 2)
      throw new Error(
        `clay ${args.join(' ')} failed (exit ${r.code}): ${r.err.slice(0, 300)}`,
      );
  }
}

// ---------------------------------------------------------------- export (read-only)
async function exportWorkspace() {
  const paged = async (noun) => {
    const out = [];
    let cursor;
    do {
      const d = await clay(
        noun,
        'list',
        '--limit',
        '100',
        ...(cursor ? ['--cursor', cursor] : []),
      );
      out.push(...(d.data || []));
      cursor = d.data?.length ? d.cursor : undefined;
    } while (cursor);
    return out;
  };
  const who = await clay('whoami');
  const inv = {
    workspace: who.workspace || who,
    exportedAt: new Date().toISOString(),
  };
  for (const noun of ['workbooks', 'tables', 'workflows', 'functions'])
    inv[noun] = await paged(noun);
  const only = opt('tables') ? new Set(opt('tables').split(',')) : null;
  if (only) inv.tables = inv.tables.filter((t) => only.has(t.id));
  writeJson(`${dir}/inventory.json`, inv);
  await pool(inv.tables, 6, async (t) =>
    writeJson(
      `${dir}/columns/${t.id}.json`,
      await clay('tables', 'columns', 'get', t.id),
    ),
  );
  await pool(inv.functions, 6, async (f) =>
    writeJson(
      `${dir}/functions/${f.id}.json`,
      await clay('functions', 'get', f.id),
    ),
  );
  // Which connection each action ran on: the workspace's own key, or Clay's shared one (isClayManaged).
  // `app-accounts list` needs a connection type, so ask for every vendor the actions name; unknown types just fail.
  const used = new Set();
  const types = new Set(Object.values(CLAY_VENDOR));
  for (const t of inv.tables)
    for (const c of readJson(`${dir}/columns/${t.id}.json`).data || []) {
      const s = c.settings || {};
      if (!s.authAccountId) continue;
      used.add(s.authAccountId);
      types.add(clayVendorOf(s.actionKey));
      types.add(s.actionKey.split('-')[0]);
    }
  for (const t of [
    'clearbit',
    'zero-bounce',
    'hunter',
    'people-data-labs',
    'snov-io',
    'anthropic',
    'openai',
    'google-gemini',
    'google-docs',
  ])
    types.add(t);
  const accounts = {};
  await pool([...types], 4, async (type) => {
    const r = await run('clay', [
      'app-accounts',
      'list',
      '--filter',
      `type=${type}`,
    ]);
    if (r.code === 0)
      for (const a of JSON.parse(r.out).data || [])
        if (used.has(a.id))
          accounts[a.id] = { type: a.type, isClayManaged: a.isClayManaged };
  });
  writeJson(`${dir}/app-accounts.json`, accounts);
  const n = Number(opt('rows', '25'));
  let rows = 0;
  if (n > 0) {
    // `rows list` returns display values only; formulas read structured `fields`, which only `rows get` returns.
    await pool(inv.tables, 4, async (t) => {
      const ids = (
        await clay(
          'tables',
          'rows',
          'list',
          t.id,
          '--limit',
          String(Math.min(n, 100)),
        )
      ).data.map((r) => r.id);
      await pool(ids, 4, async (id) => {
        writeJson(
          `${dir}/rows/${t.id}/${id}.json`,
          await clay('tables', 'rows', 'get', t.id, id),
        );
        rows++;
      });
    });
  }
  console.log(
    JSON.stringify({
      workspace: inv.workspace?.name,
      workbooks: inv.workbooks.length,
      tables: inv.tables.length,
      workflows: inv.workflows.length,
      functions: inv.functions.length,
      rows,
    }),
  );
}

// ---------------------------------------------------------------- Clay formula semantics
// Shared by `parity` (evaluated here) and every generated play (emitted verbatim), so parity tests the shipped code.
const RUNTIME = String.raw`const __clay = (() => {
  const pad = (n) => String(n).padStart(2, '0');
  const fmt = (d, f) => {
    if (Number.isNaN(d.getTime())) return 'Invalid date';
    if (f === undefined) return d.toISOString().replace(/\.\d{3}Z$/, '+00:00');
    const t = { YYYY: String(d.getUTCFullYear()), MM: pad(d.getUTCMonth() + 1), DD: pad(d.getUTCDate()), HH: pad(d.getUTCHours()), mm: pad(d.getUTCMinutes()), ss: pad(d.getUTCSeconds()) };
    return f.replace(/YYYY|MM|DD|HH|mm|ss/g, (k) => t[k]);
  };
  // Subset of moment/lodash used by Clay formulas, UTC. Extend here when the compile report lists a new helper.
  // Default parameters keep the helpers optional-argument in TypeScript, like moment's own signatures.
  const toDate = (o = undefined) => (o === undefined ? new Date() : o?._d ?? new Date(o));
  const MS = { milliseconds: 1, seconds: 1e3, minutes: 6e4, hours: 36e5, days: 864e5, weeks: 6048e5 };
  const moment = (x = undefined) => {
    const d = toDate(x);
    return {
      _d: d,
      format: (f = undefined) => fmt(d, f),
      toISOString: () => d.toISOString(),
      isSame: (o = undefined, unit = 'day') => fmt(d, unit === 'day' ? 'YYYY-MM-DD' : undefined) === fmt(toDate(o), unit === 'day' ? 'YYYY-MM-DD' : undefined),
      isSameOrAfter: (o = undefined) => d.getTime() >= toDate(o).getTime(),
      diff: (o = undefined, unit = 'milliseconds') => Math.trunc((d.getTime() - toDate(o).getTime()) / (MS[String(unit).replace(/s?$/, 's')] ?? 1)),
    };
  };
  const _ = { uniq: (a) => (a == null ? [] : [...new Set(a)]), keys: (o) => (o == null ? [] : Object.keys(o)) };
  // formatForJSON escapes text for use inside an already-quoted JSON string (every observed use is '"\\"" + Clay.formatForJSON(x) + "\\""').
  const Clay = { formatForJSON: (v) => JSON.stringify(typeof v === 'string' ? v : v == null ? '' : JSON.stringify(v)).slice(1, -1), formatForAIPrompt: (v) => (v !== null && typeof v === 'object' ? JSON.stringify(v) : (v ?? '')), formatForJS: (v) => v };
  // A {{column}} reference: CSV seeds arrive as text, so JSON objects/arrays are parsed back and '' means empty.
  const ref = (v) => {
    if (v === null || v === '') return undefined;
    if (typeof v === 'string' && /^[\[{]/.test(v.trim())) { try { return JSON.parse(v); } catch { return v; } }
    return v;
  };
  // {{col}} plus its property path resolves as one lookup: a missing column or path is '' (falsy, and empty in
  // string concatenation), never undefined. Method calls after the path run on the resolved value.
  // A provider that returns a string where Clay's vendor returned a list ({{finder}}?.email?.[0]?.email) still
  // satisfies the path: a string followed by [index].field is that field.
  const get = (v, keys) => {
    let x = ref(v);
    for (let i = 0; i < keys.length; i++) {
      if (x === undefined || x === null) return '';
      if (typeof x === 'string' && typeof keys[i] === 'number' && keys[i] === 0 && typeof keys[i + 1] === 'string') { i++; continue; }
      x = x[keys[i]];
    }
    return x === undefined || x === null ? '' : x;
  };
  // Clay stores formula output as trimmed text, then applies the column's data type.
  const EMAIL = /^[A-Za-z0-9!#$%&'*+/=?^_\x60{|}~-]+(\.[A-Za-z0-9!#$%&'*+/=?^_\x60{|}~-]+)*@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$/;
  const out = (v, type) => {
    if (v === undefined || v === null || (typeof v === 'number' && Number.isNaN(v))) return null;
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v).trim();
    // Clay leaves an over-long formula result empty. Inferred limit: observed data kept 8,055 chars, dropped 8,422.
    if (s === '' || s.length > 8192) return null;
    if (type === 'url') return /^\S+\.[A-Za-z]{2,}\S*$/.test(s) ? s : null;
    if (type === 'email') return EMAIL.test(s) ? s : null;
    if (type === 'date') { const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) || /^\d{4}-\d\d-\d\d$/.test(s) ? s : s.replace(' ', 'T') + 'Z'); return Number.isNaN(d.getTime()) ? null : d.toISOString(); }
    return s;
  };
  // Drops empty values (Clay removeBlankValues). JSON round-trip also types the result as any for tool inputs.
  const compact = (o) => JSON.parse(JSON.stringify(o, (_k, v) => (v === null || v === '' ? undefined : v)) ?? '{}');
  const list = (...v) => v.flat().filter((x) => x !== undefined && x !== null && x !== '');
  const hubspotType = (t) => ({ '0-1': 'contacts', '0-2': 'companies', '0-3': 'deals', '0-5': 'tickets' })[String(t)] ?? String(t);
  const soqlValue = (v) => "'" + String(v ?? '').replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
  const soql = (object, where, select) => {
    const cols = list(select).join(',') || 'Id';
    const conds = Object.entries(compact(where)).map(([k, v]) => k + ' = ' + soqlValue(v));
    return 'SELECT ' + cols + ' FROM ' + object + (conds.length ? ' WHERE ' + conds.join(' AND ') : '') + ' LIMIT 1';
  };
  const hash = (v) => { let h = 5381; for (const c of JSON.stringify(v)) h = ((h * 33) ^ c.charCodeAt(0)) >>> 0; return h.toString(36); };
  // Clay waterfall column: the first step formula with a non-empty result, in the user's configured order.
  const waterfall = (...steps) => { for (const s of steps) { const v = s(); if (out(v) !== null && v !== false) return v; } return undefined; };
  // A provider column read by a Clay formula. Clay formulas address Clay's field names ({{finder}}?.email); a Deepline
  // tool response nests them (rawV2.contact.email). A name present on the object resolves directly (Clay's own
  // cells, so parity stays exact); otherwise it resolves to the first non-null field of that name, breadth-first,
  // rawV2 before the rest of the envelope.
  const kids = (o) => (Array.isArray(o) ? o : [o.rawV2 ?? o.raw, ...Object.entries(o).filter(([k]) => k !== 'raw' && k !== 'rawV2' && k !== 'meta').map(([, v]) => v)]).filter((v) => v && typeof v === 'object');
  // A same-named nested field is unwrapped (Prospeo: person.email = { email, status }).
  // A same-named nested field is unwrapped (Prospeo: person.email = { email, status }), as is an email/phone object.
  const unwrap = (x, k) => {
    while (x && typeof x === 'object' && !Array.isArray(x)) { const leaf = k in x ? k : /email$/i.test(k) && 'email' in x ? 'email' : /phone$/i.test(k) && 'phone' in x ? 'phone' : null; if (!leaf) break; x = x[leaf]; }
    return x;
  };
  // Vendor fields renamed between the API version Clay calls and the one Deepline calls.
  const ALIASES = { most_probable_email: ['most_probable_work_email'], most_probable_phone: ['most_probable_mobile_phone'] };
  const find1 = (o, k) => { const q = [o]; for (let n = 0; q.length && n < 5000; n++) { const x = q.shift(); const v = Array.isArray(x) ? undefined : unwrap(x[k], k); if (v !== undefined && v !== null) return v; q.push(...kids(x)); } return undefined; };
  const find = (o, k) => { for (const name of [k, ...(ALIASES[k] || [])]) { const v = find1(o, name); if (v !== undefined) return v; } return undefined; };
  // Clay wraps some provider results in data/person/result; a Deepline response without that wrapper passes through.
  const WRAPPERS = new Set(['data', 'person', 'result']);
  const view = (v) => { const o = ref(v); if (!o || typeof o !== 'object') return o; return new Proxy(o, { get: (t, k) => { if (typeof k !== 'string') return t[k]; const x = k in t ? t[k] : find(t, k) ?? (WRAPPERS.has(k) && !Array.isArray(t) ? t : undefined); return x && typeof x === 'object' ? view(x) : x; } }); };
  // Clay does not run a column whose required input is empty.
  const hasRequired = (input, keys) => keys.every((k) => { const v = input?.[k]; return v !== undefined && v !== null && v !== '' && !(Array.isArray(v) && !v.length); });
  const nameParts = (n) => String(n ?? '').trim().split(/\s+/).filter(Boolean);
  const firstName = (n) => nameParts(n)[0] ?? '';
  const lastName = (n) => nameParts(n).slice(1).join(' ');
  // Clay Google company-to-domain: the first organic result's host, without www. No result is no record.
  const searchDomain = (r) => { const o = r && typeof r === 'object' ? find(r, 'organic') : undefined; const url = Array.isArray(o) ? o[0]?.link : undefined; try { const domain = url && new URL(url).hostname.replace(/^www\./, ''); return domain ? { domain, url } : undefined; } catch { return undefined; } };
  // The entity id a search returned (Crunchbase entities[].uuid, Dealroom items[].id), for the follow-up lookup.
  const entityId = (r) => { const x = r && typeof r === 'object' ? find(r, 'entities') ?? find(r, 'items') : undefined; const e = Array.isArray(x) ? x[0] : undefined; return e?.uuid ?? e?.id ?? undefined; };
  const linkedinSlug = (u) => (String(u ?? '').match(/linkedin\.com\/in\/([^/?#]+)/i) || [])[1] ?? String(u ?? '');
  // Clay cross-table lookup. 'table' is the target table as rows keyed by Clay column name (Clay's CSV export);
  // a hit returns the row the way Clay does: { record } or { records, numberOfResults }.
  const lookupRows = (table, column, op, value) => {
    if (!Array.isArray(table)) throw new Error('Clay cross-table lookup: pass the target table CSV as input.lookup_<tableId>');
    const v = String(value ?? '').trim().toLowerCase();
    if (!v) return [];
    return table.filter((r) => { const x = String(r[column] ?? '').trim().toLowerCase(); return op === 'CONTAIN' ? x.includes(v) : x === v; })
      .map((r) => compact(r));
  };
  const lookup = (table, column, op, value) => { const [record] = lookupRows(table, column, op, value); return record ? { record } : undefined; };
  const lookupMany = (table, column, op, value) => { const records = lookupRows(table, column, op, value); return records.length ? { records, numberOfResults: records.length } : undefined; };
  return { moment, _, Clay, ref, get, out, compact, lookup, lookupMany, list, hubspotType, soql, hash, waterfall, firstName, lastName, linkedinSlug, view, hasRequired, searchDomain, entityId };
})();
const { moment, _, Clay } = __clay;
export { __clay, moment, _, Clay };
`;
// The play bundler reads 'from "..."' / 'import("...")' inside string literals as module specifiers. A unicode
// escape keeps the same string (and the same identifier, e.g. Array.from) while hiding it from that scan.
const hideSpecifiers = (js) =>
  js
    .replace(/\bfrom(\s*["'\x60])/g, 'fro\\u006d$1')
    .replace(/\bimport(\s*\(?\s*["'\x60])/g, '\\u0069mport$1')
    .replace(/\brequire(\s*\(\s*["'\x60])/g, 'requir\\u0065$1');

const REF = /\{\{\s*(f_[A-Za-z0-9_]+)\s*\}\}/g;
const refsOf = (s) => [...String(s ?? '').matchAll(REF)].map((m) => m[1]);
// Clay allows raw newlines inside string literals; JS does not.
function parseable(js) {
  for (const candidate of [js, js.replace(/\r?\n/g, '\\n')]) {
    try {
      new Function('row', `return (${candidate});`);
      return candidate;
    } catch {}
  }
  return null;
}
// `{{f_x}}` -> referenced value. Values come from Clay cells in parity and from row aliases in plays.
// `{{f_x}}?.a?.["b"]?.[0]` (property accesses only, not method calls) becomes one path lookup.
const CHAIN =
  /\{\{\s*(f_[A-Za-z0-9_]+)\s*\}\}((?:\??\.[A-Za-z_$][\w$]*(?![\w$]*\s*(?:\?\.)?\()|(?:\?\.)?\[\s*(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\d+)\s*\])*)/g;
const KEY =
  /\??\.([A-Za-z_$][\w$]*)|(?:\?\.)?\[\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\d+)\s*\]/g;
const pathKeys = (chain) =>
  [...chain.matchAll(KEY)].map((m) =>
    m[1] !== undefined
      ? m[1]
      : /^\d+$/.test(m[2])
        ? Number(m[2])
        : m[2].startsWith("'")
          ? m[2].slice(1, -1).replace(/\\'/g, "'")
          : JSON.parse(m[2]),
  );
const translate = (formula, toRef) =>
  formula.replace(
    CHAIN,
    (_m, id, chain) =>
      `__clay.get(${toRef(id)}, ${JSON.stringify(pathKeys(chain))})`,
  );
const clayCellRef = (cell, col) => {
  if (!cell || cell.status !== 'success') return undefined;
  // Formulas read an action/source column's structured `fields`; its `value` is only a display string
  // ("❌ No Record Found"), so a column without fields reads as empty.
  if (col && col.type !== 'basic') return cell.fields ?? undefined;
  return cell.value ?? undefined;
};

// ---------------------------------------------------------------- action mapping
// Each adapter turns Clay inputsBinding (name -> TS expression) into a Deepline tool input (param -> TS expression).
// `b.pick(...names)` returns the first bound expression; `b.prefixed('fields|')` returns {suffix: expr}.
const obj = (m) =>
  `{ ${Object.entries(m)
    .filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${JSON.stringify(k)}: ${v}`)
    .join(', ')} }`;
const compactObj = (m) => `__clay.compact(${obj(m)})`;
const EMAIL_VERIFY = {
  tool: 'bounceban_verify_single',
  input: (b) => ({ email: b.pick('email') }),
};
const WORK_EMAIL = {
  tool: 'datagma_find_email',
  note: 'Clay chains finders by runIf; consider one prebuilt/name-and-domain-to-email-waterfall call instead.',
  input: (b) => ({
    full_name: b.pick('full_name', 'fullname', 'name'),
    company_domain: b.pick(
      'company_domain',
      'domain',
      'website',
      'company_url',
    ),
    company_name: b.pick('company_name', 'company'),
  }),
};
const PERSON_ENRICH = {
  tool: 'crustdata_v3_person_enrich',
  input: (b) => ({
    professional_network_profile_urls: b.list(
      'person_identifier',
      'socialMediaProfile',
      'linkedin_url',
      'profile_url',
    ),
    business_emails: b.list('email'),
  }),
};
const LINKEDIN_FIND = {
  tool: 'limadata_find_person_profiles',
  input: (b) => ({
    full_name: b.pick('full_name', 'name') ?? "''",
    email: b.pick('email', 'email_address', 'work_email', 'personal_email'),
    company_domain: b.pick('company_domain', 'domain'),
    company_name: b.pick('company_name', 'company'),
  }),
};
const EMAIL_TO_LINKEDIN = {
  tool: 'leadmagic_email_to_profile',
  input: (b) => ({
    email: b.pick('email', 'work_email'),
    personal_email: b.pick('personalEmail', 'personal_email'),
  }),
};
const MOBILE = {
  tool: 'leadmagic_mobile_finder',
  input: (b) => ({
    profile_url: b.pick(
      'profile_url',
      'linkedin_url',
      'personal_linkedin_url',
      'search_input',
      'linkedin_profile_url',
    ),
    email: b.pick('email'),
  }),
};
const DOMAIN_FIND = {
  tool: 'akta_company_search',
  input: (b) => ({ query: b.pick('companyName', 'company_name', 'query') }),
};
const NAME = (b) => b.pick('full_name', 'fullname', 'name');
const DOMAIN = (b) =>
  b.pick('company_domain', 'domain', 'website', 'company_url');
const WORK_EMAIL_POOL = [
  WORK_EMAIL,
  {
    tool: 'leadmagic_email_finder',
    input: (b) => ({
      first_name: `__clay.firstName(${NAME(b)})`,
      last_name: `__clay.lastName(${NAME(b)})`,
      domain: DOMAIN(b),
      company_name: b.pick('company_name', 'company'),
    }),
  },
  {
    tool: 'prospeo_enrich_person',
    input: (b) => ({
      full_name: NAME(b),
      company_domain: DOMAIN(b),
      company_name: b.pick('company_name', 'company'),
    }),
  },
  {
    tool: 'hunter_email_finder',
    input: (b) => ({
      full_name: NAME(b),
      domain: DOMAIN(b),
      company: b.pick('company_name', 'company'),
    }),
  },
  {
    tool: 'icypeas_email_search',
    input: (b) => ({
      firstname: `__clay.firstName(${NAME(b)})`,
      lastname: `__clay.lastName(${NAME(b)})`,
      domainOrCompany: DOMAIN(b) ?? "''",
      wait_for_completion: 'true',
      max_wait_ms: '120000',
    }),
  },
  {
    tool: 'findymail_find_from_name',
    input: (b) => ({ name: NAME(b) ?? "''", domain: DOMAIN(b) ?? "''" }),
  },
  // Finders no Clay table here used: they keep a waterfall of missing vendors on distinct providers.
  {
    tool: 'limadata_find_work_email',
    input: (b) => ({
      full_name: NAME(b) ?? "''",
      company_domain: DOMAIN(b) ?? "''",
    }),
  },
  {
    tool: 'trykitt_find_email',
    input: (b) => ({ fullName: NAME(b) ?? "''", domain: DOMAIN(b) ?? "''" }),
  },
  {
    tool: 'quickenrich_employee_email_enrich',
    input: (b) => ({
      first_name: `__clay.firstName(${NAME(b)})`,
      last_name: `__clay.lastName(${NAME(b)})`,
      company_url: DOMAIN(b),
      linkedin_url: b.pick('linkedin_url'),
    }),
  },
];
const PERSON_POOL = [
  PERSON_ENRICH,
  {
    tool: 'peopledatalabs_enrich_contact',
    input: (b) => ({
      email: b.pick('email'),
      name: b.pick('fullname', 'name'),
      profile: b.pick('person_identifier', 'linkedin_url'),
    }),
  },
  {
    tool: 'aviato_person_enrich',
    input: (b) => ({
      email: b.pick('email'),
      linkedinURL: b.pick('person_identifier', 'linkedin_url'),
    }),
  },
  {
    tool: 'contactout_enrich_person',
    input: (b) => ({
      email: b.pick('email'),
      linkedin_url: b.pick('person_identifier', 'linkedin_url'),
      full_name: b.pick('fullname', 'name'),
    }),
  },
];
const LINKEDIN_POOL = [
  LINKEDIN_FIND,
  {
    tool: 'peopledatalabs_enrich_contact',
    input: (b) => ({
      name: b.pick('full_name', 'name'),
      email: b.pick('email', 'email_address'),
      company: b.pick('company_domain', 'domain', 'company_name', 'company'),
    }),
  },
  {
    tool: 'datagma_enrich_person',
    input: (b) => ({
      fullName: b.pick('full_name', 'name'),
      email: b.pick('email', 'email_address'),
      domain: b.pick('company_domain', 'domain'),
      companyName: b.pick('company_name', 'company'),
    }),
  },
];
const DOMAIN_POOL = [
  DOMAIN_FIND,
  {
    tool: 'peopledatalabs_enrich_company',
    input: (b) => ({ name: b.pick('companyName', 'company_name', 'query') }),
  },
  {
    tool: 'crustdata_v3_company_enrich',
    input: (b) => ({ names: b.list('companyName', 'company_name', 'query') }),
  },
];
const CO_SITE = (b) => b.pick('company_identifier', 'website', 'domain');
const COMPANY_POOL = [
  {
    tool: 'prospeo_enrich_company',
    input: (b) => ({
      company_website: CO_SITE(b),
      company_linkedin_url: b.pick('linkedin'),
      company_name: b.pick('companyName'),
    }),
  },
  {
    tool: 'peopledatalabs_enrich_company',
    input: (b) => ({ domain: CO_SITE(b), name: b.pick('companyName') }),
  },
  {
    tool: 'crustdata_v3_company_enrich',
    input: (b) => ({
      domains: b.list('company_identifier', 'website', 'domain'),
    }),
  },
  {
    tool: 'aviato_company_enrich',
    input: (b) => ({ website: CO_SITE(b), linkedinURL: b.pick('linkedin') }),
  },
];
const SF_FIELDS = (b, std) => {
  const f = b.prefixed('object_fields|');
  const top = {};
  for (const [clayKey, param] of Object.entries(std))
    if (f[clayKey] !== undefined) {
      top[param] = f[clayKey];
      delete f[clayKey];
    }
  return { ...top, fields: Object.keys(f).length ? compactObj(f) : undefined };
};
const SF_STD = {
  Email: 'email',
  FirstName: 'first_name',
  LastName: 'last_name',
  Title: 'title',
  Phone: 'phone',
};
// Same vendor first: a Clay step on Findymail stays on Findymail, so the user's waterfall keeps its order and vendors.
// A vendor Deepline does not carry gets a substitute; the report marks it `substitute` with the original vendor.
const WIZA = (level) => ({
  tool: 'wiza_reveal_person',
  input: (b) => ({
    full_name: b.pick('full_name'),
    company_domain: b.pick('domain'),
    company_name: b.pick('company'),
    profile_url: b.pick('profile_url'),
    email: b.pick('email'),
    enrichment_level: JSON.stringify(level),
  }),
});
const BY_DOMAIN = (b) =>
  b.pick('company_domain', 'domain', 'company_identifier');
const DEALROOM_ID = {
  tool: 'dealroom_search_companies',
  input: (b) => ({
    keyword: BY_DOMAIN(b),
    keyword_type: "'website_domain'",
    limit: '1',
    fields: "'id,name'",
  }),
  required: ['keyword'],
};
// An empty domain leaves `query` empty, so hasRequired skips the call.
const CRUNCHBASE_ID = {
  tool: 'crunchbase_search_organizations',
  input: (b) => ({
    field_ids: "['identifier']",
    query: `__clay.list(${BY_DOMAIN(b) ?? 'undefined'}).map((d) => ({ type: 'predicate', field_id: 'website_url', operator_id: 'domain_eq', values: [d] }))`,
    limit: '1',
  }),
};
const ACTIONS = {
  'findymail-find-work-email': {
    tool: 'findymail_find_from_name',
    input: (b) => ({
      name: b.pick('full_name') ?? "''",
      domain: b.pick('company_domain') ?? "''",
    }),
  },
  'findymail-validate-email': {
    tool: 'findymail_verify_email',
    input: (b) => ({ email: b.pick('email') }),
  },
  'validate-email': {
    tool: 'zerobounce_validate',
    input: (b) => ({ email: b.pick('email') }),
  },
  'find-email-v2': {
    tool: 'hunter_email_finder',
    input: (b) => ({
      full_name: b.pick('full_name'),
      domain: b.pick('domain'),
    }),
  },
  'prospeo-find-work-email-v2': {
    tool: 'prospeo_enrich_person',
    input: (b) => ({
      full_name: b.pick('full_name'),
      company_domain: b.pick('company_domain'),
    }),
  },
  'prospeo-find-mobile-number': {
    tool: 'prospeo_enrich_person',
    input: (b) => ({
      linkedin_url: b.pick('personal_linkedin_url'),
      enrich_mobile: 'true',
    }),
  },
  'datagma-find-work-email-v3': WORK_EMAIL,
  'datagma-enrich-person': {
    tool: 'datagma_enrich_person',
    input: (b) => ({ linkedin: b.pick('data'), fullName: b.pick('fullName') }),
  },
  'datagma-find-social-profile': {
    tool: 'datagma_enrich_person',
    input: (b) => ({
      fullName: b.pick('full_name'),
      email: b.pick('email'),
      domain: b.pick('company_domain'),
    }),
  },
  'leadmagic-find-work-email': {
    tool: 'leadmagic_email_finder',
    input: (b) => ({
      first_name: `__clay.firstName(${b.pick('name')})`,
      last_name: `__clay.lastName(${b.pick('name')})`,
      domain: b.pick('domain'),
    }),
  },
  'icypeas-find-email-v2': {
    tool: 'icypeas_email_search',
    input: (b) => ({
      firstname: `__clay.firstName(${b.pick('fullname')})`,
      lastname: `__clay.lastName(${b.pick('fullname')})`,
      domainOrCompany: b.pick('domain') ?? "''",
      wait_for_completion: 'true',
      max_wait_ms: '120000',
    }),
  },
  'wiza-find-email': WIZA('partial'),
  'wiza-find-work-email': WIZA('partial'),
  'wiza-find-linkedin-profile': WIZA('none'),
  'wiza-find-phone': WIZA('phone'),
  'fullenrich-find-work-email': {
    tool: 'fullenrich_bulk_enrich',
    input: (b) => ({
      name: "'clay-migration'",
      data: `[__clay.compact({ first_name: __clay.firstName(${b.pick('full_name')}), last_name: __clay.lastName(${b.pick('full_name')}), domain: ${b.pick('domain') ?? 'undefined'}, company_name: ${b.pick('company_name') ?? 'undefined'}, linkedin_url: ${b.pick('linkedin_url') ?? 'undefined'}, enrich_fields: ['contact.emails'] })]`,
      wait_for_completion: 'true',
    }),
  },
  'enrich-person': {
    tool: 'peopledatalabs_enrich_contact',
    input: (b) => ({
      email: b.pick('email'),
      name: b.pick('name'),
      company: b.pick('companyName'),
      profile: b.pick('socialMediaProfile'),
    }),
  },
  'contactout-social-url-from-email': {
    tool: 'contactout_enrich_person',
    input: (b) => ({ email: b.pick('personalEmail') }),
  },
  'aviato-find-personal-linkedin': {
    tool: 'aviato_person_enrich',
    input: (b) => ({ email: b.pick('email') }),
  },
  'forager-find-phone-numbers': {
    tool: 'forager_person_contacts_lookup_phone_numbers',
    input: (b) => ({
      linkedin_public_identifier: `__clay.linkedinSlug(${b.pick('linkedin_url')})`,
    }),
  },
  'upcell-find-mobile-number': {
    tool: 'upcell_enrich_contact',
    input: (b) => ({
      linkedinUrl: b.pick('profile_url'),
      fields: "['mobile']",
    }),
  },
  // Substitutes: Clay vendor not in Deepline. `alts` is an ordered pool: compile takes the first tool this table does
  // not already call with the same input, so a waterfall of N missing vendors still tries N different providers.
  'enrichley-verify-email': {
    alts: [
      EMAIL_VERIFY,
      { tool: 'zerobounce_validate', input: EMAIL_VERIFY.input },
      { tool: 'findymail_verify_email', input: EMAIL_VERIFY.input },
    ],
  },
  'clearout-validate-phone': {
    tool: 'ipqs_phone_validate',
    input: (b) => ({ phone: b.pick('number', 'phone') }),
  },
  ...Object.fromEntries(
    [
      'smarte-find-work-email',
      'enrow-find-work-email',
      'dropcontact-find-work-email',
      'dropcontact-enrich-person',
    ].map((k) => [k, { alts: WORK_EMAIL_POOL }]),
  ),
  ...Object.fromEntries(
    [
      'enrich-person-with-mixrank-v2',
      'enrich-person-and-company',
      'snov-enrich-person-by-email',
      'mixrank-enrich-email-address',
      'bytemine-enrich-person',
    ].map((k) => [k, { alts: PERSON_POOL }]),
  ),
  ...Object.fromEntries(
    [
      'enrich-company-with-mixrank-v2',
      'enrich-company',
      'hg-insights-enrich-company',
    ].map((k) => [k, { alts: COMPANY_POOL }]),
  ),
  'pdl-enrich-company-v3': {
    tool: 'peopledatalabs_enrich_company',
    input: (b) => ({ domain: b.pick('website'), name: b.pick('name') }),
  },
  // Dealroom and Crunchbase look up by their own entity id: `resolve` finds it by domain, then the tool runs on it
  // (its input reads `id`). Both run on the customer's own key.
  'dealroom-get-fundraising-data': {
    resolve: DEALROOM_ID,
    tool: 'dealroom_get_company_by_id',
    input: () => ({
      id: 'id',
      fields:
        "'id,name,total_funding,total_funding_currency,last_funding,last_funding_date,fundings'",
    }),
  },
  'dealroom-get-company-valuation': {
    resolve: DEALROOM_ID,
    tool: 'dealroom_get_company_fundings',
    input: () => ({ id: 'id' }),
    note: 'Valuation is on each Dealroom funding round (items[].valuation).',
  },
  'crunchbase-enrich-company-financials': {
    resolve: CRUNCHBASE_ID,
    tool: 'crunchbase_get_organization',
    input: () => ({
      entity_id: 'id',
      field_ids: JSON.stringify([
        'identifier',
        'funding_total',
        'equity_funding_total',
        'last_funding_total',
        'last_funding_type',
        'last_funding_at',
        'num_funding_rounds',
        'funding_stage',
        'valuation',
        'valuation_date',
      ]),
    }),
  },
  ...Object.fromEntries(
    ['harmonic-get-fundraising-data'].map((k) => [
      k,
      {
        alts: [
          {
            tool: 'leadmagic_company_funding',
            input: (b) => ({
              company_domain: b.pick(
                'company_domain',
                'domain',
                'company_identifier',
              ),
            }),
          },
          {
            tool: 'aviato_get_company_funds',
            input: (b) => ({
              website: b.pick('company_domain', 'domain', 'company_identifier'),
              page: '0',
              perPage: '25',
            }),
          },
        ],
      },
    ]),
  ),
  'predict-leads-get-job-openings-for-company-v3': {
    tool: 'predictleads_company_job_openings',
    input: (b) => ({ company_id_or_domain: b.pick('unparsedDomain') }),
    note: 'Clay jobTitleFilter is applied by a follow-up filter, not an input.',
  },
  'hg-insights-get-company-tech-stack': {
    tool: 'buyercaddy_list_company_products',
    input: (b) => ({ companyDomain: b.pick('company_identifier') }),
  },
  'linkedin-find-post-audience': {
    tool: 'harvestapi_get_post_reactions',
    input: (b) => ({ post: b.pick('urn') }),
  },
  'find-lists-of-people-with-mixrank': {
    tool: 'harvestapi_search_leads',
    input: (b) => ({
      currentCompanies: b.pick('company_identifier'),
      currentJobTitles: b.pick('job_title_keywords'),
    }),
  },
  ...Object.fromEntries(
    [
      'champify-find-linkedin-profile',
      'reverse-contact-find-linkedin-profile',
      'livedata-find-linkedin-profile',
    ].map((k) => [k, { alts: LINKEDIN_POOL }]),
  ),
  'leadmagic-find-linkedin-profile': EMAIL_TO_LINKEDIN,
  // Clay's Google action is a Google search; Deepline runs the same search through Serper (`out` shapes the result).
  'google-company-to-domain': {
    tool: 'serper_google_search',
    input: (b) => ({
      query: b.pick('query', 'companyName', 'company_name'),
      num: '1',
    }),
    out: 'searchDomain',
    note: 'Google search via Serper; domain = first organic result host.',
  },
  ...Object.fromEntries(
    [
      'get-domain-from-company-name',
      'hg-insights-find-domain-from-company-name',
    ].map((k) => [k, { alts: DOMAIN_POOL }]),
  ),
  'leadmagic-find-mobile-number': MOBILE,
  ...Object.fromEntries(
    ['lyne-find-mobile-number', 'zeliq-find-phone'].map((k) => [
      k,
      {
        alts: [
          MOBILE,
          {
            tool: 'prospeo_enrich_person',
            input: (b) => ({
              linkedin_url: MOBILE.input(b).profile_url,
              enrich_mobile: 'true',
            }),
          },
        ],
      },
    ]),
  ),
  'contactout-find-phone': {
    tool: 'contactout_linkedin_contact_info',
    input: (b) => ({
      profile: b.pick('linkedin_url') ?? "''",
      include_phone: 'true',
    }),
  },
  'hubspot-lookup-object': {
    tool: 'hubspot_search_objects',
    input: (b) => {
      const f = b.prefixed('fields|');
      delete f.fieldsToFilterBy;
      delete f.searchOperator;
      const filters = Object.entries(f).map(
        ([prop, v]) =>
          `{ propertyName: ${JSON.stringify(prop)}, operator: 'EQ', value: ${v} }`,
      );
      return {
        object_type: `__clay.hubspotType(${b.pick('objectTypeId')})`,
        filter_groups: `[{ filters: [${filters.join(', ')}].filter((f) => f.value !== undefined && f.value !== '') }]`,
        limit: b.pick('limit') && `Number(${b.pick('limit')})`,
      };
    },
  },
  'hubspot-update-object': {
    tool: 'hubspot_update_object',
    input: (b) => ({
      object_type: `__clay.hubspotType(${b.pick('objectTypeId')})`,
      object_id: `String(${b.pick('objectId')})`,
      properties: compactObj(b.prefixed('fields|')),
    }),
  },
  'hubspot-create-object': {
    tool: 'hubspot_create_object',
    input: (b) => ({
      object_type: `__clay.hubspotType(${b.pick('objectTypeId')})`,
      properties: compactObj(b.prefixed('fields|')),
    }),
  },
  'salesforce-lookup-record-v2': {
    tool: 'salesforce_query',
    input: (b) => ({
      soql: `__clay.soql(${b.pick('object_type')}, ${obj(b.prefixed('dynamicFields|searchFor|'))}, ${b.pick('dynamicFields|object_fields') ?? 'undefined'})`,
    }),
  },
  'salesforce-lookup-via-soql': {
    tool: 'salesforce_query',
    input: (b) => ({ soql: b.pick('soql_query') }),
  },
  'update-object': {
    tool: (b) =>
      /lead/i.test(b.raw('object_type'))
        ? 'salesforce_update_lead'
        : /account/i.test(b.raw('object_type'))
          ? 'salesforce_update_account'
          : 'salesforce_update_contact',
    input: (b) => ({
      id: `String(${b.pick('recordId')})`,
      ...SF_FIELDS(
        b,
        /account/i.test(b.raw('object_type'))
          ? { Name: 'name', Website: 'website', Description: 'description' }
          : SF_STD,
      ),
    }),
  },
  'create-object': {
    tool: (b) =>
      /lead/i.test(b.raw('object_type'))
        ? 'salesforce_create_lead'
        : /account/i.test(b.raw('object_type'))
          ? 'salesforce_create_account'
          : 'salesforce_create_contact',
    input: (b) => {
      const m = SF_FIELDS(
        b,
        /lead|contact/i.test(b.raw('object_type'))
          ? SF_STD
          : { Name: 'name', Website: 'website' },
      );
      if (/lead/i.test(b.raw('object_type'))) m.company_name ??= "'Unknown'";
      if (/lead|contact/i.test(b.raw('object_type'))) m.last_name ??= "''";
      return m;
    },
  },
  'heyreach-add-lead-to-campaign': {
    tool: 'heyreach_add_to_campaign',
    input: (b) => ({
      campaign_id: `String(${b.pick('campaignId')})`,
      contacts: `[{ first_name: String(${b.pick('firstName') ?? "''"}), last_name: String(${b.pick('lastName') ?? "''"}), linkedin_url: String(${b.pick('profileUrl') ?? "''"}), ...${compactObj({ email: b.pick('emailAddress'), company: b.pick('companyName'), custom_fields: b.pick('customUserFields') && `__clay.ref(${b.pick('customUserFields')})` })} }]`,
    }),
    note: 'Clay location/position have no HeyReach input; pass them in custom_fields if the sequence uses them.',
  },
  'http-api-v2': {
    tool: 'generic_http_request',
    input: (b) => ({
      method:
        b.pick('method') &&
        `/** @type {any} */ (String(${b.pick('method')}).toUpperCase())`,
      url: b.pick('url') ?? "''",
      body_json: b.pick('body') && `__clay.ref(${b.pick('body')})`,
      headers: b.pick('headers') && `__clay.ref(${b.pick('headers')})`,
      follow_redirects:
        b.pick('followRedirects') && `Boolean(${b.pick('followRedirects')})`,
    }),
  },
  'add-row-to-google-sheet': {
    tool: 'google_workspace_write_table',
    note: 'tab_name is not in the Clay binding; defaults to Sheet1.',
    input: (b) => {
      const m = b.prefixed('columnMapping|');
      const cols = Object.keys(m);
      const vals = `[${Object.values(m)
        .map((v) => `__clay.out(${v})`)
        .join(', ')}]`;
      return {
        spreadsheet_id: `String(${b.pick('id')})`,
        tab_name: "'Sheet1'",
        columns: JSON.stringify(cols),
        rows: `[${vals}]`,
        operation_key: `'clay-' + __clay.hash(${vals})`,
      };
    },
  },
};
// Clay-internal or local-only actions: compiled to plain TS, no tool call.
const LOCAL = {
  'normalize-url': (b) =>
    `((u) => { if (!u) return undefined; try { const x = new URL(/^https?:/i.test(u) ? u : 'https://' + u); return ${b.raw('type') && /domain/i.test(b.raw('type')) ? "x.hostname.replace(/^www\\./, '')" : "x.origin + x.pathname.replace(/\\/$/, '')"}; } catch { return u; } })(${b.pick('url') ?? 'undefined'})`,
  'get-keywords': (b) =>
    `((kw, text) => { const t = String(text ?? '').toLowerCase(); const found = String(kw ?? '').split(',').map((k) => k.trim()).filter((k) => k && t.includes(k.toLowerCase())); return { keywordsFound: found.join(','), count: found.length }; })(${b.pick('keyWords') ?? 'undefined'}, ${b.pick('textBody') ?? 'undefined'})`,
};
// Need a decision the config cannot make: emitted as a loud failure with the Clay settings attached.
const REVIEW = {
  'lookup-company-in-other-table':
    'Cross-table company lookup: load the company table export and join by record id.',
  'write-to-other-table-v2':
    'Cross-table write: return these values from this play and feed them to the target table play.',
  'route-row':
    'Row routing: return the routed rows and run the destination table play on them (or a child play call).',
  'trigger-find-people-source':
    'Source trigger: run the destination search play per company.',
  'google-docs-append-text-to-document-v2':
    'No Deepline Google Docs write tool; write to a Sheet or Notion instead.',
  'google-docs-create-document-v2':
    'No Deepline Google Docs write tool; write to a Sheet or Notion instead.',
  'lookup-add-or-update-row-in-google-sheet':
    'Sheet upsert: google_workspace_update_cells needs explicit A1 cell targets; read the sheet first.',
};
// Clay model names -> AI Gateway ids. Clay-hosted models (clay-argon, clay-neon) use the Deepline default.
const MODELS = {
  'claude-sonnet-4-6': 'anthropic/claude-sonnet-4.6',
  'claude-opus-4-6': 'anthropic/claude-opus-4.6',
  'claude-haiku-4-5': 'anthropic/claude-haiku-4.5',
  'gpt-5-mini': 'openai/gpt-5-mini',
  'gpt-5': 'openai/gpt-5',
  'gpt-4.1-mini': 'openai/gpt-4.1-mini',
  'gpt-4.1': 'openai/gpt-4.1',
  'gpt-4o-mini': 'openai/gpt-4o-mini',
  'gpt-4o': 'openai/gpt-4o',
};
function aiCallFor(b, raw) {
  const model = b.literal('model');
  const useCase = b.literal('useCase');
  const fields = raw.answerSchemaType?.formulaMap?.fields;
  let jsonSchema;
  if (fields) {
    try {
      const props = JSON.parse(JSON.parse(fields));
      jsonSchema = JSON.stringify({
        type: 'object',
        properties: props,
        required: Object.keys(props),
      });
    } catch {}
  }
  return {
    tool: 'deeplineagent',
    input: {
      prompt: b.pick('prompt') ?? "''",
      model: MODELS[model] && JSON.stringify(MODELS[model]),
      jsonSchema,
      maxToolCalls: useCase === 'claygent' ? undefined : '0',
    },
    note: `Clay ${useCase || 'use-ai'} on ${model || 'default model'}${MODELS[model] ? '' : ' (no gateway equivalent; Deepline default model)'}${useCase === 'claygent' ? '; web research via Deepline Agent tools' : '; tools disabled to match plain LLM'}.`,
  };
}

// Clay vendor behind an action: the connection type when the export resolved it, else the action key. Generic Clay
// action keys hide the vendor (find-email-v2 runs on Hunter).
const CLAY_VENDOR = {
  'find-email-v2': 'hunter',
  'validate-email': 'zero-bounce',
  'enrich-person': 'people-data-labs',
  'enrich-company': 'clearbit',
  'get-domain-from-company-name': 'clearbit',
  'enrich-person-and-company': 'clearbit',
  'pdl-enrich-company-v3': 'people-data-labs',
  'update-object': 'salesforce',
  'create-object': 'salesforce',
  'use-ai': 'ai',
  'http-api-v2': 'http-api',
  'add-row-to-google-sheet': 'google-sheets',
  'lookup-add-or-update-row-in-google-sheet': 'google-sheets',
  'linkedin-find-post-audience': 'linkedin',
  'find-lists-of-people-with-mixrank': 'mixrank',
  'enrich-person-with-mixrank-v2': 'mixrank',
  'enrich-company-with-mixrank-v2': 'mixrank',
  'google-company-to-domain': 'google',
};
const clayVendorOf = (key, acct) =>
  acct?.type ??
  CLAY_VENDOR[key] ??
  key.match(/^(hg-insights|predict-leads|reverse-contact|google-docs)/)?.[1] ??
  key.split('-')[0];
// Clay vendor -> Deepline provider when the names differ. AI models run on deeplineagent.
const SAME_VENDOR = {
  'people-data-labs': 'peopledatalabs',
  pdl: 'peopledatalabs',
  'zero-bounce': 'zerobounce',
  'predict-leads': 'predictleads',
  'google-sheets': 'google_workspace',
  'http-api': 'generic_http',
  anthropic: 'deeplineagent',
  openai: 'deeplineagent',
  'google-gemini': 'deeplineagent',
  ai: 'deeplineagent',
};
// Clay vendor whose capability Deepline runs on another provider: the same search, not a different data source.
const SAME_CAPABILITY = { google: 'serper' };
const sameVendor = (clayVendor, provider) =>
  (SAME_VENDOR[clayVendor] ?? clayVendor).replace(/[-_]/g, '') ===
  String(provider).replace(/[-_]/g, '');
// Key needed in Deepline, from `deepline describe`: required (no managed access), optional (managed by default), or managed.
const deeplineKeyOf = (schema) =>
  schema?.byok?.required
    ? 'required'
    : (schema?.features || []).some((f) => f.name === 'byok')
      ? 'optional'
      : 'managed';

// ---------------------------------------------------------------- compile
const snake = (s) =>
  String(s)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'col';
function describeTool(tool, cacheDir) {
  const p = `${cacheDir}/${tool}.json`;
  if (!fs.existsSync(p)) {
    let out = null;
    try {
      out = execFileSync('deepline', ['describe', tool, '--json'], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      });
    } catch {}
    writeJson(p, out ? JSON.parse(out) : { missing: true });
  }
  const d = readJson(p);
  return d.kind === 'tool' ? d : null;
}

const waterfallOf = (s) =>
  s?.formulaType === 'waterfall'
    ? (s.formulaWaterfall || []).map((w) =>
        typeof w === 'string' ? w : (w?.formula ?? ''),
      )
    : [];
// Every Clay expression a column evaluates: formula, waterfall steps, run condition, tool inputs.
const formulasOf = (s) => [
  s?.formulaText,
  s?.conditionalRunFormulaText,
  ...waterfallOf(s),
  ...(s?.inputsBinding || []).flatMap((i) => [
    i.formulaText,
    ...Object.values(i.formulaMap || {}),
  ]),
];

function compileTable(
  t,
  cols,
  toolSchema,
  columnsOf,
  { accounts = {}, providerOf = () => undefined } = {},
) {
  const byId = Object.fromEntries(cols.map((c) => [c.id, c]));
  // Unique aliases: a suffixed duplicate ("enrich_person_2") must not collide with a column named "Enrich person (2)".
  const alias = {};
  const taken = new Set();
  for (const c of cols) {
    const base = snake(c.name);
    let a = base;
    for (let n = 2; taken.has(a); n++) a = `${base}_${n}`;
    taken.add(a);
    alias[c.id] = a;
  }
  const rowRef = (id) =>
    !byId[id]
      ? 'undefined /* deleted Clay column */'
      : byId[id].type === 'action'
        ? `__clay.view(row[${JSON.stringify(alias[id])}])`
        : `row[${JSON.stringify(alias[id])}]`;
  const report = [];
  const steps = [];
  const seed = [];
  const lookups = new Set();
  const calls = {};
  const picked = new Set();
  const chosen = {};
  const norm = (v) => String(SAME_VENDOR[v] ?? v).replace(/[-_]/g, '');
  const tableVendors = new Set(
    cols
      .filter((c) => c.type === 'action')
      .map((c) =>
        norm(
          clayVendorOf(
            c.settings?.actionKey ?? '',
            accounts[c.settings?.authAccountId],
          ),
        ),
      ),
  );
  // Every Clay-authored expression goes to <play>.clay.js (plain JS, not typechecked as TS), keyed by column alias:
  // F = formula columns, IN = tool inputs, IF = run conditions. Parity imports the same module.
  const mod = { F: [], IN: [], IF: [] };
  const fnOf = (body) => `(row) => ${body}`;
  const expr = (formula) => {
    if (formula == null || !String(formula).trim()) return undefined;
    return parseable(translate(String(formula), rowRef)) ?? null;
  };
  // Dependency order: Clay column order, but every step after the steps it reads.
  const deps = (c) =>
    new Set(
      formulasOf(c.settings)
        .flatMap(refsOf)
        .filter((id) => id !== c.id && byId[id]),
    );
  const order = [];
  const state = {};
  const visit = (c) => {
    if (state[c.id]) return;
    state[c.id] = 1;
    for (const d of deps(c)) visit(byId[d]);
    order.push(c);
  };
  cols.forEach(visit);
  const fail = (a, msg) =>
    `      .withColumn(${JSON.stringify(a)}, () => { throw new Error(${JSON.stringify(msg)}); })`;

  for (const c of order) {
    const s = c.settings || {};
    const a = alias[c.id];
    const k = JSON.stringify(a);
    const rec = {
      table: t.name,
      tableId: t.id,
      column: c.name,
      columnId: c.id,
      alias: a,
      type: c.type,
    };
    const dangling = [
      ...new Set(
        formulasOf(s)
          .flatMap(refsOf)
          .filter((id) => !byId[id]),
      ),
    ];
    if (dangling.length) rec.danglingRefs = dangling;
    const wf = waterfallOf(s);
    if (
      c.type === 'source' ||
      (c.type === 'basic' && !s.formulaText && !wf.length)
    ) {
      seed.push(a);
      report.push({ ...rec, kind: 'seed', status: 'compiled' });
      continue;
    }
    if (c.type === 'basic' && wf.length) {
      // Clay waterfall: the first non-empty step, in the user's order. Each step reads a provider column whose own
      // runIf gate (compiled below) skips the call once an earlier step found a value.
      const es = wf.map(expr);
      if (es.some((e) => e == null)) {
        report.push({
          ...rec,
          kind: 'waterfall',
          status: 'needs_review',
          note: 'A waterfall step is not a parseable JS expression.',
        });
        steps.push(
          fail(a, `Clay waterfall ${c.name} needs manual translation`),
        );
        continue;
      }
      report.push({
        ...rec,
        kind: 'waterfall',
        status: dangling.length ? 'needs_review' : 'compiled',
        stepColumns: wf.map((f) =>
          refsOf(f).filter((id) => byId[id]?.type === 'action'),
        ),
      });
      mod.F.push(
        `  // ${c.name} (Clay waterfall, ${es.length} steps in configured order)\n  ${k}: ${fnOf(`__clay.out(__clay.waterfall(${es.map((e) => `() => ${e}`).join(', ')}), ${JSON.stringify(s.dataTypeSettings?.type ?? 'text')})`)},`,
      );
      steps.push(`      .withColumn(${k}, (row: any) => F[${k}](row))`);
      continue;
    }
    if (c.type === 'basic') {
      const e = expr(s.formulaText);
      if (e === null) {
        report.push({
          ...rec,
          kind: 'formula',
          status: 'needs_review',
          note: 'Formula is not a parseable JS expression.',
        });
        steps.push(
          `      // NEEDS REVIEW: unparseable Clay formula ${JSON.stringify(c.name)}\n${fail(a, `Clay formula for ${c.name} needs manual translation`)}`,
        );
        continue;
      }
      const readsAction = refsOf(s.formulaText).some(
        (id) => byId[id] && byId[id].type === 'action',
      );
      report.push({
        ...rec,
        kind: 'formula',
        status: dangling.length ? 'needs_review' : 'compiled',
        ...(readsAction && {
          note: 'Reads a provider output path; confirm the path on a pilot receipt.',
        }),
      });
      mod.F.push(
        `  // ${c.name}\n  ${k}: ${fnOf(`__clay.out(${e}, ${JSON.stringify(s.dataTypeSettings?.type ?? 'text')})`)},`,
      );
      steps.push(`      .withColumn(${k}, (row: any) => F[${k}](row))`);
      continue;
    }
    const key = s.actionKey;
    const raw = Object.fromEntries(
      (s.inputsBinding || []).map((i) => [i.name, i]),
    );
    const b = {
      pick: (...names) => {
        for (const n of names) {
          const e = expr(raw[n]?.formulaText);
          if (e) return e;
        }
        return undefined;
      },
      list: (...names) => {
        const es = names.map((n) => expr(raw[n]?.formulaText)).filter(Boolean);
        return es.length ? `__clay.list(${es.join(', ')})` : undefined;
      },
      prefixed: (p) =>
        Object.fromEntries(
          Object.keys(raw)
            .filter((n) => n.startsWith(p))
            .map((n) => [n.slice(p.length), expr(raw[n].formulaText)])
            .filter(([, v]) => v),
        ),
      raw: (n) => String(raw[n]?.formulaText ?? ''),
      literal: (n) => {
        try {
          return JSON.parse(raw[n]?.formulaText ?? 'null');
        } catch {
          return null;
        }
      },
    };
    const gate = s.conditionalRunFormulaText
      ? expr(s.conditionalRunFormulaText)
      : undefined;
    if (gate) mod.IF.push(`  ${k}: ${fnOf(`Boolean(${gate})`)},`);
    const runIf = gate ? `, { runIf: (row: any) => IF[${k}](row) }` : '';
    if (
      key === 'lookup-row-in-other-table' ||
      key === 'lookup-multiple-rows-in-other-table'
    ) {
      const target = b.literal('tableId');
      const targetCol = (columnsOf(target) || []).find(
        (x) => x.id === b.literal('fields|targetColumn'),
      );
      if (!targetCol) {
        report.push({
          ...rec,
          kind: 'action',
          actionKey: key,
          status: 'needs_review',
          note: `Lookup target ${target} column ${b.literal('fields|targetColumn')} is not in this export.`,
        });
        steps.push(
          fail(
            a,
            `Clay ${key} (${c.name}): target table ${target} was not exported`,
          ),
        );
        continue;
      }
      lookups.add(target);
      report.push({
        ...rec,
        kind: 'lookup',
        actionKey: key,
        status: 'compiled',
        lookupTable: target,
        lookupColumnUpdatedAt: targetCol.updatedAt,
        note: `Needs input.lookup_${target} = target table CSV with Clay column names.`,
      });
      mod.F.push(
        `  // ${c.name} (Clay ${key} on ${target} "${targetCol.name}")\n  ${k}: (row, lookups) => __clay.${key === 'lookup-row-in-other-table' ? 'lookup' : 'lookupMany'}(lookups[${JSON.stringify(target)}], ${JSON.stringify(targetCol.name)}, ${JSON.stringify(b.literal('fields|filterOperator') || 'EQUAL')}, ${b.pick('fields|rowValue') ?? 'undefined'}),`,
      );
      steps.push(
        `      .withColumn(${k}, (row: any) => F[${k}](row, lookups)${runIf})`,
      );
      continue;
    }
    if (LOCAL[key]) {
      report.push({
        ...rec,
        kind: 'local',
        actionKey: key,
        status: 'compiled',
      });
      mod.F.push(
        `  // ${c.name} (Clay ${key})\n  ${k}: ${fnOf(LOCAL[key](b))},`,
      );
      steps.push(`      .withColumn(${k}, (row: any) => F[${k}](row)${runIf})`);
      continue;
    }
    const acct = accounts[s.authAccountId];
    Object.assign(rec, {
      clayVendor: clayVendorOf(key, acct),
      clayKey: acct
        ? acct.isClayManaged
          ? 'clay_managed'
          : 'own'
        : s.authAccountId
          ? 'unknown'
          : 'none',
    });
    const def = ACTIONS[key];
    const specOf = (d) => ({
      tool: typeof d.tool === 'function' ? d.tool(b) : d.tool,
      input: d.input(b),
      note: d.note ?? def?.note,
      out: d.out,
      ...(d.resolve && {
        resolve: {
          tool: d.resolve.tool,
          input: d.resolve.input(b),
          required: d.resolve.required ?? [],
        },
      }),
    });
    const candidates =
      key === 'use-ai'
        ? [aiCallFor(b, raw)]
        : def
          ? (def.alts ?? [def]).map(specOf)
          : [];
    if (!candidates.length) {
      const why =
        REVIEW[key] ||
        `No Deepline mapping for Clay action ${key}: run \`deepline search "<input> -> <output>" --type tools\` and add it to ACTIONS.`;
      report.push({
        ...rec,
        kind: 'action',
        actionKey: key,
        status: REVIEW[key] ? 'needs_review' : 'unmapped',
        note: why,
        claySettings: Object.fromEntries(
          Object.entries(raw).map(([n, v]) => [
            n,
            v.formulaText ?? v.formulaMap,
          ]),
        ),
      });
      steps.push(
        `      // NEEDS REVIEW (${key}): ${why}\n${fail(a, `Clay ${key} (${c.name}) is not migrated yet: ${why}`)}`,
      );
      continue;
    }
    // Validate against the live tool schema: drop unknown params, flag missing required ones.
    const checkTool = (tool, given) => {
      const schema = toolSchema(tool);
      const issues = [];
      const input = {};
      if (!schema) issues.push(`tool ${tool} not found by deepline describe`);
      for (const [p, v] of Object.entries(given)) {
        if (v === undefined) continue;
        if (schema && !schema.inputs[p]) {
          issues.push(`dropped param ${p} (not in ${tool} schema)`);
          continue;
        }
        input[p] = v;
      }
      for (const [p, v] of Object.entries(schema?.inputs || {}))
        if (v.required && input[p] === undefined)
          issues.push(`missing required ${p}`);
      return {
        schema,
        issues,
        input,
        req: Object.entries(schema?.inputs || {})
          .filter(([, v]) => v.required)
          .map(([p]) => p),
      };
    };
    // A two-step spec (`resolve`) first finds the vendor's entity id, then calls the tool on it.
    const resolve = (spec) => {
      const main = checkTool(spec.tool, spec.input);
      const pre = spec.resolve && {
        ...spec.resolve,
        ...checkTool(spec.resolve.tool, spec.resolve.input),
      };
      return {
        ...spec,
        ...main,
        pre,
        issues: [...(pre?.issues || []), ...main.issues],
        sig: `${pre ? `${pre.tool} ${obj(pre.input)} -> ` : ''}${spec.tool} ${obj(main.input)}`,
      };
    };
    // A substitute pool takes the first provider this table does not already call with this input, so a waterfall
    // over vendors Deepline lacks still tries distinct providers. When every option is taken, reuse that column's
    // result instead of paying again for the same answer.
    const options = candidates.map(resolve);
    // Substitutes skip providers this table already runs as a Clay vendor, so they add a provider instead of taking one.
    // Preference: a provider new to this table, then one not run as a Clay vendor, then any unused call.
    const fresh = (o) =>
      !calls[o.sig] && !tableVendors.has(norm(providerOf(o.tool)));
    // One Clay vendor maps to one provider per table (every Enrichley validator becomes the same validator).
    const vendorKey = `${rec.clayVendor} ${key}`;
    const spec =
      options.length === 1
        ? options[0]
        : (options.find((o) => o.tool === chosen[vendorKey]) ??
          options.find((o) => fresh(o) && !picked.has(providerOf(o.tool))) ??
          options.find(fresh) ??
          options.find((o) => !calls[o.sig]) ??
          options[0]);
    if (options.length > 1) {
      picked.add(providerOf(spec.tool));
      chosen[vendorKey] ??= spec.tool;
    }
    const reuse = calls[spec.sig];
    const { schema, issues, input, pre } = spec;
    const provider = providerOf(spec.tool);
    const sameCapability = SAME_CAPABILITY[rec.clayVendor] === provider;
    report.push({
      ...rec,
      kind: 'action',
      actionKey: key,
      tool: spec.tool,
      ...(pre && { resolveTool: pre.tool }),
      provider,
      ...(sameCapability
        ? {
            sameCapability: `Clay runs this as a ${rec.clayVendor} search; Deepline runs the same search on ${provider}.`,
          }
        : !sameVendor(rec.clayVendor, provider) && {
            substitute: `Clay ran this on ${rec.clayVendor}; Deepline has no ${rec.clayVendor} tool, so it uses ${provider}.`,
          }),
      ...(reuse && { reuses: reuse.column }),
      deeplineKey: deeplineKeyOf(schema),
      ...(schema?.byok?.setupUrl && { setupUrl: schema.byok.setupUrl }),
      status: issues.length ? 'needs_review' : 'mapped',
      ...(spec.note && { note: spec.note }),
      ...(issues.length && { issues }),
    });
    const exec = (id, tool, inp, desc) =>
      `(await ctx.tools.execute({\n            staleAfterSeconds: 0,\n            id: ${id},\n            tool: ${JSON.stringify(tool)},\n            input: ${inp},\n            description: ${JSON.stringify(desc)},\n          })).toolResponse`;
    // Clay skips a column whose required input is empty; so does the play, instead of sending an invalid call.
    const req = spec.req;
    let body;
    let callIf;
    if (pre) {
      // Step 1 finds the id (gated by the Clay run condition and its own inputs); step 2 runs only when it found one.
      const kId = JSON.stringify(`${a}:id`);
      const preReq = [...new Set([...pre.req, ...pre.required])];
      mod.IN.push(
        `  // ${c.name} (Clay ${key} -> ${pre.tool}, then ${spec.tool})\n  ${kId}: ${fnOf(`/** @type {any} */ (${obj(pre.input)})`)},\n  ${k}: (row, found) => ((id) => /** @type {any} */ (${obj(input)}))(__clay.entityId(found)),`,
      );
      if (gate) mod.IF.pop();
      mod.IF.push(
        `  ${kId}: ${fnOf(`${gate ? `Boolean(${gate}) && ` : ''}__clay.hasRequired(IN[${kId}](row), ${JSON.stringify(preReq)})`)},\n  ${k}: (row, found) => __clay.hasRequired(IN[${k}](row, found), ${JSON.stringify(req)}),`,
      );
      const found = exec(
        kId,
        pre.tool,
        `IN[${kId}](row)`,
        `${c.name} (${providerOf(pre.tool)} id)`,
      );
      const call = exec(k, spec.tool, `IN[${k}](row, found)`, c.name);
      body = `{\n          ${reuse ? `if (row[${JSON.stringify(reuse.alias)}] != null) return row[${JSON.stringify(reuse.alias)}];\n          ` : ''}const found = ${found};\n          return IF[${k}](row, found) ? ${call} : undefined;\n        }`;
      callIf = `, { runIf: (row: any) => IF[${kId}](row) }`;
    } else {
      mod.IN.push(
        `  // ${c.name} (Clay ${key} -> ${spec.tool})\n  ${k}: ${fnOf(`/** @type {any} */ (${obj(input)})`)},`,
      );
      // `out` shapes the tool response into the Clay result (F holds it, beside the formulas).
      if (spec.out)
        mod.F.push(
          `  // ${c.name}: tool response -> Clay ${key} result\n  ${k}: (r) => __clay.${spec.out}(r),`,
        );
      const call = exec(k, spec.tool, `IN[${k}](row)`, c.name);
      const shaped = spec.out ? `F[${k}](${call})` : call;
      body = reuse
        ? `row[${JSON.stringify(reuse.alias)}] ??\n          ${shaped}`
        : shaped;
      if (req.length) {
        if (gate) mod.IF.pop();
        mod.IF.push(
          `  ${k}: ${fnOf(`${gate ? `Boolean(${gate}) && ` : ''}__clay.hasRequired(IN[${k}](row), ${JSON.stringify(req)})`)},`,
        );
      }
      callIf =
        gate || req.length ? `, { runIf: (row: any) => IF[${k}](row) }` : '';
    }
    steps.push(
      `      // Clay ${key}${spec.note ? `: ${spec.note}` : ''}${reuse ? ` (same call as ${JSON.stringify(reuse.column)}: reuses its result)` : ''}\n      .withColumn(\n        ${k},\n        async (row: any, ctx) =>\n          ${body}${callIf}\n      )`,
    );
    if (!reuse) calls[spec.sig] = { column: c.name, alias: a };
  }
  const recOf = Object.fromEntries(report.map((r) => [r.columnId, r]));
  for (const r of report.filter((x) => x.kind === 'waterfall')) {
    // A step returns its last-referenced provider column (`... ? ({{finder}} && {{finder}}?.email) : ''`); the
    // earlier references are the validators and previous steps it checks first.
    const call = (x) => ({
      column: x.column,
      clayAction: x.actionKey,
      clayVendor: x.clayVendor,
      clayKey: x.clayKey,
      tool: x.tool ?? null,
      provider: x.provider ?? null,
      sameVendor: x.tool ? !x.substitute && !x.sameCapability : false,
      ...(x.sameCapability && { sameCapability: true }),
      ...(x.reuses && { reuses: x.reuses }),
      gated: Boolean(byId[x.columnId]?.settings?.conditionalRunFormulaText),
      status: x.status,
    });
    r.steps = r.stepColumns.map((ids, i) => {
      const recs = [...new Set(ids)].map((id) => recOf[id]).filter(Boolean);
      const last = recOf[ids[ids.length - 1]];
      return {
        step: i + 1,
        ...(last && { returns: call(last) }),
        calls: recs.map(call),
      };
    });
    delete r.stepColumns;
    const seen = {};
    for (const st of r.steps)
      if (st.returns?.provider && !st.returns.reuses)
        seen[st.returns.provider] = (seen[st.returns.provider] || 0) + 1;
    const repeated = Object.keys(seen).filter((p) => seen[p] > 1);
    if (repeated.length)
      r.note = `Deepline has fewer distinct providers than this Clay waterfall: ${repeated.join(', ')} serve more than one step (with different inputs).`;
  }
  const name = `clay-${snake(t.name).slice(0, 24)}-${t.id.slice(-6)}`;
  const body = (list) => hideSpecifiers(list.join('\n'));
  // @ts-nocheck: these are Clay's own JS formulas; `parity` verifies them against Clay cells instead of TypeScript.
  const js = `// @ts-nocheck
// Generated by clay-to-deepline.mjs: Clay-authored expressions for table ${t.id}. Verified by \`parity\`, not tsc.
import { __clay, moment, _, Clay } from './clay-runtime.js';

export const F = {
${body(mod.F)}
};
export const IN = {
${body(mod.IN)}
};
export const IF = {
${body(mod.IF)}
};
`;
  const src = `import { definePlay } from 'deepline';
import { F, IN, IF } from './${name}.clay.js';

// Generated by clay-to-deepline.mjs from Clay table ${t.id} (${JSON.stringify(t.name)}).
// Seed CSV columns (Clay inputs, one per basic/source column): ${seed.join(', ') || '(none)'}
export default definePlay(
  ${JSON.stringify(name)},
  async (ctx, input: { csv: string${[...lookups].map((id) => `; lookup_${id}: string`).join('')} }) => {
    const seed = await ctx.csv<Record<string, any>>(input.csv);${
      lookups.size
        ? `
    // Cross-table lookups: each target table as a CSV keyed by Clay column name, in creation order (Clay's CSV export).
    const lookups: Record<string, Record<string, any>[]> = {
${[...lookups].map((id) => `      ${JSON.stringify(id)}: await (await ctx.csv<Record<string, any>>(input.lookup_${id})).materialize(),`).join('\n')}
    };`
        : ''
    }
    const rows = await ctx
      .dataset('rows', seed)
${steps.join('\n') || '      // no computed columns'}
      .run({ description: ${JSON.stringify(`Clay table ${t.name}`)} });
    return { rows };
  },
  { compatibility: { authoringContract: 'explicit-freshness' }, description: ${JSON.stringify(`Migrated from Clay: ${t.name}`)} },
);
`;
  return { name, src, js, report, seed, alias };
}

function compileWorkspace() {
  const inv = readJson(`${dir}/inventory.json`);
  const cache = `${dir}/describe`;
  const schemas = {};
  const toolSchema = (tool) =>
    tool in schemas
      ? schemas[tool]
      : (schemas[tool] = describeTool(tool, cache));
  fs.mkdirSync(`${dir}/plays`, { recursive: true });
  fs.mkdirSync(`${dir}/seeds`, { recursive: true });
  fs.writeFileSync(
    `${dir}/plays/clay-runtime.js`,
    `// @ts-nocheck\n// Generated by clay-to-deepline.mjs: Clay formula semantics shared by every migrated play.\n${RUNTIME}`,
  );
  const accounts = fs.existsSync(`${dir}/app-accounts.json`)
    ? readJson(`${dir}/app-accounts.json`)
    : {};
  const providersPath = `${cache}/_providers.json`;
  if (!fs.existsSync(providersPath))
    writeJson(
      providersPath,
      JSON.parse(
        execFileSync('deepline', ['providers', 'list', '--json'], {
          encoding: 'utf8',
        }),
      ).providers.map((p) => p.provider),
    );
  const providers = readJson(providersPath).sort((x, y) => y.length - x.length);
  const providerOf = (tool) =>
    providers.find(
      (p) => tool.startsWith(`${p.replace(/-/g, '_')}_`) || tool === p,
    ) ?? tool.split('_')[0];
  const all = [];
  const tables = [];
  for (const t of inv.tables) {
    const cols = readJson(`${dir}/columns/${t.id}.json`).data;
    const columnsOf = (id) =>
      fs.existsSync(`${dir}/columns/${id}.json`)
        ? readJson(`${dir}/columns/${id}.json`).data
        : null;
    const { name, src, js, report, seed, alias } = compileTable(
      t,
      cols,
      toolSchema,
      columnsOf,
      { accounts, providerOf },
    );
    fs.writeFileSync(`${dir}/plays/${name}.play.ts`, src);
    fs.writeFileSync(`${dir}/plays/${name}.clay.js`, js);
    // Seed CSV from the exported rows, so the play can be piloted on real Clay inputs.
    const rowDir = `${dir}/rows/${t.id}`;
    const rows = fs.existsSync(rowDir)
      ? fs.readdirSync(rowDir).map((f) => readJson(`${rowDir}/${f}`))
      : [];
    const seedIds = cols.filter((c) => seed.includes(alias[c.id]));
    const cell = (v) => {
      const s =
        v === undefined || v === null
          ? ''
          : typeof v === 'object'
            ? JSON.stringify(v)
            : String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [
      seedIds.map((c) => cell(alias[c.id])).join(','),
      ...rows.map((r) =>
        seedIds.map((c) => cell(clayCellRef(r.cells[c.id], c))).join(','),
      ),
    ];
    if (seedIds.length)
      fs.writeFileSync(`${dir}/seeds/${name}.csv`, lines.join('\n') + '\n');
    tables.push({
      table: t.name,
      tableId: t.id,
      play: `plays/${name}.play.ts`,
      module: `plays/${name}.clay.js`,
      seed: seedIds.length ? `seeds/${name}.csv` : null,
      seedRows: rows.length,
    });
    all.push(...report);
  }
  // Functions: `clay functions get` returns an XML schema, not column settings; inventory them for a reusable-play port.
  const functions = (inv.functions || []).map((f) => {
    const p = `${dir}/functions/${f.id}.json`;
    const s = fs.existsSync(p) ? readJson(p).schema || '' : '';
    const inputs = [
      ...new Set(
        [...s.matchAll(/\{\{Function inputs\}\}\?\.\["([^"\]]+)"\]/g)].map(
          (m) => m[1],
        ),
      ),
    ];
    const actions = [...s.matchAll(/<action name="([^"]+)"/g)].map((m) => m[1]);
    return {
      function: f.name,
      id: f.id,
      inputs,
      actions,
      status: 'needs_review',
      note: 'Port as a reusable play with input contract = inputs; actions are named by display name, map each with deepline search.',
    };
  });
  const count = (k) =>
    all.reduce((m, r) => ((m[r[k]] = (m[r[k]] || 0) + 1), m), {});
  const summary = {
    tables: tables.length,
    columns: all.length,
    byKind: count('kind'),
    byStatus: count('status'),
    functions: functions.length,
    workflows: (inv.workflows || []).length,
  };
  // Keys: one row per Deepline provider. `required` providers fail until connected; an `optional` provider runs on
  // Deepline-managed credits unless the user connects their own key (do so when they used their own key in Clay).
  const keys = {};
  for (const r of all.filter((x) => x.tool)) {
    const k = (keys[r.provider] ??= {
      provider: r.provider,
      deeplineKey: r.deeplineKey,
      setupUrl: r.setupUrl,
      clayVendors: new Set(),
      clayKeys: new Set(),
      columns: 0,
      tools: new Set(),
    });
    k.columns++;
    k.tools.add(r.tool);
    if (r.resolveTool) k.tools.add(r.resolveTool);
    k.clayVendors.add(r.clayVendor);
    // Only a same-vendor column can reuse the user's Clay key; a substitute or same-capability vendor needs its own decision.
    if (!r.substitute && !r.sameCapability) k.clayKeys.add(r.clayKey);
  }
  const keyRows = Object.values(keys)
    .map((k) => ({
      ...k,
      clayVendors: [...k.clayVendors],
      clayKeys: [...k.clayKeys],
      tools: [...k.tools],
      connect: `deepline tools connect ${k.provider}`,
      action:
        k.deeplineKey === 'required'
          ? 'connect (required: no Deepline-managed access)'
          : k.deeplineKey === 'optional' && k.clayKeys.has('own')
            ? 'connect your own key (you used one in Clay)'
            : k.deeplineKey === 'optional'
              ? 'optional: runs on Deepline credits until you connect a key'
              : 'none: Deepline-managed only',
    }))
    .sort((x, y) => x.action.localeCompare(y.action) || y.columns - x.columns);
  writeJson(`${dir}/keys.json`, keyRows);
  const waterfalls = all.filter((x) => x.kind === 'waterfall');
  summary.waterfalls = {
    columns: waterfalls.length,
    steps: waterfalls.reduce((n, w) => n + w.steps.length, 0),
    calls: 0,
    sameVendor: 0,
    sameCapability: 0,
    substitute: 0,
    reused: 0,
  };
  for (const c of new Map(
    waterfalls
      .flatMap((w) =>
        w.steps.flatMap((st) =>
          st.calls.map((c) => [`${w.tableId} ${c.column}`, c]),
        ),
      )
      .filter(([, c]) => c.tool),
  ).values()) {
    summary.waterfalls.calls++;
    summary.waterfalls[
      c.reuses
        ? 'reused'
        : c.sameVendor
          ? 'sameVendor'
          : c.sameCapability
            ? 'sameCapability'
            : 'substitute'
    ]++;
  }
  summary.keys = {
    required: keyRows
      .filter((k) => k.deeplineKey === 'required')
      .map((k) => k.provider),
    connectOwn: keyRows
      .filter((k) => k.action.startsWith('connect your own'))
      .map((k) => k.provider),
  };
  writeJson(`${dir}/migration-report.json`, {
    summary,
    tables,
    columns: all,
    functions,
  });
  console.log(JSON.stringify(summary));
}

// ---------------------------------------------------------------- sample (paid only when you run it)
// One column and everything it reads, as its own play plus an N-row seed: pilot a waterfall without the table's
// CRM writes or unrelated paid columns. `deepline plays run` it with --max-credits.
function sampleColumn() {
  const [tableId, column] = [opt('table'), opt('column')];
  const n = Number(opt('rows', '3'));
  if (!tableId || !column)
    throw new Error(
      'sample needs --table <tableId> --column "<Clay column name>"',
    );
  const inv = readJson(`${dir}/inventory.json`);
  const t = inv.tables.find((x) => x.id === tableId);
  const cols = readJson(`${dir}/columns/${tableId}.json`).data;
  const byId = Object.fromEntries(cols.map((c) => [c.id, c]));
  const target = cols.find((c) => c.name === column || c.id === column);
  if (!t || !target) throw new Error(`no column ${column} in table ${tableId}`);
  const keep = new Set();
  const visit = (c) => {
    if (!c || keep.has(c.id)) return;
    keep.add(c.id);
    formulasOf(c.settings)
      .flatMap(refsOf)
      .forEach((id) => visit(byId[id]));
  };
  visit(target);
  const sub = cols.filter((c) => keep.has(c.id));
  const cache = `${dir}/describe`;
  const schemas = {};
  const providers = readJson(`${cache}/_providers.json`).sort(
    (x, y) => y.length - x.length,
  );
  const providerOf = (tool) =>
    providers.find(
      (p) => tool.startsWith(`${p.replace(/-/g, '_')}_`) || tool === p,
    ) ?? tool.split('_')[0];
  const accounts = fs.existsSync(`${dir}/app-accounts.json`)
    ? readJson(`${dir}/app-accounts.json`)
    : {};
  const c = compileTable(
    t,
    sub,
    (tool) =>
      tool in schemas
        ? schemas[tool]
        : (schemas[tool] = describeTool(tool, cache)),
    () => null,
    { accounts, providerOf },
  );
  const { report: rep, seed, alias } = c;
  const name = `${c.name}-${snake(target.name).slice(0, 16)}-sample`;
  fs.writeFileSync(
    `${dir}/plays/${name}.play.ts`,
    c.src.replaceAll(c.name, name),
  );
  fs.writeFileSync(`${dir}/plays/${name}.clay.js`, c.js);
  // Seed rows are the exported Clay rows, so the sample runs on the same inputs parity used.
  const rowDir = `${dir}/rows/${tableId}`;
  const chosen = opt('row-ids')
    ? opt('row-ids').split(',')
    : fs
        .readdirSync(rowDir)
        .slice(0, n)
        .map((f) => f.replace(/\.json$/, ''));
  const seedCols = sub.filter((c) => seed.includes(alias[c.id]));
  const cell = (v) => {
    const x =
      v === undefined || v === null
        ? ''
        : typeof v === 'object'
          ? JSON.stringify(v)
          : String(v);
    return /[",\n\r]/.test(x) ? `"${x.replace(/"/g, '""')}"` : x;
  };
  const lines = [
    seedCols.map((c) => alias[c.id]).join(','),
    ...chosen.map((id) => {
      const r = readJson(`${rowDir}/${id}.json`);
      return seedCols.map((c) => cell(clayCellRef(r.cells[c.id], c))).join(',');
    }),
  ];
  fs.writeFileSync(`${dir}/seeds/${name}.csv`, lines.join('\n') + '\n');
  writeJson(`${dir}/samples/${name}.json`, {
    table: t.name,
    tableId,
    column: target.name,
    rows: chosen,
    play: `plays/${name}.play.ts`,
    seed: `seeds/${name}.csv`,
    columns: rep.map((x) => ({
      column: x.column,
      kind: x.kind,
      tool: x.tool,
      provider: x.provider,
      substitute: x.substitute,
      status: x.status,
    })),
  });
  console.log(
    JSON.stringify({
      play: `${dir}/plays/${name}.play.ts`,
      seed: `${dir}/seeds/${name}.csv`,
      rows: chosen.length,
      columns: rep.length,
      tools: rep.filter((x) => x.tool).map((x) => x.tool),
      run: `deepline plays run ${dir}/plays/${name}.play.ts --input '{"csv":"${dir}/seeds/${name}.csv"}' --max-credits <cap>`,
    }),
  );
}

// ---------------------------------------------------------------- parity (free, local)
// Imports the generated <play>.clay.js modules, so this tests the code the plays run. Run `compile` first.
async function parity() {
  const inv = readJson(`${dir}/inventory.json`);
  const report = readJson(`${dir}/migration-report.json`);
  const abs = (p) => 'file://' + path.resolve(dir, p);
  const { __clay: rt } = await import(abs('plays/clay-runtime.js'));
  const NOW = /moment\(\s*\)|new Date\(\s*\)|Date\.now\(/;
  const cellsCsv = ['table_id,row_id,column_id,column,verdict,expected,actual'];
  const columns = [];
  const csv = (v) => {
    const s = v === undefined || v === null ? '' : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  for (const t of inv.tables) {
    const cols = readJson(`${dir}/columns/${t.id}.json`).data;
    const byId = Object.fromEntries(cols.map((c) => [c.id, c]));
    const rowDir = `${dir}/rows/${t.id}`;
    const rows = fs.existsSync(rowDir)
      ? fs.readdirSync(rowDir).map((f) => readJson(`${rowDir}/${f}`))
      : [];
    const entry = report.tables.find((x) => x.tableId === t.id);
    const { F } = await import(abs(entry.module));
    const aliasOf = Object.fromEntries(
      report.columns
        .filter((x) => x.tableId === t.id)
        .map((x) => [x.columnId, x.alias]),
    );
    // A play row holds each column under its alias; build it from Clay's own cells so every formula is tested in isolation.
    const asRow = (r) =>
      Object.fromEntries(
        cols.map((x) => [aliasOf[x.id], clayCellRef(r.cells[x.id], x)]),
      );
    for (const c of cols) {
      const f = c.settings?.formulaText || waterfallOf(c.settings).join('\n');
      if (c.type !== 'basic' || !f) continue;
      const type = c.settings.dataTypeSettings?.type ?? 'text';
      const refs = refsOf(f);
      const dangling = refs.some((id) => !byId[id]);
      const fn = F[aliasOf[c.id]];
      const st = {
        table: t.name,
        tableId: t.id,
        column: c.name,
        columnId: c.id,
        timeDependent: NOW.test(f),
        rows: 0,
        match: 0,
        mismatch: 0,
        clay_not_evaluated: 0,
        clay_stale_input: 0,
        dangling_ref: 0,
        clay_error: 0,
        examples: [],
      };
      for (const r of rows) {
        const got = r.cells[c.id];
        if (
          got &&
          [
            'running',
            'queued',
            'retry',
            'rate_limited',
            'awaiting_callback',
          ].includes(got.status)
        )
          continue;
        st.rows++;
        let actual, err;
        try {
          actual = fn ? fn(asRow(r)) : null;
          if (!fn) err = 'not compiled';
        } catch (e) {
          err = e.message;
          actual = null;
        }
        const expected =
          got?.status === 'success' ? rt.out(got.value, type) : null;
        let verdict;
        if (dangling)
          verdict = 'dangling_ref'; // references a deleted Clay column: Clay kept an old value we cannot reproduce
        else if (!got || got.status === 'empty')
          verdict = actual === null ? 'match' : 'clay_not_evaluated'; // Clay never computed this cell
        else if (got.status === 'error')
          verdict = actual === null || err ? 'clay_error' : 'mismatch';
        // "now" formulas: same emptiness, value is evaluation time
        else if (st.timeDependent)
          verdict =
            (expected === null) === (actual === null) ? 'match' : 'mismatch';
        else if (expected === actual) verdict = 'match';
        else
          verdict = refs.some((id) => {
            const x = r.cells[id];
            return !x || x.status === 'empty' || x.isStale;
          })
            ? 'clay_stale_input'
            : 'mismatch'; // an input changed after Clay computed this cell
        st[verdict === 'match' ? 'match' : verdict]++;
        if (verdict !== 'match' && st.examples.length < 3)
          st.examples.push({
            rowId: r.id,
            verdict,
            expected,
            actual,
            ...(err && { err }),
          });
        cellsCsv.push(
          [t.id, r.id, c.id, c.name, verdict, expected, actual]
            .map(csv)
            .join(','),
        );
      }
      columns.push(st);
    }
  }
  // Cross-table lookups: rerun each lookup against the target table's sampled rows. A record Clay found that is not
  // in the sample cannot be checked (not_in_sample); everything else must match Clay exactly.
  const lookupStats = {
    cells: 0,
    match: 0,
    mismatch: 0,
    not_in_sample: 0,
    clay_stale: 0,
    target_changed_later: 0,
    examples: [],
  };
  const sampleOf = {};
  const asNamedRows = (tid) =>
    (sampleOf[tid] ??= (() => {
      const tcols = fs.existsSync(`${dir}/columns/${tid}.json`)
        ? readJson(`${dir}/columns/${tid}.json`).data
        : [];
      const rd = `${dir}/rows/${tid}`;
      // Clay returns the earliest-created match, so order the sample by Created At (export the CSV in that order too).
      return (fs.existsSync(rd) ? fs.readdirSync(rd) : [])
        .map((f) => {
          const cells = readJson(`${rd}/${f}`).cells;
          return Object.fromEntries(
            tcols.map((x) => [x.name, cells[x.id]?.value ?? null]),
          );
        })
        .sort((a, b) =>
          String(a['Created At'] ?? '').localeCompare(
            String(b['Created At'] ?? ''),
          ),
        );
    })());
  const same = (a, b) =>
    Object.keys(a).every((k) => String(a[k]) === String(b?.[k]));
  for (const col of report.columns.filter((x) => x.kind === 'lookup')) {
    const entry = report.tables.find((x) => x.tableId === col.tableId);
    const { F, IF } = await import(abs(entry.module));
    const cols = readJson(`${dir}/columns/${col.tableId}.json`).data;
    const aliasOf = Object.fromEntries(
      report.columns
        .filter((x) => x.tableId === col.tableId)
        .map((x) => [x.columnId, x.alias]),
    );
    const target = asNamedRows(col.lookupTable);
    const rd = `${dir}/rows/${col.tableId}`;
    for (const f of fs.existsSync(rd) ? fs.readdirSync(rd) : []) {
      const r = readJson(`${rd}/${f}`);
      const got = r.cells[col.columnId];
      if (!got || got.status !== 'success') continue;
      const clayRecs = got.fields?.record
        ? [got.fields.record]
        : got.fields?.records || [];
      const row = Object.fromEntries(
        cols.map((x) => [aliasOf[x.id], clayCellRef(r.cells[x.id], x)]),
      );
      const ran = !IF[col.alias] || IF[col.alias](row);
      const ours = ran
        ? F[col.alias](row, { [col.lookupTable]: target })
        : undefined;
      const ourRecs = ours?.record ? [ours.record] : ours?.records || [];
      let verdict;
      const srcCreated = String(r.cells.f_created_at?.value ?? '');
      if (clayRecs.some((R) => !target.some((t) => same(R, t))))
        verdict = 'not_in_sample';
      else if (
        clayRecs.length === ourRecs.length &&
        clayRecs.every((R, i) => same(R, ourRecs[i]))
      )
        verdict = 'match';
      else if (got.isStale)
        verdict = 'clay_stale'; // Clay marks this cell stale: an input changed after it ran
      // Clay does not re-run a lookup when the target table changes: the matching target row, or the target column
      // itself, is newer than this row.
      else if (
        !clayRecs.length &&
        srcCreated &&
        (String(col.lookupColumnUpdatedAt ?? '') > srcCreated ||
          ourRecs.every((t) => String(t['Created At'] ?? '') > srcCreated))
      )
        verdict = 'target_changed_later';
      else verdict = 'mismatch';
      lookupStats.cells++;
      lookupStats[verdict]++;
      if (verdict === 'mismatch' && lookupStats.examples.length < 20)
        lookupStats.examples.push({
          column: col.column,
          rowId: r.id,
          clay: clayRecs.length,
          ours: ourRecs.length,
        });
      cellsCsv.push(
        [
          col.tableId,
          r.id,
          col.columnId,
          col.column,
          `lookup_${verdict}`,
          clayRecs.length,
          ourRecs.length,
        ]
          .map(csv)
          .join(','),
      );
    }
  }
  fs.writeFileSync(`${dir}/parity-cells.csv`, cellsCsv.join('\n') + '\n');
  writeJson(`${dir}/parity-columns.json`, columns);
  const sum = (k) => columns.reduce((n, s) => n + s[k], 0);
  const tested = columns.filter((s) => s.rows);
  const summary = {
    formulaColumns: columns.length,
    columnsWithRows: tested.length,
    columnsAllMatch: tested.filter((s) => s.match === s.rows).length,
    cells: sum('rows'),
    match: sum('match'),
    mismatch: sum('mismatch'),
    clay_not_evaluated: sum('clay_not_evaluated'),
    clay_stale_input: sum('clay_stale_input'),
    dangling_ref: sum('dangling_ref'),
    clay_error: sum('clay_error'),
  };
  summary.parityOnEvaluatedCells = `${summary.match}/${summary.match + summary.mismatch}`;
  summary.lookups = lookupStats;
  console.log(JSON.stringify(summary));
  if (summary.mismatch || lookupStats.mismatch) process.exitCode = 1;
}

// ---------------------------------------------------------------- check (free)
async function checkAll() {
  const files = fs
    .readdirSync(`${dir}/plays`)
    .filter((f) => f.endsWith('.play.ts'));
  const results = await pool(files, 4, async (f) => {
    const r = await run('deepline', [
      'plays',
      'check',
      `${dir}/plays/${f}`,
      '--json',
    ]);
    let issues = [];
    try {
      const d = JSON.parse(r.out);
      issues = (d.issues || [])
        .filter((i) => i.severity === 'error')
        .map((i) => i.message);
      return { play: f, valid: d.valid === true, errors: issues };
    } catch {
      return { play: f, valid: false, errors: [(r.out + r.err).slice(0, 500)] };
    }
  });
  writeJson(`${dir}/check-results.json`, results);
  console.log(
    JSON.stringify({
      plays: results.length,
      valid: results.filter((r) => r.valid).length,
      invalid: results.filter((r) => !r.valid).length,
    }),
  );
}

// ---------------------------------------------------------------- selftest (no Clay or Deepline access)
// Each assertion is a Clay behavior observed on a real workspace's cells.
async function selftest() {
  const tmp = fs.mkdtempSync(
    path.join(process.env.TMPDIR || '/tmp', 'clay-selftest-'),
  );
  fs.writeFileSync(`${tmp}/clay-runtime.js`, RUNTIME);
  const { __clay: c } = await import('file://' + `${tmp}/clay-runtime.js`);
  const t = (formula, row) =>
    new Function(
      'row',
      '__clay',
      'moment',
      '_',
      'Clay',
      `return (${parseable(translate(formula, (id) => `row[${JSON.stringify(id)}]`))});`,
    )(row, c, c.moment, c._, c.Clay);
  const eq = (a, b, why) => {
    if (JSON.stringify(a) !== JSON.stringify(b))
      throw new Error(
        `${why}: got ${JSON.stringify(a)}, want ${JSON.stringify(b)}`,
      );
  };
  eq(
    c.out(t('"Job title: " + {{f_a}}?.title', {})),
    'Job title:',
    'missing path is empty, not "undefined"; output trimmed',
  );
  eq(
    c.out(t('{{f_a}}?.toLowerCase?.() || "none"', { f_a: 'X' })),
    'x',
    'method calls run on the resolved value',
  );
  eq(
    c.out(t('!{{f_a}} ? "Failed" : "Enriched"', {})),
    'Failed',
    'missing column is falsy',
  );
  eq(c.out(t('"a\nb"', {})), 'a\nb', 'raw newline in a Clay string literal');
  eq(c.out('-', 'url'), null, 'invalid url is empty');
  eq(c.out('a.com/x', 'url'), 'a.com/x', 'valid url kept');
  eq(c.out('x)@a.com', 'email'), null, 'invalid email is empty');
  eq(
    c.out('2026-05-21 23:51:18.911', 'date'),
    '2026-05-21T23:51:18.911Z',
    'naive date is UTC ISO',
  );
  eq(c.out('x'.repeat(9000)), null, 'over-long text is empty');
  eq(
    '{"P": "' + c.Clay.formatForJSON('say "hi"\n') + '"}',
    '{"P": "say \\"hi\\"\\n"}',
    'formatForJSON escapes inside quotes',
  );
  eq(
    c.moment('2026-01-31').diff(c.moment('2026-01-01'), 'days'),
    30,
    'moment diff days',
  );
  const table = [
    { Domain: 'acme.com', 'Created At': '1' },
    { Domain: 'acme.com/en', 'Created At': '2' },
  ];
  eq(
    c.lookup(table, 'Domain', 'CONTAIN', 'ACME.com'),
    { record: table[0] },
    'lookup: first match, case-insensitive',
  );
  eq(
    c.lookupMany(table, 'Domain', 'CONTAIN', 'acme')?.numberOfResults,
    2,
    'lookup many',
  );
  eq(
    hideSpecifiers('"data from "+x'),
    '"data fro\\u006d "+x',
    'bundler-safe string',
  );
  eq(
    c.waterfall(
      () => '',
      () => null,
      () => 'b@x.com',
      () => 'c@x.com',
    ),
    'b@x.com',
    'waterfall: first non-empty step',
  );
  eq(
    c.get(c.view({ raw: {}, rawV2: { contact: { email: 'a@x.com' } } }), [
      'email',
    ]),
    'a@x.com',
    'view: Clay field found inside a Deepline response',
  );
  eq(
    c.get(c.view({ email: null, data: { email: 'deep@x.com' } }), ['email']),
    '',
    'view: a field on the object wins, as in a Clay cell',
  );
  eq(
    c.get(c.view({ rawV2: { email: 'w@x.com' } }), ['data', 'email']),
    'w@x.com',
    'view: missing Clay wrapper passes through',
  );
  eq(
    c.get(
      c.view({
        rawV2: { person: { email: { email: null, status: 'UNAVAILABLE' } } },
      }),
      ['email'],
    ),
    '',
    'view: same-named nested field unwraps; null is empty',
  );
  eq(
    c.get(c.view({ rawV2: { email: 'g@x.com' } }), ['email', 0, 'email']),
    'g@x.com',
    'string satisfies a Clay list path',
  );
  eq(
    c.get(
      c.view({
        rawV2: {
          data: [
            {
              contact_info: {
                most_probable_work_email: {
                  email: 'm@x.com',
                  status: 'CATCH_ALL',
                },
              },
            },
          ],
        },
      }),
      ['most_probable_email'],
    ),
    'm@x.com',
    'renamed vendor field',
  );
  eq(
    c.hasRequired({ domain: '' }, ['domain']),
    false,
    'empty required input skips the call',
  );
  eq(
    c.searchDomain({
      rawV2: {
        organic: [
          { link: 'https://www.acme.com/about' },
          { link: 'https://x.com' },
        ],
      },
    }),
    { domain: 'acme.com', url: 'https://www.acme.com/about' },
    'Google company-to-domain: first organic host, no www',
  );
  eq(
    c.searchDomain({ raw: { organic: [] } }),
    undefined,
    'Google company-to-domain: no result is no record',
  );
  eq(
    [
      c.entityId({ raw: { entities: [{ uuid: 'u1' }] } }),
      c.entityId({ raw: { items: [{ id: 7 }] } }),
      c.entityId(undefined),
    ],
    ['u1', 7, undefined],
    'entity id from a Crunchbase or Dealroom search',
  );
  // Mapping: Google -> Serper (same capability), Crunchbase/Dealroom -> id lookup by domain, then the funding tool.
  const schema = (inputs, byok) => ({
    kind: 'tool',
    inputs: Object.fromEntries(
      Object.entries(inputs).map(([p, r]) => [p, { required: r }]),
    ),
    ...(byok && { byok: { required: true } }),
  });
  const S = {
    serper_google_search: schema({ query: true, num: false }),
    crunchbase_search_organizations: schema(
      { field_ids: true, query: true, limit: false },
      1,
    ),
    crunchbase_get_organization: schema(
      { entity_id: true, field_ids: false },
      1,
    ),
    dealroom_search_companies: schema(
      { keyword: false, keyword_type: false, limit: false, fields: false },
      1,
    ),
    dealroom_get_company_fundings: schema({ id: true }, 1),
  };
  const col = (id, name, actionKey, bind) => ({
    id,
    name,
    type: 'action',
    settings: {
      actionKey,
      inputsBinding: Object.entries(bind).map(([n, f]) => ({
        name: n,
        formulaText: f,
      })),
    },
  });
  const cols = [
    { id: 'f_n', name: 'Company', type: 'source' },
    { id: 'f_d', name: 'Domain', type: 'source' },
    col('f_g', 'Google domain', 'google-company-to-domain', {
      query: '{{f_n}}',
    }),
    col('f_c', 'Financials', 'crunchbase-enrich-company-financials', {
      company_domain: '{{f_d}}',
    }),
    col('f_v', 'Valuation', 'dealroom-get-company-valuation', {
      domain: '{{f_d}}',
    }),
  ];
  const ct = compileTable(
    { id: 't_selftest', name: 'selftest' },
    cols,
    (tool) => S[tool] ?? null,
    () => null,
    { providerOf: (tool) => tool.split('_')[0] },
  );
  const rep = Object.fromEntries(
    ct.report.filter((r) => r.tool).map((r) => [r.alias, r]),
  );
  eq(
    [
      rep.google_domain.tool,
      Boolean(rep.google_domain.sameCapability),
      rep.google_domain.substitute,
    ],
    ['serper_google_search', true, undefined],
    'Google company-to-domain runs on Serper, same capability',
  );
  eq(
    [
      rep.financials.resolveTool,
      rep.financials.tool,
      rep.financials.deeplineKey,
      rep.financials.substitute,
      rep.financials.status,
    ],
    [
      'crunchbase_search_organizations',
      'crunchbase_get_organization',
      'required',
      undefined,
      'mapped',
    ],
    'Crunchbase: id by domain, then organization, own key',
  );
  eq(
    [rep.valuation.resolveTool, rep.valuation.tool, rep.valuation.status],
    ['dealroom_search_companies', 'dealroom_get_company_fundings', 'mapped'],
    'Dealroom: id by domain, then fundings',
  );
  fs.writeFileSync(`${tmp}/${ct.name}.clay.js`, ct.js);
  const { F, IN, IF } = await import('file://' + `${tmp}/${ct.name}.clay.js`);
  eq(
    F.google_domain({ rawV2: { organic: [{ link: 'http://acme.io' }] } })
      ?.domain,
    'acme.io',
    'Serper response shaped into the Clay domain result',
  );
  eq(
    [
      IF['financials:id']({ domain: '' }),
      IF['financials:id']({ domain: 'acme.com' }),
      IF['valuation:id']({ domain: '' }),
    ],
    [false, true, false],
    'id lookup skipped without a domain',
  );
  eq(
    IN['financials:id']({ domain: 'acme.com' }).query,
    [
      {
        type: 'predicate',
        field_id: 'website_url',
        operator_id: 'domain_eq',
        values: ['acme.com'],
      },
    ],
    'Crunchbase search by website domain',
  );
  eq(
    [
      IF.financials({}, { raw: { entities: [] } }),
      IN.financials({}, { raw: { entities: [{ uuid: 'u1' }] } }).entity_id,
    ],
    [false, 'u1'],
    'funding call needs the found id',
  );
  eq(
    IN.valuation({}, { raw: { items: [{ id: 42 }] } }).id,
    42,
    'Dealroom fundings on the found id',
  );
  console.log('selftest ok');
}

const cmds = {
  export: exportWorkspace,
  compile: compileWorkspace,
  sample: sampleColumn,
  parity,
  check: checkAll,
  selftest,
};
if (!cmds[cmd] || (!dir && cmd !== 'selftest')) {
  console.error(
    'usage: clay-to-deepline.mjs <export|compile|parity|check> <dir> [--rows N] [--tables t_a,t_b] | selftest',
  );
  process.exit(2);
}
await cmds[cmd]();
