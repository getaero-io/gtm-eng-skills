/*
 * Clay Table Extractor — Bookmarklet (source)
 *
 * Run this on any Clay table view URL, e.g.
 *   https://app.clay.com/workspaces/1114258/tables/t_xxx/views/gv_xxx
 *
 * It uses the already-authenticated browser session (credentials: 'include',
 * so the claysession cookie is sent automatically) to pull, from Clay's
 * internal v3 API:
 *   - table config        GET  /v3/tables/{TABLE_ID}            (fields, typeSettings, prompts, action bindings)
 *   - schema + samples     GET  /v3/tables/{TABLE_ID}/views/{VIEW_ID}/table-schema-v2
 *   - all record ids       GET  /v3/tables/{TABLE_ID}/views/{VIEW_ID}/records/ids
 *   - full cell data       POST /v3/tables/{TABLE_ID}/bulk-fetch-records  (batched)
 *
 * Output: downloads a single JSON file shaped to match the clay-extract.py
 * extract the deepline clay-to-deepline skill expects:
 *   { _meta, table, fields, tableSchema, exampleRecords, recordIds, bulkFetchRecords }
 *
 * Two ways to run it:
 *   1. Human: minify to a `javascript:` URL (see clay-extract-bookmarklet.url.txt)
 *      and drag it to the bookmarks bar, then click it on a Clay table tab.
 *   2. Agent (Claude-in-Chrome): paste this IIFE body into `javascript_tool` on
 *      the table tab. It assigns the result to `window.__clayExtract`; read that
 *      (or return JSON.stringify) instead of relying on the file download.
 *
 * The cookie is NEVER read, logged, or written — only the browser uses it.
 */
(async () => {
  const API = 'https://api.clay.com';
  const MAX_RECORDS = 500; // cap full pull; raise if you need every row
  const BATCH = 50; // bulk-fetch page size

  const path = location.pathname;
  const tableId = (path.match(/\/tables\/(t_[A-Za-z0-9]+)/) || [])[1];
  let viewId = (path.match(/\/views\/(gv_[A-Za-z0-9]+)/) || [])[1];

  if (!tableId) {
    alert('Clay extract: no table id in URL. Open a /tables/t_... page first.');
    return;
  }

  const toast = (msg) => {
    let el = document.getElementById('__clay_extract_toast');
    if (!el) {
      el = document.createElement('div');
      el.id = '__clay_extract_toast';
      el.style.cssText =
        'position:fixed;z-index:2147483647;bottom:20px;right:20px;background:#111;color:#fff;' +
        'font:13px/1.4 -apple-system,system-ui,sans-serif;padding:10px 14px;border-radius:8px;' +
        'box-shadow:0 4px 16px rgba(0,0,0,.3);max-width:320px';
      document.body.appendChild(el);
    }
    el.textContent = 'Clay extract: ' + msg;
    return el;
  };

  const getJSON = async (url, opts) => {
    const r = await fetch(url, {
      credentials: 'include',
      headers: { accept: 'application/json, text/plain, */*', ...(opts && opts.headers) },
      ...opts,
    });
    if (!r.ok) throw new Error(url.replace(API, '') + ' → ' + r.status);
    return r.json();
  };

  try {
    toast('fetching table config…');
    const table = await getJSON(API + '/v3/tables/' + tableId);

    // Resolve view id from the table if it wasn't in the URL.
    viewId = viewId || table?.table?.firstViewId || table?.firstViewId;
    if (!viewId) throw new Error('could not resolve a view id (firstViewId missing)');

    // table-schema-v2 returns { tableSchema: { f_xxx: {...} }, exampleRecords: [ { f_xxx: <rendered value> } ] }
    // exampleRecords here carry RENDERED formula/action cell values (richest source) — capped by Clay (~2-66 rows).
    toast('fetching schema + sample records…');
    let schemaTree = null;
    let exampleRecords = [];
    try {
      const sv2 = await getJSON(
        API + '/v3/tables/' + tableId + '/views/' + viewId + '/table-schema-v2',
      );
      schemaTree = sv2?.tableSchema || sv2 || null;
      exampleRecords = sv2?.exampleRecords || sv2?.records || sv2?.sampleRecords || [];
    } catch (e) {
      console.warn('[clay-extract] table-schema-v2 failed:', e.message);
    }

    // True record count (no pagination on records/ids, but this confirms the cap).
    let totalRecordCount = null;
    try {
      const cnt = await getJSON(API + '/v3/tables/' + tableId + '/count');
      totalRecordCount = cnt?.tableTotalRecordsCount ?? cnt?.count ?? null;
    } catch (e) {
      console.warn('[clay-extract] count failed:', e.message);
    }

    toast('fetching record ids…');
    let recordIds = [];
    try {
      const ids = await getJSON(
        API + '/v3/tables/' + tableId + '/views/' + viewId + '/records/ids',
      );
      // Clay returns { results: [r_xxx, ...] }; tolerate older shapes too.
      recordIds = ids?.results || ids?.recordIds || ids?.ids || (Array.isArray(ids) ? ids : []);
    } catch (e) {
      console.warn('[clay-extract] records/ids failed:', e.message);
    }

    const truncated = recordIds.length > MAX_RECORDS;
    const idsToFetch = recordIds.slice(0, MAX_RECORDS);
    const bulkFetchRecords = [];
    for (let i = 0; i < idsToFetch.length; i += BATCH) {
      const chunk = idsToFetch.slice(i, i + BATCH);
      toast('records ' + (i + chunk.length) + '/' + idsToFetch.length + '…');
      try {
        const res = await getJSON(API + '/v3/tables/' + tableId + '/bulk-fetch-records', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ recordIds: chunk, includeExternalContentFieldIds: [] }),
        });
        if (res?.results) bulkFetchRecords.push(...res.results);
      } catch (e) {
        console.warn('[clay-extract] bulk-fetch batch failed:', e.message);
      }
    }

    if (truncated) {
      console.warn(
        '[clay-extract] record pull capped at MAX_RECORDS=' +
          MAX_RECORDS +
          ' of ' +
          recordIds.length +
          ' total. Raise MAX_RECORDS to pull all.',
      );
    }

    const extract = {
      _meta: {
        extractedAt: new Date().toISOString(),
        method: 'bookmarklet',
        tableId,
        viewId,
        url: location.href,
        totalRecordCount, // true table size from /count
        idCount: recordIds.length, // ids returned
        fetchedRecordCount: bulkFetchRecords.length, // rows pulled via bulk-fetch (may be sparse/unrun)
        exampleRecordCount: exampleRecords.length, // rendered sample rows from table-schema-v2 (richest)
        truncated, // true if MAX_RECORDS capped the pull
      },
      table: table?.table || table,
      fields: table?.fields || table?.table?.fields || [],
      // Schema tree keyed by field id (f_xxx → { type, name, children, ... }).
      tableSchema: schemaTree,
      // Rendered sample rows: flat { f_xxx: value } maps with formula/action outputs. Prefer these for prompts/samples.
      exampleRecords,
      recordIds,
      // Raw per-cell data for ALL records (cells are sparse — only populated fields appear).
      bulkFetchRecords,
    };

    const name =
      (extract.table?.name || tableId).replace(/[^A-Za-z0-9_-]+/g, '_').slice(0, 60);
    const blob = new Blob([JSON.stringify(extract, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'clay_extract_' + name + '.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);

    window.__clayExtract = extract; // also left on window for console inspection
    toast(
      'done: ' +
        (extract.fields?.length || 0) +
        ' fields, ' +
        exampleRecords.length +
        ' sample rows, ' +
        bulkFetchRecords.length +
        '/' +
        (totalRecordCount ?? recordIds.length) +
        ' records' +
        (truncated ? ' (CAPPED)' : '') +
        '. Downloaded JSON.',
    );
    setTimeout(() => document.getElementById('__clay_extract_toast')?.remove(), 6000);
  } catch (err) {
    console.error('[clay-extract]', err);
    toast('ERROR: ' + err.message + ' (see console)');
  }
})();
