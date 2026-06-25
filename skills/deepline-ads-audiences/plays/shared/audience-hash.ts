export type HashAudit = {
  inputRows: number;
  outputRows: number;
  malformedHashes: number;
  duplicateHashes: number;
  rawEmailFieldsPresent: boolean;
};

export type HashOnlyUploadRow = {
  email_sha256: string;
};

type HashInputRow = {
  email_sha256?: unknown;
  email?: unknown;
};

const SHA256_K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
  0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
  0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

declare const TextEncoder: {
  new (): { encode(value: string): ArrayLike<number> };
};

function rightRotate(value: number, shift: number): number {
  return (value >>> shift) | (value << (32 - shift));
}

function utf8Bytes(value: string): number[] {
  return Array.from(new TextEncoder().encode(value));
}

export function sha256Hex(value: string): string {
  const bytes = utf8Bytes(value);
  const bitLength = bytes.length * 8;
  bytes.push(0x80);
  while (bytes.length % 64 !== 56) bytes.push(0);
  for (let shift = 56; shift >= 0; shift -= 8) {
    bytes.push(Math.floor(bitLength / 2 ** shift) & 0xff);
  }

  let h0 = 0x6a09e667;
  let h1 = 0xbb67ae85;
  let h2 = 0x3c6ef372;
  let h3 = 0xa54ff53a;
  let h4 = 0x510e527f;
  let h5 = 0x9b05688c;
  let h6 = 0x1f83d9ab;
  let h7 = 0x5be0cd19;

  for (let offset = 0; offset < bytes.length; offset += 64) {
    const words = Array.from({ length: 64 }, () => 0);
    for (let index = 0; index < 16; index += 1) {
      const i = offset + index * 4;
      words[index] =
        ((bytes[i] ?? 0) << 24) |
        ((bytes[i + 1] ?? 0) << 16) |
        ((bytes[i + 2] ?? 0) << 8) |
        (bytes[i + 3] ?? 0);
    }
    for (let index = 16; index < 64; index += 1) {
      const s0 =
        rightRotate(words[index - 15]!, 7) ^
        rightRotate(words[index - 15]!, 18) ^
        (words[index - 15]! >>> 3);
      const s1 =
        rightRotate(words[index - 2]!, 17) ^
        rightRotate(words[index - 2]!, 19) ^
        (words[index - 2]! >>> 10);
      words[index] = (words[index - 16]! + s0 + words[index - 7]! + s1) >>> 0;
    }

    let a = h0;
    let b = h1;
    let c = h2;
    let d = h3;
    let e = h4;
    let f = h5;
    let g = h6;
    let h = h7;

    for (let index = 0; index < 64; index += 1) {
      const s1 = rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + s1 + ch + SHA256_K[index]! + words[index]!) >>> 0;
      const s0 = rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (s0 + maj) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }

    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
    h5 = (h5 + f) >>> 0;
    h6 = (h6 + g) >>> 0;
    h7 = (h7 + h) >>> 0;
  }

  return [h0, h1, h2, h3, h4, h5, h6, h7].map(wordHex).join('');
}

function wordHex(value: number): string {
  const alphabet = '0123456789abcdef';
  let output = '';
  for (let shift = 28; shift >= 0; shift -= 4) {
    output += alphabet[(value >>> shift) & 0xf];
  }
  return output;
}

export function normalizeEmail(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const normalized = value.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) return null;
  return normalized;
}

export function normalizeSha256(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const normalized = value.trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(normalized)) return null;
  return normalized;
}

export function auditHashRows(rows: HashInputRow[]): HashAudit {
  const hashes = rows
    .map((row) => normalizeSha256(row.email_sha256))
    .filter((hash): hash is string => Boolean(hash));
  return {
    inputRows: rows.length,
    outputRows: hashes.length,
    malformedHashes: rows.length - hashes.length,
    duplicateHashes: hashes.length - new Set(hashes).size,
    rawEmailFieldsPresent: rows.some((row) =>
      Object.prototype.hasOwnProperty.call(row, 'email'),
    ),
  };
}

export function prepareHashOnlyUploadRows(
  rows: HashInputRow[],
): { rows: HashOnlyUploadRow[]; audit: HashAudit } {
  const audit = auditHashRows(rows);
  const output: HashOnlyUploadRow[] = [];
  const seen = new Set<string>();

  for (const row of rows) {
    const hash = normalizeSha256(row.email_sha256);
    if (!hash || seen.has(hash)) continue;
    seen.add(hash);
    output.push({ email_sha256: hash });
  }

  return { rows: output, audit };
}
