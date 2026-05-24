#!/usr/bin/env node

import process from 'node:process';

const TERMINAL_TOOL_NAMES = new Set([
  'run_in_terminal',
  'send_to_terminal',
  'get_terminal_output',
  'kill_terminal',
  'execution_subagent',
  'terminal_last_command',
  'terminal_selection',
  'create_and_run_task',
  'run_task',
]);

const HIGH_RISK_PATTERNS = [
  { pattern: /\brm\s+-rf\s+\/$/, reason: 'Refusing to delete the filesystem root.' },
  { pattern: /\bsudo\s+rm\b/, reason: 'Refusing privileged recursive deletion commands.' },
  { pattern: /\bmkfs(\.[a-z0-9_+-]+)?\b/i, reason: 'Refusing filesystem format commands.' },
  { pattern: /\bdd\b.*\bof=\/dev\//i, reason: 'Refusing raw device write commands.' },
  { pattern: /:\s*\(\)\s*\{\s*:\|:&\s*\};:/, reason: 'Refusing fork bomb pattern.' },
];

const ASK_PATTERNS = [
  { pattern: /\bgit\s+reset\s+--hard\b/i, reason: 'This will discard local Git changes.' },
  { pattern: /\bgit\s+clean\s+-fdx\b/i, reason: 'This will remove untracked files and ignored files.' },
  { pattern: /\brm\s+-rf\b/i, reason: 'Recursive delete detected.' },
  { pattern: /\b(drop|truncate)\s+table\b/i, reason: 'Destructive SQL detected.' },
  { pattern: /\bnpm\s+publish\b/i, reason: 'Publishing to a package registry should be confirmed.' },
];

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => {
      data += chunk;
    });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

function isTerminalLikeTool(toolName) {
  if (!toolName) {
    return false;
  }

  return (
    TERMINAL_TOOL_NAMES.has(toolName) ||
    toolName.includes('terminal') ||
    toolName.includes('command') ||
    toolName.includes('task')
  );
}

function extractCommand(toolName, toolInput) {
  if (!toolInput || typeof toolInput !== 'object') {
    return '';
  }

  if (typeof toolInput.command === 'string') {
    return toolInput.command;
  }

  if (typeof toolInput.query === 'string' && toolName === 'execution_subagent') {
    return toolInput.query;
  }

  if (typeof toolInput.text === 'string') {
    return toolInput.text;
  }

  return '';
}

function printDecision(permissionDecision, permissionDecisionReason) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision,
        permissionDecisionReason,
      },
    })
  );
}

try {
  const rawInput = await readStdin();
  const payload = rawInput.trim() ? JSON.parse(rawInput) : {};
  const toolName = typeof payload.tool_name === 'string' ? payload.tool_name : '';

  if (!isTerminalLikeTool(toolName)) {
    printDecision('allow', 'Non-command tool.');
    process.exit(0);
  }

  const command = extractCommand(toolName, payload.tool_input).trim();
  if (!command) {
    printDecision('allow', 'No command string found to validate.');
    process.exit(0);
  }

  for (const rule of HIGH_RISK_PATTERNS) {
    if (rule.pattern.test(command)) {
      printDecision('deny', rule.reason);
      process.exit(0);
    }
  }

  for (const rule of ASK_PATTERNS) {
    if (rule.pattern.test(command)) {
      printDecision('ask', `${rule.reason} Command: ${command}`);
      process.exit(0);
    }
  }

  printDecision('allow', 'Command passed pre-run validation.');
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'ask',
        permissionDecisionReason: `Hook failed open and requires confirmation: ${message}`,
      },
      systemMessage: `Pre-run command hook could not fully validate this tool call: ${message}`,
    })
  );
  process.exit(0);
}