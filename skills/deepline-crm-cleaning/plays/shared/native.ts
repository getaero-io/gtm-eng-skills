/* eslint-disable @typescript-eslint/no-require-imports -- Static sandbox imports with narrow API types; the Play checker does not load ambient Node declarations. */
/** Pure Node 20 APIs available in the Play sandbox. No network or filesystem access. */
export interface Hash {
  update(value: string | Uint8Array): Hash;
  digest(encoding: 'hex'): string;
}
export interface ByteBuffer extends Uint8Array {
  toString(encoding?: 'base64' | 'hex' | 'utf8'): string;
}

const crypto: {
  createHash(algorithm: 'sha256'): Hash;
} = require('node:crypto');
const net: { isIP(value: string): 0 | 4 | 6 } = require('node:net');
const runtimeProcess: {
  versions: { unicode: string };
} = require('node:process');
const buffer: {
  Buffer: { from(value: string, encoding: 'base64'): ByteBuffer };
} = require('node:buffer');

export const createHash = crypto.createHash;
export const isIP = net.isIP;
export const Buffer = buffer.Buffer;
export const runtimeUnicodeVersion = runtimeProcess.versions.unicode;
