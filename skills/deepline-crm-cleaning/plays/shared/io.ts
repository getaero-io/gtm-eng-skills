import { canonicalJson, strictJsonParse, type JsonObject } from './json';

export function objectJson(text: string, label: string): JsonObject {
  const value = strictJsonParse(text);
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label}: expected a JSON object`);
  }
  return value as JsonObject;
}

/** Dataset exports can feed another Play without flattening nested evidence. */
export async function* recordStream(
  dataset: AsyncIterable<{ record_json: string }>,
): AsyncGenerator<JsonObject> {
  let index = 0;
  for await (const row of dataset) {
    if (typeof row.record_json !== 'string')
      throw new Error(`CSV row ${index + 1}: record_json column required`);
    yield objectJson(row.record_json, `CSV row ${++index}`);
  }
}

export async function readRecords(
  dataset: AsyncIterable<{ record_json: string }>,
): Promise<JsonObject[]> {
  const rows: JsonObject[] = [];
  for await (const row of recordStream(dataset)) rows.push(row);
  return rows;
}

export async function readDocument(
  dataset: AsyncIterable<{ record_json: string }>,
): Promise<JsonObject> {
  let result: JsonObject | undefined;
  for await (const row of recordStream(dataset)) {
    if (result)
      throw new Error('Document CSV requires exactly one record_json row');
    result = row;
  }
  if (!result)
    throw new Error('Document CSV requires exactly one record_json row');
  return result;
}

export async function* recordRows(
  records: Iterable<unknown> | AsyncIterable<unknown>,
  runId: string,
) {
  if (typeof runId !== 'string' || !runId.trim())
    throw new Error('Output rows require a nonempty run ID');
  let index = 0;
  for await (const record of records) {
    yield { row_id: `${runId}:${index++}`, record_json: canonicalJson(record) };
  }
}
