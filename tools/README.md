# Tools

Store tool references, wrappers, and helper scripts in this folder.

Examples:

- CLI setup docs
- utility scripts
- configuration snippets

## jira-read-work-item

This workspace contains a self-contained Jira ticket reader for AI agents and terminal workflows:

```bash
npm install
npm run jira:read -- --help
node tools/jira-read-work-item.js --help
```

Prerequisites:

- `acli` installed and on `PATH`
- `acli jira auth login --web` completed
- Node.js and npm available

The tool writes artifacts to `.jira-work-items/<ISSUE_KEY>` by default and supports `--artifacts-dir` when an agent needs a different output location.

## postgres-mcp

This workspace also includes a Postgres MCP starter in [tools/postgres-mcp/README.md](tools/postgres-mcp/README.md).

Use it for:

- local MCP config templates
- schema export helpers
- example SQL for AI prompting

Quick start:

```bash
DB_NAME=mydb DB_USER=myuser bash tools/postgres-mcp/export-schema.sh
```

Then prompt your AI tool with:

```text
@tools/postgres-mcp/db-schema.sql @tools/postgres-mcp/example-queries.sql Write a Postgres query to fetch failed tasks by day for the last two weeks.
```
