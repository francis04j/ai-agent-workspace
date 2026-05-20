#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const { join } = require("node:path");

const tsEntry = join(__dirname, "jira-read-work-item.ts");
const args = ["tsx", tsEntry, ...process.argv.slice(2)];

const result = spawnSync("npx", args, { stdio: "inherit", shell: true });

if (result.error) {
  console.error(String(result.error));
  process.exit(1);
}

process.exit(result.status ?? 1);
