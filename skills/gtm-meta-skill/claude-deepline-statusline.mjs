#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execSync } from 'node:child_process';

const MAX_TRANSCRIPT_BYTES = 1024 * 1024;
const MAX_RUNNING_SHOWN = 2;
const BACKEND_STATUS_TTL_MS = 15000;
const ACTIVE_PERSIST_MS = 45_000;
const STATE_PATH = path.join(os.homedir(), '.claude', 'deepline-statusline-state.json');

const SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
const BACKEND_PULSE = ['●', '◉'];

const C = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  white: '\x1b[97m',
  dim: '\x1b[37m',
  cyan: '\x1b[96m',
  green: '\x1b[92m',
  red: '\x1b[91m',
  yellow: '\x1b[93m',
};

const PROVIDER_LABELS = {
  apify: 'Apify',
  apollo: 'Apollo',
  crustdata: 'CrustData',
  deepline_native: 'Deepline Native',
  dropleads: 'DropLeads',
  exa: 'Exa',
  leadmagic: 'LeadMagic',
  hunter: 'Hunter',
  parallel: 'Parallel',
  peopledatalabs: 'People Data Labs',
  adyntel: 'Adyntel',
  google_search: 'Google Search',
  instantly: 'Instantly',
  lemlist: 'Lemlist',
  heyreach: 'HeyReach',
};

function ansi(text, color, useBold = false) {
  return `${useBold ? C.bold : ''}${color}${text}${C.reset}`;
}

function stripAnsi(text) {
  return text.replace(/\x1b\[[0-9;]*m/g, '');
}

function width() {
  const w = Number(process.stdout.columns || process.env.COLUMNS || 120);
  return Number.isFinite(w) && w > 20 ? w : 120;
}

function truncateText(text, maxLen) {
  if (maxLen <= 0) return '';
  if (text.length <= maxLen) return text;
  if (maxLen <= 3) return '.'.repeat(maxLen);
  return `${text.slice(0, maxLen - 3)}...`;
}

function joinInline(left, right) {
  const w = width();
  const leftRaw = stripAnsi(left);
  const sepRaw = ' | ';
  const leftLen = leftRaw.length;
  const sepLen = sepRaw.length;
  const availableRight = Math.max(16, w - leftLen - sepLen);
  const trimmedRight = truncateText(stripAnsi(right), availableRight);
  return `${left}${ansi(sepRaw, C.dim)}${ansi(trimmedRight, C.white, true)}`;
}

async function readStdin() {
  if (process.stdin.isTTY) return null;
  const chunks = [];
  process.stdin.setEncoding('utf8');
  try {
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    const text = chunks.join('').trim();
    return text.length ? text : null;
  } catch {
    return null;
  }
}

function parseJsonLine(line) {
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

function readTranscriptTail(transcriptPath, maxBytes = MAX_TRANSCRIPT_BYTES) {
  if (!transcriptPath) return [];
  try {
    const resolved = path.resolve(transcriptPath);
    const stat = fs.statSync(resolved);
    if (!stat.isFile()) return [];

    const start = Math.max(0, stat.size - maxBytes);
    const len = stat.size - start;
    const fd = fs.openSync(resolved, 'r');
    const buffer = Buffer.alloc(len);
    fs.readSync(fd, buffer, 0, len, start);
    fs.closeSync(fd);

    let text = buffer.toString('utf8');
    if (start > 0) {
      const firstNl = text.indexOf('\n');
      if (firstNl >= 0) text = text.slice(firstNl + 1);
    }

    return text
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map(parseJsonLine)
      .filter(Boolean);
  } catch {
    return [];
  }
}

function getToolUsesFromMessage(message) {
  const content = Array.isArray(message?.content) ? message.content : [];
  return content.filter((b) => b?.type === 'tool_use');
}

function getToolResultsFromMessage(message) {
  const content = Array.isArray(message?.content) ? message.content : [];
  return content.filter((b) => b?.type === 'tool_result');
}

function extractToolUseCommand(toolUse) {
  const input = toolUse?.input;
  if (!input || typeof input !== 'object') return '';
  if (typeof input.command === 'string') return input.command;
  if (typeof input.cmd === 'string') return input.cmd;
  return '';
}

function extractToolUseName(toolUse) {
  const name = toolUse?.name;
  return typeof name === 'string' ? name : '';
}

function extractThinkingText(lines) {
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const message = lines[i]?.message;
    const content = Array.isArray(message?.content) ? message.content : [];
    for (let j = content.length - 1; j >= 0; j -= 1) {
      const block = content[j];
      if (block?.type === 'text' && typeof block?.text === 'string') {
        const text = block.text.trim();
        if (text) return text;
      }
    }
  }
  return '';
}

function isDeeplineCommand(command) {
  return /(^|\s)(deepline|dl)(\s|$)/.test(command);
}

function isDeeplineToolUse(toolUse) {
  const name = String(toolUse?.name || '').toLowerCase();
  if (name.includes('deepline')) return true;
  const cmd = extractToolUseCommand(toolUse);
  return Boolean(cmd && isDeeplineCommand(cmd));
}

function classifyCommand(command) {
  if (!command) return 'running';
  if (/\b(deepline|dl)\s+enrich\b/.test(command)) return 'enrich';
  if (/\b(deepline|dl)\s+tools\s+get\b/.test(command)) return 'tools_get';
  if (/\b(deepline|dl)\s+tools\s+execute\b/.test(command)) return 'tools_execute';
  if (/\b(deepline|dl)\s+tools\s+(search|list)\b/.test(command)) return 'tools_search';
  if (/\b(deepline|dl)\s+csv\s+--execute_cells\b/.test(command)) return 'csv';
  return 'running';
}

function isTrackableMode(mode) {
  return mode === 'enrich' || mode === 'tools_get' || mode === 'tools_execute' || mode === 'tools_search' || mode === 'csv' || mode === 'running';
}

function shouldUseCachedBackendOnly(command) {
  if (!command) return false;
  return /\b(deepline|dl)\s+backend\b/.test(command) ||
    /\b(deepline|dl)\s+csv\s+render\b/.test(command) ||
    /\b(deepline|dl)\s+csv\s+--execute_cells\b/.test(command);
}

function parseRowCount(command) {
  const rows = command.match(/--rows\s+(\d+)\s*:\s*(\d+)/);
  if (rows) {
    const start = Number(rows[1]);
    const end = Number(rows[2]);
    if (Number.isFinite(start) && Number.isFinite(end) && end >= start) {
      return end - start + 1;
    }
  }
  const limit = command.match(/--limit\s+(\d+)/);
  if (limit) {
    const n = Number(limit[1]);
    if (Number.isFinite(n) && n > 0) return n;
  }
  return null;
}

function extractCsvPath(command) {
  const patterns = [
    /--input\s+("([^"]+)"|'([^']+)'|(\S+))/,
    /--csv\s+("([^"]+)"|'([^']+)'|(\S+))/,
    /--output\s+("([^"]+)"|'([^']+)'|(\S+))/,
  ];
  for (const p of patterns) {
    const m = command.match(p);
    if (m) return m[2] || m[3] || m[4] || '';
  }
  return '';
}

function extractExecutedTools(command) {
  const out = [];
  const execRe = /(?:deepline|dl)\s+tools\s+execute\s+([a-zA-Z0-9_:-]+)/g;
  let m = execRe.exec(command);
  while (m) {
    out.push(m[1]);
    m = execRe.exec(command);
  }
  const withRe = /=[\s"']*([a-zA-Z0-9_]+):\{/g;
  m = withRe.exec(command);
  while (m) {
    out.push(m[1]);
    m = withRe.exec(command);
  }
  return [...new Set(out)];
}

function extractToolsGetTarget(command) {
  const m = command.match(/(?:deepline|dl)\s+tools\s+get\s+([a-zA-Z0-9_:-]+)/);
  return m ? m[1] : '';
}

function extractPayloadPreview(command) {
  const idx = command.indexOf('--payload');
  if (idx < 0) return '';
  let raw = command.slice(idx + '--payload'.length).trim();
  if (!raw) return '';
  const nextFlag = raw.search(/\s--[a-zA-Z0-9_-]+/);
  if (nextFlag > 0) raw = raw.slice(0, nextFlag).trim();
  if ((raw.startsWith('"') && raw.endsWith('"')) || (raw.startsWith("'") && raw.endsWith("'"))) {
    raw = raw.slice(1, -1).trim();
  }
  return truncateText(raw.replace(/\s+/g, ' '), 18);
}

function extractPayloadQuery(command) {
  const idx = command.indexOf('--payload');
  if (idx < 0) return '';
  let raw = command.slice(idx + '--payload'.length).trim();
  if (!raw) return '';
  const nextFlag = raw.search(/\s--[a-zA-Z0-9_-]+/);
  if (nextFlag > 0) raw = raw.slice(0, nextFlag).trim();
  if ((raw.startsWith('"') && raw.endsWith('"')) || (raw.startsWith("'") && raw.endsWith("'"))) {
    raw = raw.slice(1, -1).trim();
  }

  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object' && typeof parsed.query === 'string') {
      return truncateText(parsed.query.replace(/\s+/g, ' ').trim(), 48);
    }
  } catch {
    // fall through to regex extraction
  }

  const m = raw.match(/"query"\s*:\s*"([^"]+)"/);
  if (m && m[1]) {
    return truncateText(m[1].replace(/\s+/g, ' ').trim(), 48);
  }
  return '';
}

function getProviderLabel(toolId) {
  const prefixes = Object.keys(PROVIDER_LABELS).sort((a, b) => b.length - a.length);
  for (const prefix of prefixes) {
    if (toolId === prefix || toolId.startsWith(`${prefix}_`)) return PROVIDER_LABELS[prefix];
  }
  return null;
}

function titleCaseWords(text) {
  return text
    .split(/[_\-\s]+/)
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

function labelAction(actionRaw) {
  const action = actionRaw.toLowerCase();
  if (action.includes('linkedin') && action.includes('post')) return 'LinkedIn Posts';
  if (action.includes('job') || action.includes('hiring')) return 'Job Listings';
  if (action.includes('comment') && action.includes('filter')) return 'Comment Filtering';
  if (action.includes('comment') && action.includes('search')) return 'Comment Search';
  if (action.includes('tam')) return 'TAM Analysis';
  if (action.includes('people') && action.includes('search')) return 'People Search';
  if (action.includes('company') && action.includes('search')) return 'Company Search';
  if (action.includes('email') && (action.includes('finder') || action.includes('find'))) return 'Email Finder';
  if (action.includes('verify') || action.includes('validation')) return 'Verification';
  return null;
}

function formatToolName(toolId) {
  const provider = getProviderLabel(toolId);
  const prefixes = Object.keys(PROVIDER_LABELS).sort((a, b) => b.length - a.length);
  if (provider) {
    const prefix = prefixes.find((p) => toolId === p || toolId.startsWith(`${p}_`));
    const actionRaw = prefix ? toolId.slice(prefix.length).replace(/^_+/, '') : toolId;
    if (!actionRaw) return provider;
    const clean = actionRaw
      .replace(/_search$/, ' search')
      .replace(/_finder$/, ' finder')
      .replace(/_enrichment$/, ' enrichment')
      .replace(/_verify|_validation$/, ' verify');
    return `${provider}: ${labelAction(clean) || titleCaseWords(clean)}`;
  }
  return labelAction(toolId) || titleCaseWords(toolId);
}

function shortToolTarget(toolId) {
  if (!toolId) return 'tool';
  const provider = getProviderLabel(toolId);
  if (provider) {
    return provider.toLowerCase();
  }
  return toolId.split('_')[0].toLowerCase();
}

function summarizeProviders(toolIds) {
  const names = [...new Set(toolIds.map((id) => getProviderLabel(id)).filter(Boolean))];
  return names.join(', ');
}

function basenameSafe(filePath) {
  return filePath ? path.basename(filePath) : '';
}

function explainCommand(command) {
  const mode = classifyCommand(command);
  const toolIds = extractExecutedTools(command);
  const primaryTool = toolIds[0] || '';
  const target = shortToolTarget(primaryTool);
  const primaryLabel = primaryTool ? formatToolName(primaryTool) : '';
  const rows = parseRowCount(command);
  const csv = basenameSafe(extractCsvPath(command));
  const payload = extractPayloadPreview(command);
  const payloadQuery = extractPayloadQuery(command);

  if (mode === 'enrich') {
    if (rows && csv) return { detail: `Enriching ${rows} rows (${csv})`, current: '', providers: '' };
    if (rows) return { detail: `Enriching ${rows} rows`, current: '', providers: '' };
    return { detail: 'Enriching rows', current: '', providers: '' };
  }

  if (mode === 'tools_get') {
    const target = extractToolsGetTarget(command);
    return { detail: `Learning ${shortToolTarget(target)}`, current: '', providers: '' };
  }

  if (mode === 'tools_execute') {
    if (payloadQuery && primaryLabel) return { detail: `${primaryLabel}: ${payloadQuery}`, current: '', providers: '' };
    if (primaryLabel && payload) return { detail: `${primaryLabel}: ${payload}`, current: '', providers: '' };
    if (primaryLabel) return { detail: `Running ${primaryLabel}`, current: '', providers: '' };
    if (payload) return { detail: `Calling ${target} with ${payload}`, current: '', providers: '' };
    return { detail: `Calling ${target}`, current: '', providers: '' };
  }

  if (mode === 'tools_search') {
    return { detail: 'Searching tools', current: '', providers: '' };
  }

  if (mode === 'csv') {
    return { detail: rows ? `Running CSV (${rows} rows)` : 'Running CSV', current: '', providers: '' };
  }

  return { detail: '', current: '', providers: '' };
}

function loadState() {
  try {
    const raw = fs.readFileSync(STATE_PATH, 'utf8');
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return { sessions: {}, backend: {} };
    return {
      sessions: parsed.sessions && typeof parsed.sessions === 'object' ? parsed.sessions : {},
      backend: parsed.backend && typeof parsed.backend === 'object' ? parsed.backend : {},
    };
  } catch {
    return { sessions: {}, backend: {} };
  }
}

function saveState(state) {
  try {
    fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
    fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2));
  } catch {
    // Keep status line resilient.
  }
}

function nextSpinnerFrame(sessionState) {
  const index = Number.isFinite(sessionState?.spinner_index) ? sessionState.spinner_index : 0;
  const next = (index + 1) % SPINNER_FRAMES.length;
  sessionState.spinner_index = next;
  return SPINNER_FRAMES[next];
}

function parseBackendUpFromText(text) {
  if (!text) return { up: null, renderUrl: '' };
  const lines = text.split('\n');
  let section = '';
  let backendStatus = null;
  let renderStatus = null;
  let renderUrl = '';
  let backendApiUrl = '';

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    if (/^backend:/i.test(line)) {
      section = 'backend';
      continue;
    }
    if (/^render:/i.test(line)) {
      section = 'render';
      continue;
    }
    if (/^[a-z][a-z0-9 _-]*:/i.test(line) && !/^status:/i.test(line) && !/^api url:/i.test(line) && !/^url:/i.test(line)) {
      section = '';
    }

    const statusMatch = line.match(/^status:\s*([a-z_ -]+)/i);
    if (statusMatch) {
      const val = statusMatch[1].trim().toLowerCase();
      if (section === 'backend') backendStatus = val;
      if (section === 'render') renderStatus = val;
    }

    const apiUrlMatch = line.match(/^api url:\s*(https?:\/\/\S+)/i);
    if (apiUrlMatch && section === 'backend') {
      backendApiUrl = apiUrlMatch[1];
    }

    const renderUrlMatch = line.match(/^url:\s*(https?:\/\/\S+)/i);
    if (renderUrlMatch && section === 'render') {
      renderUrl = renderUrlMatch[1];
    }
  }

  const lower = text.toLowerCase();
  if (!backendStatus) {
    if (lower.includes('"backend":{"running":true') || lower.includes('"backend":{"status":"running"')) {
      backendStatus = 'running';
    } else if (lower.includes('"backend":{"running":false') || lower.includes('"backend":{"status":"stopped"')) {
      backendStatus = 'stopped';
    }
  }

  let up = null;
  if (backendStatus) {
    up = backendStatus.includes('running') || backendStatus.includes('healthy');
  } else if (lower.includes('backend') && lower.includes('running')) {
    up = true;
  } else if (lower.includes('backend') && (lower.includes('stopped') || lower.includes('not running') || lower.includes('down'))) {
    up = false;
  }

  if (!renderUrl && renderStatus && renderStatus.includes('running') && backendApiUrl) {
    renderUrl = backendApiUrl;
  }

  return { up, renderUrl };
}

function parseBackendUpFromJson(output) {
  try {
    const parsed = JSON.parse(output);
    let up = null;
    if (typeof parsed?.backend?.running === 'boolean') {
      up = parsed.backend.running;
    } else if (typeof parsed?.backend?.healthy === 'boolean') {
      up = parsed.backend.healthy;
    } else if (typeof parsed?.running === 'boolean') {
      up = parsed.running;
    } else if (typeof parsed?.healthy === 'boolean') {
      up = parsed.healthy;
    } else if (typeof parsed?.backend?.status === 'string') {
      const s = parsed.backend.status.toLowerCase();
      up = s.includes('running') || s.includes('healthy');
    }

    const renderStatus = String(parsed?.render?.status || parsed?.render_status || '').toLowerCase();
    let renderUrl = String(parsed?.render?.url || parsed?.render_url || parsed?.csv_render_url || '').trim();
    if (!renderUrl && renderStatus.includes('running')) {
      renderUrl = String(parsed?.backend?.api_url || parsed?.api_url || '').trim();
    }

    return { up, renderUrl };
  } catch {
    return parseBackendUpFromText(output);
  }
}

function getBackendStatus(state, opts = {}) {
  const { allowProbe = true } = opts;
  const now = Date.now();
  const cached = state.backend || {};
  if (
    Number.isFinite(cached.checked_at_ms) &&
    now - cached.checked_at_ms < BACKEND_STATUS_TTL_MS &&
    typeof cached.up === 'boolean'
  ) {
    return {
      up: cached.up,
      renderUrl: cached.renderUrl || '',
      checked_at_ms: cached.checked_at_ms,
    };
  }

  if (!allowProbe) {
    return {
      up: typeof cached.up === 'boolean' ? cached.up : null,
      renderUrl: cached.renderUrl || '',
      checked_at_ms: Number.isFinite(cached.checked_at_ms) ? cached.checked_at_ms : 0,
    };
  }

  let up = null;
  let renderUrl = '';
  try {
    const out = execSync('deepline backend status --json', {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 1200,
    });
    const parsed = parseBackendUpFromJson(String(out || ''));
    up = parsed.up;
    renderUrl = parsed.renderUrl || '';
  } catch (err) {
    const stdout = String(err?.stdout || '');
    const stderr = String(err?.stderr || '');
    const parsed = parseBackendUpFromText(`${stdout}\n${stderr}`);
    up = typeof parsed.up === 'boolean' ? parsed.up : false;
    renderUrl = parsed.renderUrl || '';
  }

  const status = { up, renderUrl, checked_at_ms: now };
  state.backend = status;
  return status;
}

function buildActiveFromTranscript(lines, fallbackCommand) {
  const pending = new Map();
  const deeplineHistory = [];

  for (const entry of lines) {
    if (entry?.type === 'assistant') {
      for (const toolUse of getToolUsesFromMessage(entry.message)) {
        pending.set(toolUse.id, toolUse);
        if (isDeeplineToolUse(toolUse)) deeplineHistory.push(toolUse);
      }
      continue;
    }

    if (entry?.type === 'user') {
      for (const result of getToolResultsFromMessage(entry.message)) {
        if (typeof result?.tool_use_id === 'string') pending.delete(result.tool_use_id);
      }
    }
  }

  const active = [...pending.values()].filter((toolUse) => isDeeplineToolUse(toolUse));
  if (active.length > 0) {
    const latestCmd = extractToolUseCommand(active[active.length - 1]) || fallbackCommand || '';
    if (!isTrackableMode(classifyCommand(latestCmd))) return null;
    const explained = explainCommand(latestCmd);
    const runningIds = [...new Set(active.flatMap((toolUse) => extractExecutedTools(extractToolUseCommand(toolUse))))];
    const currentFallback = runningIds.slice(0, MAX_RUNNING_SHOWN).map((id) => formatToolName(id)).join(', ');
    return {
      detail: explained.detail,
      current: explained.current || currentFallback,
      providers: explained.providers || summarizeProviders(runningIds),
      summary: explained.current || explained.detail || currentFallback || 'workflow',
    };
  }

  const fallback = fallbackCommand || extractToolUseCommand(deeplineHistory[deeplineHistory.length - 1]) || '';
  if (!fallback || !isDeeplineCommand(fallback)) return null;
  if (!isTrackableMode(classifyCommand(fallback))) return null;

  if (deeplineHistory.length === 0) {
    const explained = explainCommand(fallback);
    return {
      detail: explained.detail,
      current: explained.current,
      providers: explained.providers,
      summary: explained.current || explained.detail || explained.providers || 'workflow',
    };
  }

  return null;
}

function backendBadge(backend, frameIndex) {
  if (typeof backend?.up !== 'boolean') {
    return '';
  }
  void frameIndex;
  if (backend.up) {
    return ansi('✅ Backend running', C.green, true);
  }
  return ansi('⏸️ Backend paused', C.red, true);
}

function renderActiveLine(frame, status, backend, frameIndex, thinking) {
  const detail = status.detail || 'Running task';
  const thinkingSuffix = thinking ? ` | ${thinking}` : '';
  const rightRaw = `${frame} ${detail}${thinkingSuffix}`;
  const right = ansi(rightRaw, C.white, true);
  const left = backendBadge(backend, frameIndex);
  if (!left) return right;
  return joinInline(left, right);
}

async function main() {
  const input = await readStdin();
  if (!input) return;

  let data;
  try {
    data = JSON.parse(input);
  } catch {
    return;
  }

  const fallbackCommand = typeof data?.command === 'string' ? data.command : '';
  const transcriptPath = typeof data?.transcript_path === 'string' ? data.transcript_path : '';
  const sessionId = typeof data?.session_id === 'string' ? data.session_id : 'default';

  const state = loadState();
  const sessionState = state.sessions[sessionId] || {
    spinner_index: 0,
    was_active: false,
    active_summary: '',
    last_ran: '',
  };

  const frame = nextSpinnerFrame(sessionState);
  const frameIndex = sessionState.spinner_index || 0;

  const lines = readTranscriptTail(transcriptPath);
  const activeStatus = buildActiveFromTranscript(lines, fallbackCommand);
  const latestThinking = extractThinkingText(lines);
  const backendStatus = getBackendStatus(state, {
    allowProbe: !activeStatus && !shouldUseCachedBackendOnly(fallbackCommand),
  });

  if (activeStatus) {
    sessionState.was_active = true;
    sessionState.active_summary = activeStatus.summary || activeStatus.detail;
    sessionState.active_started_ms = Date.now();
    state.sessions[sessionId] = sessionState;
    saveState(state);
    const activeThinking = latestThinking ? `Thinking: ${truncateText(latestThinking, 56)}` : '';
    console.log(renderActiveLine(frame, activeStatus, backendStatus, frameIndex, activeThinking));
    return;
  }

  const now = Date.now();
  const lastActiveMs = Number.isFinite(sessionState.active_started_ms) ? sessionState.active_started_ms : 0;
  if (sessionState.was_active && lastActiveMs && now - lastActiveMs < ACTIVE_PERSIST_MS && sessionState.active_summary) {
    sessionState.was_active = true;
    state.sessions[sessionId] = sessionState;
    saveState(state);
    const persisted = {
      detail: sessionState.active_summary,
      current: sessionState.active_summary,
      providers: '',
      summary: sessionState.active_summary,
    };
    const activeThinking = latestThinking ? `Thinking: ${truncateText(latestThinking, 56)}` : '';
    console.log(renderActiveLine(frame, persisted, backendStatus, frameIndex, activeThinking));
    return;
  }

  if (sessionState.was_active && sessionState.active_summary) {
    sessionState.last_ran = sessionState.active_summary;
  }
  sessionState.was_active = false;
  sessionState.active_summary = '';

  state.sessions[sessionId] = sessionState;
  saveState(state);

  // Stay silent when no Deepline command is active.
  return;
}

main();
