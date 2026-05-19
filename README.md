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
