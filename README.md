# AI Agent Workspace

This repository is a ready-to-use VS Code workspace for developers who want one place to manage:

- **skills**
- **workflows**
- **tools**
- **commands**

## Workspace structure

```text
.
├── .vscode/
│   ├── settings.json
│   └── tasks.json
├── commands/
├── skills/
├── tools/
├── workflows/
└── ai-agent-workspace.code-workspace
```

## Use in VS Code

1. Clone this repository.
2. Open `ai-agent-workspace.code-workspace` in VS Code.
3. Add your shared developer assets in:
   - `skills/`
   - `workflows/`
   - `tools/`
   - `commands/`
4. Run `Terminal: Run Task` in VS Code and select one of the predefined tasks.

## Notes

- This repository is intentionally lightweight and does not include a build/test toolchain.
- Add project-specific automation as needed.

## Included Tooling

- `jira-read-work-item` lives in [tools/jira-read-work-item.ts](tools/jira-read-work-item.ts) with a JS wrapper at [tools/jira-read-work-item.js](tools/jira-read-work-item.js).
- Install workspace dependencies with `npm install`, then run `npm run jira:read -- --help` from the workspace root.
- `postgres-mcp` starter files live under [tools/postgres-mcp/README.md](tools/postgres-mcp/README.md) and include a schema export script, MCP config template, and example SQL.

## Included Skills

- `code-using-tdd` lives in [skills/code-using-tdd/SKILL.md](skills/code-using-tdd/SKILL.md).
- In Copilot Chat, ask: `Use the code-using-tdd skill for this implementation.`

## Triggering The Workflow

- The Copilot-oriented wrapper lives at [commands/jira-read-work-item.md](commands/jira-read-work-item.md).
- In GitHub Copilot Chat, ask: `Run the jira-read-work-item workflow for PROJ-123.`
- For a terminal-first path, run: `npm run jira:read -- --key PROJ-123 --origin github-copilot:read-work-item --max-linked-items 10`
