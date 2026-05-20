---
id: jira-read-work-item
description: Retrieve Jira issue context with jira-read-work-item, summarize the ticket for the user, and optionally create a local analysis artifact for follow-up work. Produces machine-readable JSON that works well with GitHub Copilot and other AI agents.
platform:
  github:
    mode: agent
share: public
version: 1
tags: [jira, atlassian, acli, copilot, workflow, investigation]
---

# Jira Read Work Item

Use this command when you want GitHub Copilot to fetch a Jira ticket, inspect linked issues and comments, and turn the result into an actionable summary or analysis artifact.

## What This Wraps

Primary tool:

```bash
npm run jira:read -- --key <ISSUE-KEY> --origin github-copilot:read-work-item --max-linked-items 10
```

Direct wrapper:

```bash
node tools/jira-read-work-item.js --key <ISSUE-KEY>
```

The tool returns JSON with:

- `status`
- `message`
- `data.issue`
- `data.linkedIssues`
- `data.comments`
- `data.metadata`
- `data.artifacts`
- `data.suggestedWritePath`
- `data.agentContext`

## Trigger In Copilot

Use one of these prompts in GitHub Copilot Chat after opening the `ai-agent-workspace` workspace:

```text
Run the jira-read-work-item workflow for PROJ-123.
```

```text
Use jira-read-work-item to fetch PROJ-123 and summarize the issue, linked tickets, comments, and next steps.
```

```text
Run jira-read-work-item for PROJ-123 and save the raw JSON to .jira-work-items/PROJ-123/PROJ-123-raw.json.
```

If you want a more explicit prompt for Copilot, use:

```text
From /Users/francisadediran/development/ai-agent-workspace, run `npm run jira:read -- --key PROJ-123 --origin github-copilot:read-work-item --max-linked-items 10 --output-file .jira-work-items/PROJ-123/PROJ-123-raw.json`, then summarize the JSON response.
```

## Recommended Agent Behavior

1. Confirm `acli` is available and Jira auth is valid if the tool returns a `fix` response.
2. Run the tool from the `ai-agent-workspace` root.
3. Read the JSON response instead of relying on human-readable CLI output.
4. Present a concise summary of the primary issue: key, summary, type, status, priority, assignee.
5. Include linked issue count, comment count, referenced images, and any existing artifacts.
6. If requested, write or update analysis artifacts under `data.suggestedWritePath`.

## Common Examples

Basic retrieval:

```bash
npm run jira:read -- --key PROJ-123
```

Capture raw JSON for later analysis:

```bash
npm run jira:read -- --key PROJ-123 --output-file .jira-work-items/PROJ-123/PROJ-123-raw.json
```

Inspect existing artifacts only:

```bash
npm run jira:read -- --key PROJ-123 --artifacts-only
```

Write artifacts to a custom directory:

```bash
npm run jira:read -- --key PROJ-123 --artifacts-dir ./tmp/jira-work-items
```

## Prerequisites

- Run `npm install` in the workspace root.
- Ensure `acli` is installed.
- Authenticate with Jira:

```bash
acli jira auth login --web
```

## Expected Output Pattern

When successful, Copilot should report:

1. A short ticket summary.
2. Whether linked items were truncated.
3. Whether comments or image references were found.
4. Where artifacts already exist or should be written.
5. Any follow-up analysis questions if the ticket is underspecified.

## Notes

- Default artifact root is `.jira-work-items/<ISSUE-KEY>`.
- Default origin label is `github-copilot:read-work-item`.
- If the tool returns `status: "fix"`, resolve the setup or auth problem before retrying.
