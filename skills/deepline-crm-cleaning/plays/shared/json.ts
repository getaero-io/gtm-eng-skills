import { createHash } from './native';
import casefold from './unicode-casefold.json';

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Schema-validated dynamic CRM and receipt objects share this JSON boundary.
export type JsonObject = Record<string, any>;
export const HASH_FORMAT = 'crm-json-js-v1';

export function sha256(value: string | Uint8Array): string {
  return createHash('sha256').update(value).digest('hex');
}

export function compareCodepoints(a: string, b: string): number {
  const aa = Array.from(a, (c) => c.codePointAt(0)!);
  const bb = Array.from(b, (c) => c.codePointAt(0)!);
  for (let i = 0; i < Math.min(aa.length, bb.length); i++) {
    if (aa[i] !== bb[i]) return aa[i] - bb[i];
  }
  return aa.length - bb.length;
}

/** Versioned finite JSON encoding. Number spelling follows JavaScript JSON. */
export function canonicalJson(
  value: unknown,
  options: { ascii?: boolean } = {},
): string {
  const active = new Set<object>();
  function encode(item: unknown): string {
    if (item === null) return 'null';
    if (typeof item === 'string') {
      const result = JSON.stringify(item);
      return options.ascii
        ? result.replace(
            /[\u007f-\uffff]/g,
            (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'),
          )
        : result;
    }
    if (typeof item === 'number') {
      if (!Number.isFinite(item)) throw new Error('Non-finite JSON number');
      if (Number.isInteger(item) && !Number.isSafeInteger(item))
        throw new Error(
          'Unsafe JSON integer; encode exact identifiers as strings',
        );
      return JSON.stringify(item);
    }
    if (typeof item === 'boolean') return String(item);
    if (typeof item !== 'object') throw new Error('Expected a JSON value');
    if (active.has(item)) throw new Error('Cyclic JSON value');
    active.add(item);
    try {
      if (Array.isArray(item))
        return '[' + Array.from(item, encode).join(',') + ']';
      if (
        Object.getPrototypeOf(item) !== Object.prototype &&
        Object.getPrototypeOf(item) !== null
      ) {
        throw new Error('Expected a plain JSON object');
      }
      return (
        '{' +
        Object.keys(item)
          .sort(compareCodepoints)
          .map((key) => encode(key) + ':' + encode((item as JsonObject)[key]))
          .join(',') +
        '}'
      );
    } finally {
      active.delete(item);
    }
  }
  return encode(value);
}

/** Parse JSON without accepting duplicate keys or overflowing numbers. */
export function strictJsonParse(text: string): unknown {
  let offset = 0;
  const fail = (message: string): never => {
    throw new Error(`${message} at JSON offset ${offset}`);
  };
  const whitespace = () => {
    while (/[\t\n\r ]/.test(text[offset] ?? '\0')) offset++;
  };
  function string(): string {
    const start = offset++;
    while (offset < text.length) {
      const ch = text[offset++];
      if (ch === '"') return JSON.parse(text.slice(start, offset));
      if (ch === '\\') offset++;
    }
    return fail('Unterminated string');
  }
  function value(): unknown {
    whitespace();
    if (text[offset] === '"') return string();
    if (text[offset] === '{') {
      offset++;
      whitespace();
      const result: JsonObject = {};
      if (text[offset] === '}') {
        offset++;
        return result;
      }
      while (true) {
        whitespace();
        if (text[offset] !== '"') fail('Expected object key');
        const key = string();
        whitespace();
        if (Object.hasOwn(result, key)) fail(`Duplicate JSON key: ${key}`);
        if (text[offset++] !== ':') fail('Expected colon');
        Object.defineProperty(result, key, {
          value: value(),
          enumerable: true,
          writable: true,
          configurable: true,
        });
        whitespace();
        const next = text[offset++];
        if (next === '}') return result;
        if (next !== ',') fail('Expected comma');
      }
    }
    if (text[offset] === '[') {
      offset++;
      whitespace();
      const result: unknown[] = [];
      if (text[offset] === ']') {
        offset++;
        return result;
      }
      while (true) {
        result.push(value());
        whitespace();
        const next = text[offset++];
        if (next === ']') return result;
        if (next !== ',') fail('Expected comma');
      }
    }
    for (const [literal, result] of [
      ['true', true],
      ['false', false],
      ['null', null],
    ] as const) {
      if (text.startsWith(literal, offset)) {
        offset += literal.length;
        return result;
      }
    }
    const numeric = text
      .slice(offset)
      .match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
    if (!numeric) return fail('Expected JSON value');
    offset += numeric[0].length;
    const result = Number(numeric[0]);
    if (!Number.isFinite(result)) fail('Non-finite JSON number');
    if (Number.isInteger(result) && !Number.isSafeInteger(result))
      fail('Unsafe JSON integer; encode exact identifiers as strings');
    return result;
  }
  const result = value();
  whitespace();
  if (offset !== text.length) fail('Unexpected trailing input');
  return result;
}

/** Python 3 Unicode 16.0 full case folding, frozen independently of the host ICU. */
export function pythonCasefold(value: string): string {
  return Array.from(
    value,
    (char) => (casefold as Record<string, string>)[char] ?? char,
  ).join('');
}

/** Ratcliff/Obershelp matching with Python SequenceMatcher's stable tie order; no autojunk. */
export function sequenceMatcherRatio(left: string, right: string): number {
  const a = Array.from(left),
    b = Array.from(right);
  if (!a.length && !b.length) return 1;
  const positions = new Map<string, number[]>();
  b.forEach((char, index) => {
    const list = positions.get(char) ?? [];
    list.push(index);
    positions.set(char, list);
  });
  const pending = [[0, a.length, 0, b.length]];
  let matched = 0;
  while (pending.length) {
    const [alo, ahi, blo, bhi] = pending.pop()!;
    let bestA = alo,
      bestB = blo,
      bestSize = 0;
    let previous = new Map<number, number>();
    for (let i = alo; i < ahi; i++) {
      const current = new Map<number, number>();
      for (const j of positions.get(a[i]) ?? []) {
        if (j < blo) continue;
        if (j >= bhi) break;
        const size = (previous.get(j - 1) ?? 0) + 1;
        current.set(j, size);
        if (size > bestSize) {
          bestA = i - size + 1;
          bestB = j - size + 1;
          bestSize = size;
        }
      }
      previous = current;
    }
    if (!bestSize) continue;
    matched += bestSize;
    if (alo < bestA && blo < bestB) pending.push([alo, bestA, blo, bestB]);
    if (bestA + bestSize < ahi && bestB + bestSize < bhi)
      pending.push([bestA + bestSize, ahi, bestB + bestSize, bhi]);
  }
  return (2 * matched) / (a.length + b.length);
}
