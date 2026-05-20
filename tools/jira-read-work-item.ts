#!/usr/bin/env node

// jira-read-work-item - Retrieve Jira issue context with pruned fields, linked issues,
// comments, and local artifact discovery for AI agents and CLI workflows.

import {
    executeAcli,
    hasAcli,
    isAuthenticated,
    buildFixMessage,
    classifyAcliError,
    buildNoCliResponse,
} from './atlassianCli';
import type { ToolResponse, AcliErrorClass } from './atlassianCli';
import { existsSync, mkdirSync, readdirSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';

const DEFAULT_ARTIFACTS_ROOT = process.env.JIRA_WORK_ITEMS_DIR || '.jira-work-items';
const DEFAULT_ORIGIN = 'github-copilot:read-work-item';

interface Args {
    key: string;
    maxLinkedItems: number;
    origin?: string;
    artifactsOnly: boolean;
    outputFile?: string;
    artifactsDir: string;
}

interface ReferencedImage {
    attachmentId: string;
    fileName: string;
    url: string;
    referencedIn: string[];
}

interface WorkItemArtifacts {
    basePath: string;
    analysisPath?: string;
    planPath?: string;
    taskFiles: string[];
    exists: boolean;
}

interface AgentContext {
    toolName: 'jira-read-work-item';
    machineReadable: true;
    recommendedOrigin: string;
    artifactDirectory: string;
}

interface JiraIssueContextData {
    issue: unknown;
    linkedIssues: unknown[];
    comments: unknown[];
    metadata: {
        linkedItemsRetrieved: number;
        linkedItemsTotal: number;
        truncated: boolean;
        referencedImages: ReferencedImage[];
        appliedLabels: string[];
    };
    artifacts: WorkItemArtifacts;
    suggestedWritePath: string;
    agentContext: AgentContext;
}

interface ArtifactsOnlyData {
    artifacts: WorkItemArtifacts;
    suggestedWritePath: string;
    agentContext: AgentContext;
}

function discoverArtifacts(issueKey: string, artifactsRoot: string): WorkItemArtifacts {
    const basePath = join(artifactsRoot, issueKey);

    if (!existsSync(basePath)) {
        return { basePath, taskFiles: [], exists: false };
    }

    const files = readdirSync(basePath);
    const analysisPath = files.find((fileName) => fileName.endsWith('-analysis.md'));
    const planPath = files.find((fileName) => fileName === 'plan.md' || fileName.endsWith('-plan.md'));
    const taskFiles = files.filter((fileName) => /^task-\d+/.test(fileName));

    return {
        basePath,
        analysisPath: analysisPath ? join(basePath, analysisPath) : undefined,
        planPath: planPath ? join(basePath, planPath) : undefined,
        taskFiles: taskFiles.map((fileName) => join(basePath, fileName)),
        exists: true,
    };
}

function buildAgentContext(artifacts: WorkItemArtifacts): AgentContext {
    return {
        toolName: 'jira-read-work-item',
        machineReadable: true,
        recommendedOrigin: DEFAULT_ORIGIN,
        artifactDirectory: artifacts.basePath,
    };
}

function executeAcliCommand(args: string[]): unknown {
    const result = executeAcli(args, { timeout: 60000 });
    if (!result.success) {
        if (/not found|no such issue|does not exist/i.test(result.stderr)) {
            throw new Error('ISSUE_NOT_FOUND');
        }
        throw new Error(result.message, { cause: { stderr: result.stderr, errorClass: result.errorClass } });
    }
    return JSON.parse(result.stdout);
}

function applyOriginLabel(
    issueKey: string,
    existingLabels: string[],
    origin?: string,
): { added: boolean; labels: string[] } {
    try {
        if (!origin || existingLabels.some((label) => label.toLowerCase() === origin.toLowerCase())) {
            return { added: false, labels: [] };
        }

        const allLabels = [...existingLabels, origin];
        const result = executeAcli([
            'jira', 'workitem', 'update', issueKey,
            '--labels', allLabels.join(','),
        ]);

        if (!result.success) {
            return { added: false, labels: [] };
        }

        return { added: true, labels: [origin] };
    } catch {
        return { added: false, labels: [] };
    }
}

function pruneIdentity(identity: Record<string, unknown>): Record<string, unknown> {
    return {
        displayName: identity.displayName,
        emailAddress: identity.emailAddress,
    };
}

function pruneIssueFields(fields: Record<string, unknown>): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(fields)) {
        if (
            key.includes('customfield_') ||
            key.includes('worklog') ||
            key.includes('timetracking') ||
            key.includes('aggregatetimespent') ||
            key.includes('aggregatetimeoriginalestimate') ||
            key.includes('aggregatetimeestimate') ||
            key.includes('timespent') ||
            key.includes('timeoriginalestimate') ||
            key.includes('timeestimate') ||
            key === 'votes' ||
            key === 'watches' ||
            key === 'workratio' ||
            key === 'environment' ||
            key === 'progress' ||
            key === 'aggregateprogress'
        ) {
            continue;
        }

        if (value && typeof value === 'object' && !Array.isArray(value)) {
            const obj = value as Record<string, unknown>;
            if (obj.displayName && (obj.emailAddress || obj.accountId)) {
                result[key] = pruneIdentity(obj);
            } else {
                result[key] = value;
            }
        } else {
            result[key] = value;
        }
    }
    return result;
}

function extractImageReferences(fields: Record<string, unknown>): ReferencedImage[] {
    const imageMap = new Map<string, ReferencedImage>();
    const textFields = ['description', 'customfield_10014'];

    for (const fieldName of textFields) {
        const fieldValue = fields[fieldName];
        if (typeof fieldValue !== 'string') continue;

        const imgRegex = /(?:src="([^"]*\/attachment\/(\d+)[^"]*)"|"id":\s*"([a-f0-9-]+)".*?"type":\s*"file")/gi;
        let match;

        while ((match = imgRegex.exec(fieldValue)) !== null) {
            const url = match[1] || '';
            const attachmentId = match[2] || match[3] || '';

            if (attachmentId && !imageMap.has(attachmentId)) {
                const filenameMatch = url.match(/[?&]filename=([^&"]+)/);
                const fileName = filenameMatch ? decodeURIComponent(filenameMatch[1]) : 'unknown';

                imageMap.set(attachmentId, {
                    attachmentId,
                    fileName,
                    url,
                    referencedIn: [fieldName],
                });
            } else if (attachmentId) {
                const existing = imageMap.get(attachmentId);
                if (existing && !existing.referencedIn.includes(fieldName)) {
                    existing.referencedIn.push(fieldName);
                }
            }
        }
    }

    return Array.from(imageMap.values());
}

export function readJiraIssue(args: Args): ToolResponse {
    const { key, maxLinkedItems, origin, artifactsOnly, artifactsDir } = args;

    const artifacts = discoverArtifacts(key, artifactsDir);
    const agentContext = buildAgentContext(artifacts);

    if (artifactsOnly) {
        const data: ArtifactsOnlyData = {
            artifacts,
            suggestedWritePath: artifacts.basePath,
            agentContext,
        };

        let message = `Discovered artifacts for issue ${key}.`;
        if (artifacts.exists) {
            const count =
                (artifacts.analysisPath ? 1 : 0) + (artifacts.planPath ? 1 : 0) + artifacts.taskFiles.length;
            message += ` Found ${count} existing artifact${count !== 1 ? 's' : ''} at ${artifacts.basePath}.`;
        } else {
            message += ` No existing artifacts found. Suggested write path: ${artifacts.basePath}`;
        }

        return { status: 'success', message, data };
    }

    try {
        if (!hasAcli()) {
            return buildNoCliResponse();
        }

        if (!isAuthenticated()) {
            return {
                status: 'fix',
                message: buildFixMessage('auth', 'Not authenticated to Jira'),
            };
        }

        const issueRaw = executeAcliCommand([
            'jira', 'workitem', 'view', key,
            '--fields', '*all',
            '--json',
        ]) as Record<string, unknown>;

        const rawFields = (issueRaw.fields as Record<string, unknown>) || {};
        const issue = {
            ...issueRaw,
            fields: pruneIssueFields(rawFields),
        };

        const issueLinks = (rawFields.issuelinks as Record<string, unknown>[]) || [];
        const linkedIssues: unknown[] = [];

        if (maxLinkedItems > 0) {
            const toFetch = issueLinks.slice(0, maxLinkedItems);
            for (const link of toFetch) {
                const linkedRef = (link.inwardIssue || link.outwardIssue) as Record<string, unknown> | undefined;
                if (linkedRef && linkedRef.key) {
                    try {
                        const linked = executeAcliCommand([
                            'jira', 'workitem', 'view', linkedRef.key as string,
                            '--fields', 'summary,status,priority,issuetype,assignee',
                            '--json',
                        ]);
                        linkedIssues.push(linked);
                    } catch {
                    }
                }
            }
        }

        const parent = rawFields.parent as Record<string, unknown> | undefined;
        if (parent && parent.key && maxLinkedItems > 0) {
            try {
                const parentIssue = executeAcliCommand([
                    'jira', 'workitem', 'view', parent.key as string,
                    '--fields', 'summary,status,priority,issuetype,assignee',
                    '--json',
                ]);
                linkedIssues.push(parentIssue);
            } catch {
            }
        }

        let comments: unknown[] = [];
        try {
            const commentsResult = executeAcli([
                'jira', 'workitem', 'comment', 'list',
                '--key', key,
                '--json',
            ]);
            if (commentsResult.success) {
                const parsed = JSON.parse(commentsResult.stdout);
                comments = Array.isArray(parsed) ? parsed : [];
            }
        } catch {
        }

        const referencedImages = extractImageReferences(rawFields);
        const existingLabels = (rawFields.labels as string[]) || [];
        const labelResult = applyOriginLabel(key, existingLabels, origin);

        const contextData: JiraIssueContextData = {
            issue,
            linkedIssues,
            comments,
            metadata: {
                linkedItemsRetrieved: linkedIssues.length,
                linkedItemsTotal: issueLinks.length + (parent ? 1 : 0),
                truncated: linkedIssues.length < issueLinks.length + (parent ? 1 : 0),
                referencedImages,
                appliedLabels: labelResult.labels,
            },
            artifacts,
            suggestedWritePath: artifacts.basePath,
            agentContext,
        };

        let message = `Retrieved Jira issue ${key}.`;
        if (labelResult.added) {
            message += ` Applied origin label '${labelResult.labels[0]}'.`;
        }
        if (referencedImages.length > 0) {
            message += ` Contains ${referencedImages.length} image attachment${referencedImages.length > 1 ? 's' : ''}.`;
        }
        if (linkedIssues.length > 0) {
            message += ` Retrieved ${linkedIssues.length} linked issue${linkedIssues.length !== 1 ? 's' : ''}.`;
        }
        if (comments.length > 0) {
            message += ` Retrieved ${comments.length} comment${comments.length !== 1 ? 's' : ''}.`;
        }
        if (artifacts.exists) {
            const count =
                (artifacts.analysisPath ? 1 : 0) + (artifacts.planPath ? 1 : 0) + artifacts.taskFiles.length;
            message += ` Found ${count} existing artifact${count !== 1 ? 's' : ''} at ${artifacts.basePath}.`;
        } else {
            message += ` No existing artifacts. Suggested write path: ${artifacts.basePath}`;
        }

        return { status: 'success', message, data: contextData };
    } catch (error) {
        if (error instanceof Error) {
            if (error.message === 'ISSUE_NOT_FOUND') {
                return {
                    status: 'fail',
                    message: `Jira issue ${key} not found. Verify the key and try again.`,
                };
            }

            const cause = error.cause as { stderr?: string; errorClass?: AcliErrorClass } | undefined;
            const stderr = cause?.stderr ?? '';
            const errorClass = cause?.errorClass ?? classifyAcliError(`${error.message} ${stderr}`);

            if (errorClass !== 'unknown') {
                return {
                    status: 'fix',
                    message: buildFixMessage(errorClass, stderr || error.message),
                };
            }

            return { status: 'fail', message: `Jira API error: ${error.message}` };
        }
        return { status: 'fail', message: `Unexpected error: ${String(error)}` };
    }
}

function parseArgs(argv: string[]): Args | null {
    if (argv.includes('--help') || argv.includes('-h')) {
        console.log('jira-read-work-item - Retrieve Jira issue context for AI agents and CLI workflows\n');
        console.log('Usage:');
        console.log('  jira-read-work-item --key <ISSUE-KEY> [options]\n');
        console.log('Options:');
        console.log('  --key              Jira issue key (e.g., PROJ-123) (required)');
        console.log('  --max-linked-items Maximum linked items to retrieve [default: 10]');
        console.log(`  --origin           Optional Jira label to add for agent tracking [default: ${DEFAULT_ORIGIN}]`);
        console.log(`  --artifacts-dir    Artifact root directory [default: ${DEFAULT_ARTIFACTS_ROOT}]`);
        console.log('  --artifacts-only   Skip API fetch, only discover local artifacts');
        console.log('  --output-file      Write tool JSON output to file (UTF-8)');
        console.log('  --help             Show this help message');
        process.exit(0);
    }

    let key = '';
    let maxLinkedItems = 10;
    let origin = DEFAULT_ORIGIN;
    let artifactsOnly = false;
    let outputFile: string | undefined;
    let artifactsDir = DEFAULT_ARTIFACTS_ROOT;

    for (let i = 2; i < argv.length; i++) {
        const arg = argv[i];
        switch (arg) {
            case '--key':
                key = argv[++i] || '';
                break;
            case '--max-linked-items': {
                const value = parseInt(argv[++i] || '10', 10);
                if (Number.isNaN(value) || value < 0) {
                    console.error('Invalid value for --max-linked-items. Expected a non-negative integer.');
                    process.exit(1);
                }
                maxLinkedItems = value;
                break;
            }
            case '--origin':
                origin = argv[++i] || '';
                if (!origin) {
                    console.error('Missing value for --origin');
                    process.exit(1);
                }
                break;
            case '--artifacts-dir':
                artifactsDir = argv[++i] || '';
                if (!artifactsDir) {
                    console.error('Missing value for --artifacts-dir');
                    process.exit(1);
                }
                break;
            case '--artifacts-only':
                artifactsOnly = true;
                break;
            case '--output-file':
                outputFile = argv[++i] || '';
                if (!outputFile) {
                    console.error('Missing value for --output-file');
                    process.exit(1);
                }
                break;
            default:
                console.error(`Unknown argument: ${arg}`);
                process.exit(1);
        }
    }

    if (!key) {
        console.error('Missing required argument: --key');
        process.exit(1);
    }

    return { key, maxLinkedItems, origin, artifactsOnly, outputFile, artifactsDir };
}

function main(): void {
    const args = parseArgs(process.argv);
    if (!args) {
        process.exit(1);
    }

    const response = readJiraIssue(args);
    const responseJson = JSON.stringify(response);

    if (args.outputFile) {
        try {
            const parentDir = dirname(args.outputFile);
            if (parentDir && parentDir !== '.') {
                mkdirSync(parentDir, { recursive: true });
            }
            writeFileSync(args.outputFile, responseJson, 'utf-8');
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            console.error(`Failed to write --output-file '${args.outputFile}': ${message}`);
            process.exit(1);
        }
    }

    console.log(responseJson);
    process.exit(response.status === 'fail' ? 1 : 0);
}

const isDirectExecution = process.argv[1]?.includes('jira-read-work-item');
if (isDirectExecution) {
    main();
}
