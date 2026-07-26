// Two FieldPlugins for the route-fanout engine: work-email and validated-phone.
//
// The engine (./route-fanout-core.ts, createRouteFanoutEngine) owns all field-AGNOSTIC
// logic — RRF fusion, the diversity floor, the org-name guard, the tag
// vocabulary, row isolation, the ledger. A plugin owns only the field-SPECIFIC
// judgment: candidate shape, canonicalization, extraction, the identity gate
// (email → pure domain alignment; phone → a PAID trestle_real_contact call),
// the optional validator, verdict reading, and cell projection.
//
// COST MODEL. Email's identity gate is a pure, free domain-alignment check and
// its VALIDATOR (leadmagic) is the paid stage. Phone INVERTS this: its identity
// gate IS the paid call — trestle_real_contact returns name_match AND
// line-type/activity/validity in one shot, so it is both the identity gate and
// the validator. That is why phoneFieldPlugin exposes NO runValidator: the paid
// identityGate stashes its normalized verdict on the candidate, and readVerdict
// reads it back. This is the load-bearing generalization proof — the gate is a
// plugin method that can spend.
//
// Before writing a plugin for a NEW field, PROBE the validator/judge response
// shape with `deepline tools execute <ref> --input '{...}' --json`: provider
// verdict shapes differ. Trestle returns FLAT dotted keys (phone.is_valid,
// phone.linetype, phone.name_match, phone.activity_score) — a nested-only reader
// silently broke the first phone pilot. And keep isCandidateShaped STRICT (email
// regex / bounded phone digits+charset), never "≥7 digits anywhere".

import {
  canonicalizeDomain,
  canonicalizeEmail,
  canonicalizePhone,
  domainAligned,
  emailDomain,
  identityTokens,
  isParentDomainFill,
  normalizeEmailVerdict,
  passesIdentityGate,
  type FieldPlugin,
  type FieldProjection,
  type NormalizedVerdict,
  type PluginCandidate,
  type RowGuardingPlugin,
  type ValidationVerdict,
} from './route-fanout-core';

// ---------------------------------------------------------------------------
// Shared provider-shape adapters (pure).
// ---------------------------------------------------------------------------
function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function getExtracted(result: unknown, key: string): unknown {
  const wrapped = asRecord(result);
  const bag = asRecord(wrapped.extractedValues);
  const entry = bag[key] as { get?: () => unknown } | undefined;
  if (entry && typeof entry.get === 'function') {
    try {
      return entry.get();
    } catch {
      return null;
    }
  }
  return null;
}

function rawResponse(result: unknown): Record<string, unknown> {
  const wrapped = asRecord(result);
  return asRecord(asRecord(wrapped.toolResponse).raw ?? wrapped);
}

// ===========================================================================
// EMAIL — reproduces the 3-round-hardened work-email behavior EXACTLY.
// ===========================================================================
//
// Identity gate = the two-part gate the engine used to inline: name tokens must
// appear in the returned record (passesIdentityGate) AND the candidate email
// domain must align with the row domain / a declared alias (domainAligned).
// Validator = leadmagic_email_validation; only valid/catch_all ship. A
// parent-domain fill caps the tag at verify_next even on a valid verdict.

const EMAIL_VALIDATOR_REF = 'leadmagic_email_validation';

type EmailRow = {
  first_name?: string;
  last_name?: string;
  domain?: string;
  company_name?: string;
  domainAliases?: string[];
};

type EmailCand = PluginCandidate;

// Providers signal misses with sentinel strings ("undetermined", "not_found");
// only an email-shaped string is a candidate.
function isEmailShaped(value: unknown): boolean {
  return typeof value === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

// A prebuilt play returns { email, ... } as a scalar object (runPlay return).
function extractPlayEmail(result: unknown): EmailCand[] {
  const record = asRecord(result);
  const haystack = JSON.stringify(record);
  return isEmailShaped(record.email)
    ? [{ value: (record.email as string).trim(), haystack }]
    : [];
}

// A tool result exposes extractedValues + toolResponse.raw.
function extractToolEmail(result: unknown, getterKey: string): EmailCand[] {
  const extracted = getExtracted(result, getterKey);
  const raw = rawResponse(result);
  const haystack = JSON.stringify(raw);
  const values: string[] = [];
  if (isEmailShaped(extracted)) values.push((extracted as string).trim());
  const rawEmail = raw.email ?? asRecord(raw.data).email;
  if (isEmailShaped(rawEmail)) values.push((rawEmail as string).trim());
  return [...new Set(values)].map((value) => ({ value, haystack }));
}

// Recursively collect email-shaped strings from an aggregator response, in
// encounter order (rank 1 = first found). Over-collection is safe: every
// candidate still passes the domain-aligned identity gate before fusion.
function collectEmailsDeep(value: unknown, out: string[] = []): string[] {
  if (Array.isArray(value)) {
    for (const item of value) collectEmailsDeep(item, out);
    return out;
  }
  if (value && typeof value === 'object') {
    for (const child of Object.values(value as Record<string, unknown>)) {
      collectEmailsDeep(child, out);
    }
    return out;
  }
  if (isEmailShaped(value)) out.push((value as string).trim());
  return out;
}

function extractAggregatorEmails(result: unknown): EmailCand[] {
  const raw = rawResponse(result);
  const haystack = JSON.stringify(raw);
  return [...new Set(collectEmailsDeep(raw))].map((value) => ({ value, haystack }));
}

// Read the normalized email verdict off the validator's extractedValues, with a
// fallback to raw status fields. Mirrors the shipped readEmailVerdict exactly.
function readEmailVerdict(result: unknown): ValidationVerdict {
  const status = getExtracted(result, 'email_status');
  if (status && typeof status === 'object') {
    const rec = asRecord(status);
    if (rec.signals && asRecord(rec.signals).catch_all === true) return 'catch_all';
    if (typeof rec.status === 'string') return normalizeEmailVerdict(rec.status);
    if (typeof rec.verdict === 'string') {
      if (rec.verdict === 'verify_next') return 'catch_all';
      if (rec.verdict === 'drop' || rec.verdict === 'hold') return 'invalid';
      if (rec.verdict === 'send' || rec.verdict === 'send_with_caution') return 'valid';
    }
  }
  const raw = rawResponse(result);
  return normalizeEmailVerdict(
    raw.email_status ?? raw.status ?? asRecord(raw.data).email_status,
  );
}

// The extraction router: which extractor a route uses is declared per-route, so
// the plugin dispatches on a tag baked into the route's ref via a small map. The
// play passes the ref; the plugin recognizes the known email extraction shapes.
function extractEmailByRef(ref: string, result: unknown): EmailCand[] {
  if (ref.startsWith('prebuilt/')) return extractPlayEmail(result);
  if (ref === 'fullenrich_bulk_enrich') return extractAggregatorEmails(result);
  if (ref === 'zerobounce_email_finder') return extractToolEmail(result, 'email');
  // Unknown ref: best-effort deep collection keeps the plugin from silently
  // dropping a new route's candidates.
  return extractAggregatorEmails(result);
}

export const emailFieldPlugin: FieldPlugin<EmailCand> & RowGuardingPlugin = {
  id: 'email',

  isCandidateShaped: (raw) => isEmailShaped(raw),

  canonicalize: (raw) =>
    typeof raw === 'string' ? canonicalizeEmail(raw) : null,

  // A row with no employer domain cannot be identity-verified: a "found" email
  // would be unverifiable by construction. Skip before any route spends.
  rowGuard: (row) => {
    const seedDomain = canonicalizeDomain(String((row as EmailRow).domain ?? ''));
    return seedDomain ? null : 'missing_domain';
  },

  // The engine passes each route result through here per route; the plugin needs
  // to know WHICH route produced it. The engine tags the result object with the
  // route ref under `__ref` so the plugin can dispatch. (Set by the engine.)
  extractCandidates: (routeResult) => {
    const ref = String(asRecord(routeResult).__ref ?? '');
    return extractEmailByRef(ref, routeResult);
  },

  // Identity gate: pure, free. Name tokens must appear in the record haystack
  // AND the email domain must align with the row domain / a declared alias. A
  // same-name stranger at another company passes the token half and dies here.
  identityGate: async (cand, row) => {
    const emailRow = row as EmailRow;
    const seedDomain = canonicalizeDomain(String(emailRow.domain ?? ''));
    const tokens = identityTokens({
      firstName: emailRow.first_name,
      lastName: emailRow.last_name,
      domain: emailRow.domain,
      companyName: emailRow.company_name,
    });
    if (!passesIdentityGate(cand.haystack, tokens)) {
      return { ok: false };
    }
    const aliases = emailRow.domainAliases ?? [];
    if (!domainAligned(cand.value, seedDomain, aliases)) {
      return {
        ok: false,
        reason: `${cand.value.trim()}[${emailDomain(cand.value) ?? '?'}!=${seedDomain ?? '?'}]`,
      };
    }
    return { ok: true };
  },

  // Paid validator: leadmagic. Runs on the fused winner only (engine calls it
  // once per row). This is the paid stage for email.
  runValidator: async (cand, row, rowCtx) => {
    const emailRow = row as EmailRow;
    const ctx = rowCtx as {
      tools: {
        execute: (args: {
          id: string;
          tool: string;
          input: never;
          description: string;
        }) => Promise<unknown>;
      };
    };
    return ctx.tools.execute({
      id: 'validate_top',
      tool: EMAIL_VALIDATOR_REF,
      input: {
        email: cand.value,
        first_name: emailRow.first_name,
        last_name: emailRow.last_name,
      } as never,
      description: 'Validate the top fused work-email candidate.',
    });
  },

  readVerdict: (validatorResult): NormalizedVerdict => {
    const v = readEmailVerdict(validatorResult);
    if (v === 'valid') return { verdict: 'valid', ship: true };
    if (v === 'catch_all') return { verdict: 'catch_all', ship: true, tagCap: 'verify_next' };
    if (v === 'invalid') return { verdict: 'invalid', ship: false };
    return { verdict: 'unknown', ship: false };
  },

  // rerank.py blend, email terms: judge = validator verdict strength; signalA =
  // domain-alignment quality (exact-domain fill stronger than a parent fill);
  // signalB neutral (email has no engagement analog).
  scoreSignals: (cand, verdict, row) => {
    const judge =
      verdict?.verdict === 'valid'
        ? 95
        : verdict?.verdict === 'catch_all'
          ? 60
          : verdict?.verdict === 'invalid'
            ? 0
            : 20;
    const seedDomain = canonicalizeDomain(String((row as EmailRow).domain ?? ''));
    const signalA = isParentDomainFill(cand.value, seedDomain) ? 60 : 100;
    return { judge, signalA, signalB: 50 };
  },

  // Contact projection: read the winner (ranked[0]) and return a SCALAR cell.
  project: (ranked, verdict, row): FieldProjection => {
    const winning = ranked[0] ?? null;
    if (!winning || !verdict) return { value: null, miss_reason: 'no_candidates' };
    if (!verdict.ship) return { value: null, miss_reason: `verdict_${verdict.verdict}` };
    // A parent-domain fill (mailbox at the broad parent org, weaker than the
    // specific practice) keeps the email but is capped at verify_next upstream
    // via tagCap; recall untouched.
    const seedDomain = canonicalizeDomain(String((row as EmailRow).domain ?? ''));
    const parentFill = isParentDomainFill(winning.value, seedDomain);
    void parentFill; // tag capping handled by the engine via verdict.tagCap
    return { value: winning.value.trim(), miss_reason: null };
  },
};

// ===========================================================================
// PHONE — validated-mobile recovery. The identity gate IS the paid call.
// ===========================================================================
//
// trestle_real_contact returns name_match + contact_grade + line-type +
// activity in ONE call, so it is BOTH the identity gate AND the validator. The
// paid identityGate stashes its normalized verdict on the candidate; readVerdict
// reads it back. There is no runValidator. A wrong-number is dropped LOUD — it
// burns a rep's call and the account, worse than a miss.

const PHONE_JUDGE_REF = 'trestle_real_contact';

type PhoneRow = {
  first_name?: string;
  last_name?: string;
  domain?: string;
  linkedin_url?: string;
};

// Phone candidate carries a stash for the paid Trestle verdict, set by the
// identity gate and read by readVerdict + scoreSignals.
type PhoneCand = PluginCandidate & {
  _verdict?: NormalizedVerdict & {
    lineType?: string | null;
    activityScore?: number | null;
  };
};

// STRICT phone shape: 10-11 digits, phone charset only. Rejects UUIDs (hex +
// letters), LinkedIn URLs (slashes + letters), and long ids — the "≥7 digits
// anywhere" test was far too loose.
function isPhoneShaped(value: unknown): boolean {
  if (typeof value !== 'string') return false;
  const s = value.trim();
  const digits = s.replace(/\D/g, '');
  const phoneish = /^[+\d][\d\s().+-]{6,}$/.test(s);
  return phoneish && digits.length >= 10 && digits.length <= 11;
}

// person-to-phone returns { phone, phone_line_type, ... }.
function extractPlayPhone(result: unknown): PhoneCand[] {
  const record = asRecord(result);
  const haystack = JSON.stringify(record);
  return isPhoneShaped(record.phone)
    ? [{ value: (record.phone as string).trim(), haystack }]
    : [];
}

function collectPhonesDeep(value: unknown, out: string[] = []): string[] {
  if (Array.isArray(value)) {
    for (const item of value) collectPhonesDeep(item, out);
    return out;
  }
  if (value && typeof value === 'object') {
    for (const child of Object.values(value as Record<string, unknown>)) {
      collectPhonesDeep(child, out);
    }
    return out;
  }
  if (isPhoneShaped(value)) out.push((value as string).trim());
  return out;
}

function extractToolPhone(result: unknown): PhoneCand[] {
  const extracted = getExtracted(result, 'phone');
  const raw = rawResponse(result);
  const haystack = JSON.stringify(raw);
  const values: string[] = [];
  if (isPhoneShaped(extracted)) values.push((extracted as string).trim());
  for (const p of collectPhonesDeep(raw)) values.push(p);
  return [...new Set(values)].map((value) => ({ value, haystack }));
}

function extractPhoneByRef(ref: string, result: unknown): PhoneCand[] {
  if (ref.startsWith('prebuilt/')) return extractPlayPhone(result);
  return extractToolPhone(result);
}

// Read the Trestle Real Contact verdict off its FLAT dotted keys, with a nested
// fallback for defensiveness. name_match + validity + line-type + activity.
export function readPhoneVerdict(result: unknown): NormalizedVerdict & {
  lineType: string | null;
  activityScore: number | null;
} {
  const raw = rawResponse(result);
  const nested = asRecord(raw.phone ?? asRecord(raw.data).phone);
  const pick = (dotted: string, nestedKey: string): unknown =>
    raw[dotted] ?? nested[nestedKey];
  const isValid = pick('phone.is_valid', 'is_valid') === true;
  const lt = pick('phone.linetype', 'linetype') ?? pick('phone.line_type', 'line_type');
  const lineType = typeof lt === 'string' ? lt : null;
  const activityRaw = pick('phone.activity_score', 'activity_score');
  const activity = typeof activityRaw === 'number' ? activityRaw : null;
  const nameMatchRaw = pick('phone.name_match', 'name_match');
  const grade = String(pick('phone.contact_grade', 'contact_grade') ?? '')
    .trim()
    .toUpperCase();
  const nameMatch =
    nameMatchRaw === true ||
    String(nameMatchRaw ?? '').toLowerCase() === 'match' ||
    grade === 'A' ||
    grade === 'B';
  const nameNoMatch =
    nameMatchRaw === false ||
    String(nameMatchRaw ?? '').toLowerCase() === 'no_match';

  const dialable =
    lineType !== null &&
    /(mobile|cell|voip|wireless)/i.test(lineType);

  if (!isValid) return { verdict: 'invalid', ship: false, lineType, activityScore: activity };
  if (nameNoMatch) return { verdict: 'wrong_person', ship: false, lineType, activityScore: activity };
  const active = activity === null ? true : activity >= 30;
  if (nameMatch && active) {
    // Confirmed owner: ship. A landline still reaches the right desk but mobile
    // is the stronger dialable signal — cap a non-mobile at verify_next.
    return dialable
      ? { verdict: 'active_owner', ship: true, lineType, activityScore: activity }
      : { verdict: 'active_owner', ship: true, tagCap: 'verify_next', lineType, activityScore: activity };
  }
  // Valid line, identity unconfirmed: keep the number, name the risk.
  return { verdict: 'valid_unnamed', ship: true, tagCap: 'verify_next', lineType, activityScore: activity };
}

export const phoneFieldPlugin: FieldPlugin<PhoneCand> = {
  id: 'phone',

  isCandidateShaped: (raw) => isPhoneShaped(raw),

  canonicalize: (raw) =>
    typeof raw === 'string' ? canonicalizePhone(raw) : null,

  extractCandidates: (routeResult) => {
    const ref = String(asRecord(routeResult).__ref ?? '');
    return extractPhoneByRef(ref, routeResult);
  },

  // The identity gate IS the paid call. A pure name-token pre-check rejects a
  // finder that echoed a different person cheaply; when it passes, Trestle
  // confirms identity + validity + line-type in one paid shot, and the verdict
  // is stashed on the candidate for readVerdict.
  identityGate: async (cand, row, rowCtx) => {
    const phoneRow = row as PhoneRow;
    const tokens = identityTokens({
      firstName: phoneRow.first_name,
      lastName: phoneRow.last_name,
    });
    if (!passesIdentityGate(cand.haystack, tokens)) {
      return { ok: false };
    }
    const ctx = rowCtx as {
      tools: {
        execute: (args: {
          id: string;
          tool: string;
          input: never;
          description: string;
        }) => Promise<unknown>;
      };
    };
    try {
      const judge = await ctx.tools.execute({
        id: 'judge_identity',
        tool: PHONE_JUDGE_REF,
        input: {
          phone: cand.value,
          name: `${phoneRow.first_name ?? ''} ${phoneRow.last_name ?? ''}`.trim(),
        } as never,
        description: 'Identity + validity check on the phone candidate (Trestle).',
      });
      const verdict = readPhoneVerdict(judge);
      cand._verdict = verdict;
      // wrong_person / invalid fail the gate LOUD; anything shippable passes and
      // the stashed verdict decides tagging downstream.
      if (verdict.verdict === 'wrong_person') {
        return { ok: false, reason: `${cand.value}[wrong_person]` };
      }
      if (verdict.verdict === 'invalid') {
        return { ok: false, reason: `${cand.value}[invalid_line]` };
      }
      return { ok: true };
    } catch (error) {
      // A credential/provider failure on the paid gate leaves the candidate
      // unjudged: fail the gate so nothing unverified ships. Loud, not silent.
      cand._verdict = { verdict: 'unknown', ship: false };
      return {
        ok: false,
        reason: `${cand.value}[judge_error:${error instanceof Error ? error.message.slice(0, 40) : 'err'}]`,
      };
    }
  },

  // No runValidator: the paid identityGate already produced the verdict.

  readVerdict: (validatorResult): NormalizedVerdict => {
    // The engine passes the winning candidate here (runValidator absent). Read
    // the verdict the paid identity gate stashed on it.
    const cand = validatorResult as PhoneCand;
    return cand?._verdict ?? { verdict: 'unknown', ship: false };
  },

  // rerank.py blend, phone terms: judge = name_match × validity (active_owner
  // strongest); signalA = activity band (Trestle activity_score, when present);
  // signalB = line-type dialability (mobile/voip strongest, landline weaker).
  // Read from the verdict stashed on the candidate by the paid identity gate.
  scoreSignals: (cand, verdict) => {
    const stashed = (cand as PhoneCand)._verdict as
      | (NormalizedVerdict & { lineType?: string | null; activityScore?: number | null })
      | undefined;
    const v = verdict?.verdict ?? stashed?.verdict;
    const judge =
      v === 'active_owner' ? 95 : v === 'valid_unnamed' ? 50 : 0;
    const lineType = (stashed?.lineType ?? '').toLowerCase();
    const dialable = /(mobile|cell|voip|wireless)/.test(lineType);
    const signalB = dialable ? 100 : lineType ? 40 : 50;
    // Activity: Trestle activity_score is 0-100; clamp. Absent -> neutral 50.
    const activity =
      typeof stashed?.activityScore === 'number'
        ? Math.max(0, Math.min(100, stashed.activityScore))
        : 50;
    return { judge, signalA: activity, signalB };
  },

  project: (ranked, verdict): FieldProjection => {
    const winning = ranked[0] ?? null;
    if (!winning || !verdict) return { value: null, miss_reason: 'no_candidates' };
    if (!verdict.ship) return { value: null, miss_reason: `verdict_${verdict.verdict}` };
    return { value: winning.value.trim(), miss_reason: null };
  },
};
