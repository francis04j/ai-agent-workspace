# Postgres MCP Starter

This folder contains a safe starter kit for querying Postgres with an AI-enabled IDE through MCP.

Included files:

- `export-schema.sh`: extracts tables, columns, foreign keys, indexes, and sampled JSONB structures from a Postgres database
- `mcp.template.json`: example MCP server configuration without secrets
- `example-queries.sql`: seed examples to help plain-English to SQL prompting

## What To Store Here

Good candidates for this folder:

- helper scripts
- config templates
- example SQL
- setup notes for Copilot, Cursor, or other IDEs

Do not commit:

- real database passwords
- production connection strings
- local MCP config files with secrets
- generated schema dumps from sensitive databases

## Suggested Local Setup

1. Install Postgres client tools so `psql` is available.
2. Copy `mcp.template.json` to a local ignored file such as `mcp.local.json` and fill in your connection string.
3. Set `DB_NAME` and `DB_USER`, plus `PGHOST` and `PGPORT` if needed.
4. Run `bash tools/postgres-mcp/export-schema.sh` from the workspace root.
5. Reference the generated `db-schema.sql` and `example-queries.sql` in your prompt.

## Example Copilot Prompts

```text
Use the Postgres MCP setup in tools/postgres-mcp and tell me what I still need to configure locally.
```

```text
I have a schema file at tools/postgres-mcp/db-schema.sql and example queries at tools/postgres-mcp/example-queries.sql. Help me write a Postgres query in plain English.
```

```text
Based on tools/postgres-mcp/example-queries.sql, generate a query to show failed tasks by day for the last two weeks.
```

## Example IDE Prompt Pattern

After you have created `db-schema.sql`, a useful prompt pattern is:

```text
@tools/postgres-mcp/db-schema.sql @tools/postgres-mcp/example-queries.sql Write a Postgres query to fetch day-wise failure percentages for the last two weeks.
```

## Safety Notes

- Prefer read-only database access.
- Avoid connecting an AI tool directly to production.
- Review generated SQL before running anything against important systems.
- Check your IDE privacy settings before sharing database-derived context with a model.