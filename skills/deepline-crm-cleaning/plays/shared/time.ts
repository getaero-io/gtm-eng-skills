/** Receipt timestamps: microsecond precision; local and UTC years 1 through 9999. */
export function timestamp(value: unknown): bigint {
  if (typeof value !== 'string')
    throw new Error('timestamp with timezone required');
  const parts =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d\d:?\d\d)$/.exec(
      value,
    );
  if (!parts) throw new Error('invalid timestamp with timezone');
  const year = +parts[1],
    month = +parts[2],
    leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0),
    monthDays = [
      31,
      leapYear ? 29 : 28,
      31,
      30,
      31,
      30,
      31,
      31,
      30,
      31,
      30,
      31,
    ],
    zone = parts[8].replace(':', '');
  if (
    year === 0 ||
    month < 1 ||
    month > 12 ||
    +parts[3] < 1 ||
    +parts[3] > monthDays[month - 1] ||
    +parts[4] > 23 ||
    +parts[5] > 59 ||
    +parts[6] > 59 ||
    (zone !== 'Z' && (+zone.slice(1, 3) > 23 || +zone.slice(3) > 59))
  )
    throw new Error('invalid timestamp with timezone');
  const normalizedZone =
    zone === 'Z' ? 'Z' : `${zone.slice(0, 3)}:${zone.slice(3)}`;
  const ms = Date.parse(value.slice(0, -parts[8].length) + normalizedZone);
  const utcYear = new Date(ms).getUTCFullYear();
  if (!Number.isFinite(ms) || utcYear < 1 || utcYear > 9999)
    throw new Error('invalid timestamp: UTC year must be from 1 through 9999');
  return BigInt(ms) * 1000n + BigInt((parts[7] ?? '').padEnd(6, '0').slice(3));
}
export function normalized_timestamp(value: unknown): string {
  const micros = timestamp(value),
    seconds = micros >= 0n ? micros / 1000000n : (micros - 999999n) / 1000000n;
  const fraction = micros - seconds * 1000000n;
  return new Date(Number(seconds * 1000n))
    .toISOString()
    .replace(
      '.000Z',
      (fraction ? '.' + fraction.toString().padStart(6, '0') : '') + '+00:00',
    );
}
