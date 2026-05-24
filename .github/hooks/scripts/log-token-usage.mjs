#!/usr/bin/env node
/**
 * PostToolUse hook — log token usage from any LLM tool response.
 *
 * Works with any agent/SDK that surfaces token counts under these field names:
 *   Anthropic / our API:  usage.input_tokens, usage.output_tokens, usage.total_tokens
 *   OpenAI:               usage.prompt_tokens, usage.completion_tokens, usage.total_tokens
 *
 * Appends one line per run to .github/hooks/logs/token-usage.log.
 * Never blocks the agent — all errors fail open.
 */

import { appendFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const LOG_DIR = join(__dirname, '../logs');
const LOG_FILE = join(LOG_DIR, 'token-usage.log');

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

function tryParseJson(value) {
  if (value && typeof value === 'object') return value;
  if (typeof value === 'string') {
    try { return JSON.parse(value); } catch { return null; }
  }
  return null;
}

/**
 * Recursively search an object for token usage fields.
 * Handles Anthropic (input_tokens/output_tokens) and OpenAI (prompt_tokens/completion_tokens).
 * Also tries to parse any string values that look like JSON.
 */
function findUsage(obj, depth = 0) {
  if (!obj || typeof obj !== 'object' || depth > 6) return null;

  // Direct hit — object itself contains token count fields
  if ('input_tokens' in obj || 'prompt_tokens' in obj) {
    const inputTokens = obj.input_tokens ?? obj.prompt_tokens ?? 0;
    const outputTokens = obj.output_tokens ?? obj.completion_tokens ?? 0;
    const totalTokens = obj.total_tokens ?? (inputTokens + outputTokens);
    return { input_tokens: inputTokens, output_tokens: outputTokens, total_tokens: totalTokens };
  }

  // Check a nested 'usage' key first (most common pattern)
  if (obj.usage) {
    const found = findUsage(obj.usage, depth + 1);
    if (found) return found;
  }

  // Walk all values — parse JSON strings, recurse into objects
  for (const val of Object.values(obj)) {
    if (typeof val === 'string' && val.trimStart().startsWith('{')) {
      const parsed = tryParseJson(val);
      if (parsed) {
        const found = findUsage(parsed, depth + 1);
        if (found) return found;
      }
    } else if (val && typeof val === 'object') {
      const found = findUsage(val, depth + 1);
      if (found) return found;
    }
  }

  return null;
}

function buildLogLine(toolName, requestId, usage) {
  const ts = new Date().toISOString();
  return [
    ts,
    `tool=${toolName || 'unknown'}`,
    requestId ? `request_id=${requestId}` : null,
    `input_tokens=${usage.input_tokens}`,
    `output_tokens=${usage.output_tokens}`,
    `total_tokens=${usage.total_tokens}`,
  ]
    .filter(Boolean)
    .join(' | ');
}

function writeLog(line) {
  try {
    mkdirSync(LOG_DIR, { recursive: true });
    appendFileSync(LOG_FILE, line + '\n', 'utf8');
  } catch {
    // Non-fatal: log write failure must not block the agent
  }
}

function exit(systemMessage) {
  const out = { hookSpecificOutput: { hookEventName: 'PostToolUse' } };
  if (systemMessage) out.systemMessage = systemMessage;
  process.stdout.write(JSON.stringify(out));
  process.exit(0);
}

try {
  const raw = await readStdin();
  const payload = raw.trim() ? tryParseJson(raw) : null;

  if (!payload) exit();

  const toolName = typeof payload.tool_name === 'string' ? payload.tool_name : '';
  const responseOutput = payload.tool_response?.output ?? payload.tool_response ?? {};
  const parsed = tryParseJson(responseOutput) ?? (typeof responseOutput === 'object' ? responseOutput : {});

  const usage = findUsage(parsed);
  if (!usage) exit();

  const requestId = parsed.request_id ?? parsed.id ?? null;
  const line = buildLogLine(toolName, requestId, usage);
  writeLog(line);

  exit(`[token-usage] ${line}`);
} catch {
  // Fail open — logging errors must never interrupt the agent
  exit();
}
